"""The epic #105 capstone, streaming edition: fixture Track-A artifacts in →
Hop-B artifacts out (ADR-013 e2e), through resolve_run leases + the streaming
sink with fake ports only.

Covers the S7 acceptance criteria under the OOM-fix design: (a) §6 gate before
any of a target's bytes are staged, (b) upload order shards → sidecar → manifest
LAST, (c) §4.1a document fields with the pinned consumer name, (d) the §11.4
interlock (default config ⇒ ZERO store calls), (e) byte parity with the full
fixture set (toolchain-pinned — fails loud on drift, never skips silently),
plus the streaming-specific ragged-run refusals.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pytest

from views_postprocessing.delivery.draws import DrawsCollapseError
from views_postprocessing.unfao import product

from views_postprocessing.contract.frames import build_prediction_frame
from views_postprocessing.contract.wire import sink
from views_postprocessing.contract.wire import source_selection as sel

# The wire takes the partner's product facts as ARGUMENTS since #153 — it no longer
# reaches into `unfao.product` for defaults. These tests exercise the FAO product, so
# they pass FAO's facts, exactly as the manager does.
_PRODUCT = {
    "consumer_name": product.CONSUMER_DOCUMENT_NAME,
    "s_min": product.S_MIN,
}

_FIX = Path(__file__).resolve().parent / "fixtures" / "wire_contract"
_MANIFEST_NAME = "fixture_run_0__lr_ged_sb__manifest.json"
_SHARD_NAME = "fixture_run_0__lr_ged_sb__m000543.tap.zip"
_GIDS = [100001, 100002, 100003, 100004, 100005, 100006]


class FakeSourceStore:
    def __init__(self):
        self._records = [
            ("f-shard", {**sel.HOP_A_SHARD_FILTERS, "name": _SHARD_NAME}, (_FIX / _SHARD_NAME).read_bytes()),
            ("f-manifest", {**sel.HOP_A_MANIFEST_FILTERS, "name": _MANIFEST_NAME}, (_FIX / _MANIFEST_NAME).read_bytes()),
        ]

    def latest_file_id(self, filters):
        for file_id, meta, _ in reversed(self._records):
            if all(meta.get(k) == v for k, v in filters.items()):
                return file_id
        return None

    def download(self, file_id):
        return next(b for i, _, b in self._records if i == file_id)


class FakeLease:
    """Trivial lease: preloaded values, for failure-path tests."""

    def __init__(self, run_id, frame, headers):
        self.run_id = run_id
        self._value = (frame, headers)

    def load(self):
        return self._value


class UploadLog:
    def __init__(self):
        self.calls = []

    def upload(self, file_path, **kwargs):
        self.calls.append({"file": Path(file_path).name, **kwargs})


def _synthetic_lookup() -> pa.Table:
    return pa.table(
        {
            "priogrid_gid": pa.array(_GIDS, pa.int64()),
            "pg_xcoord": pa.array([10.25, 10.75, 11.25, 11.75, 12.25, 12.75], pa.float64()),
            "pg_ycoord": pa.array([5.25, 5.25, 5.25, 5.75, 5.75, 5.75], pa.float64()),
            "country_iso_a3": pa.array(["AAA", "AAA", "AAA", "BBB", "BBB", None]).dictionary_encode(),
            "admin1_gaul1_code": pa.array([11, 11, 12, 21, 21, None], pa.int64()),
            "admin1_gaul1_name": pa.array(["A-one", "A-one", "A-two", "B-one", "B-one", None]).dictionary_encode(),
            "admin1_gaul0_code": pa.array([1, 1, 1, 2, 2, None], pa.int64()),
            "admin1_gaul0_name": pa.array(["Aland", "Aland", "Aland", "Bland", "Bland", None]).dictionary_encode(),
            "admin2_gaul2_code": pa.array([111, 112, 121, 211, 212, None], pa.int64()),
            "admin2_gaul2_name": pa.array(["A-1-1", "A-1-2", "A-2-1", "B-1-1", "B-1-2", None]).dictionary_encode(),
        }
    )


def _leases():
    """Real leases through the real resolver — the full inbound chain."""
    return sel.resolve_run(
        FakeSourceStore(),
        expected_targets=["lr_ged_sb"],
        expected_ensemble="fixture_ensemble",
    )


def _fixture_frame_and_headers():
    return _leases()["lr_ged_sb"].load()


def test_interlock_default_config_makes_zero_store_calls(tmp_path):
    # (d) — the default configuration is provably unable to touch the bucket.
    log = UploadLog()
    summary = sink.deliver_run(
        _leases(), lookup=_synthetic_lookup(), staging_dir=tmp_path, **_PRODUCT, store=log
    )
    assert product.UPLOAD_ENABLED is False
    assert summary["uploaded"] is False
    assert log.calls == []  # ZERO store calls (§11.4)
    assert (Path(summary["staging_dir"]) / summary["manifest"]).exists()
    assert Path(summary["staging_dir"]).name == "fixture_run_0"  # per-run_id subdir


def test_gate_fires_before_any_write(tmp_path):
    # (a) — a collapsed payload raises and NOTHING is staged.
    values = np.zeros((6, 4), dtype=np.float32)  # every row draw-degenerate
    frame = build_prediction_frame(
        values, np.full(6, 543, dtype=np.int64), np.array(_GIDS, dtype=np.int64)
    )
    _, headers = _fixture_frame_and_headers()
    with pytest.raises(DrawsCollapseError):
        sink.deliver_run(
            {"lr_ged_sb": FakeLease("fixture_run_0", frame, headers)},
            lookup=_synthetic_lookup(),
            staging_dir=tmp_path, **_PRODUCT,
        )
    assert list(tmp_path.iterdir()) == []  # gate first: no bytes staged, no subdir


def test_upload_order_and_document_fields(tmp_path):
    # (b) + (c) — order shards → sidecar → manifest LAST; §4.1a fields on every doc.
    log = UploadLog()
    summary = sink.deliver_run(
        _leases(),
        lookup=_synthetic_lookup(),
        staging_dir=tmp_path, **_PRODUCT,
        store=log,
        upload_enabled=True,  # explicit declaration (test scope only)
    )
    assert summary["uploaded"] is True
    doc_types = [c["doc_type"] for c in log.calls]
    assert doc_types == [
        "sampled_forecast_shard",
        "sampled_forecast_sidecar",
        "sampled_forecast_manifest",  # LAST: the commit marker (§4.2)
    ]
    for call in log.calls:
        assert call["name"] == "un_fao"  # the §4.1a pin — the F1 fix
        assert call["category"] == "forecast" and call["loa"] == "pgm"
    assert log.calls[0]["targets"] == ["lr_ged_sb"]
    assert log.calls[-1]["targets"] == ["lr_ged_sb"]


def test_ragged_run_refused_and_first_target_released(tmp_path):
    frame, headers = _fixture_frame_and_headers()
    other = dict(headers[0])
    other["run_id"] = "another_run"
    with pytest.raises(sink.SinkError, match="disagree on run_id"):
        sink.deliver_run(
            {
                "lr_ged_sb": FakeLease("fixture_run_0", frame, headers),
                "lr_ged_ns": FakeLease("fixture_run_0", frame, [other]),
            },
            lookup=_synthetic_lookup(),
            staging_dir=tmp_path, **_PRODUCT,
        )
    # first target's shards were staged (harmless: no manifest = invisible, §4.2)
    staged = list((tmp_path / "fixture_run_0").iterdir())
    assert all("manifest" not in p.name for p in staged)


def test_targets_disagreeing_on_cells_refused(tmp_path):
    frame, headers = _fixture_frame_and_headers()
    small = build_prediction_frame(
        frame.values[:5], np.asarray(frame.index.time)[:5], np.asarray(frame.index.unit)[:5]
    )
    with pytest.raises(sink.SinkError, match="cell set"):
        sink.deliver_run(
            {
                "lr_ged_sb": FakeLease("fixture_run_0", frame, headers),
                "lr_ged_ns": FakeLease("fixture_run_0", small, headers),
            },
            lookup=_synthetic_lookup(),
            staging_dir=tmp_path, **_PRODUCT,
        )


def test_e2e_byte_parity_with_the_fixture(tmp_path):
    # (e) — the anti-corruption proof (§10): fixture Track-A in → fixture Hop-B out,
    # byte for byte, through resolve → lease → streamed sink. Toolchain-pinned.
    import pyarrow

    assert pyarrow.__version__ == "16.1.0", (
        f"pinned toolchain violated (fixture README): found {pyarrow.__version__}."
    )
    summary = sink.deliver_run(
        _leases(), lookup=_synthetic_lookup(), staging_dir=tmp_path, **_PRODUCT
    )
    staging = Path(summary["staging_dir"])
    for name in (
        "fixture_run_0__lr_ged_sb__m000543.arrow.parquet",
        "fixture_run_0__sidecar.parquet",
        "fixture_run_0__manifest.json",
    ):
        assert (staging / name).read_bytes() == (_FIX / name).read_bytes(), name
    manifest = json.loads((staging / summary["manifest"]).read_text())
    assert manifest["shards"][0]["sha256"] == hashlib.sha256(
        (_FIX / "fixture_run_0__lr_ged_sb__m000543.arrow.parquet").read_bytes()
    ).hexdigest()
