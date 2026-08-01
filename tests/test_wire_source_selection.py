"""Contract-mode Hop-A inbound (wire/source_selection.py) — resolve + lease model:
dict-backed fake store serving the golden fixture; cheap resolution with pinned
file_ids, lazy verified+curated loading, loud refusals."""

import json
from pathlib import Path

import pytest

from views_postprocessing.contract.wire import source_selection as sel

_FIX = Path(__file__).resolve().parent / "fixtures" / "wire_contract"
_MANIFEST_NAME = "fixture_run_0__lr_ged_sb__manifest.json"
_SHARD_NAME = "fixture_run_0__lr_ged_sb__m000543.tap.zip"


class FakeStore:
    """The two-method source port over (file_id, metadata, payload) records."""

    def __init__(self, records):
        self._records = records  # newest LAST
        self.downloads = []

    def latest_file_id(self, filters):
        for file_id, meta, _ in reversed(self._records):
            if all(meta.get(k) == v for k, v in filters.items()):
                return file_id
        return None

    def download(self, file_id):
        self.downloads.append(file_id)
        return next(b for i, _, b in self._records if i == file_id)


def _fixture_store() -> FakeStore:
    return FakeStore(
        [
            ("f-shard", {**sel.HOP_A_SHARD_FILTERS, "name": _SHARD_NAME}, (_FIX / _SHARD_NAME).read_bytes()),
            ("f-manifest", {**sel.HOP_A_MANIFEST_FILTERS, "name": _MANIFEST_NAME}, (_FIX / _MANIFEST_NAME).read_bytes()),
        ]
    )


def _resolve(store=None, **overrides):
    kwargs = dict(
        expected_targets=["lr_ged_sb"], expected_ensemble="fixture_ensemble"
    )
    kwargs.update(overrides)
    return sel.resolve_run(store or _fixture_store(), **kwargs)


# --- resolution: cheap, pinned, complete -------------------------------------------


def test_resolve_is_cheap_and_pins_file_ids():
    store = _fixture_store()
    leases = sel.resolve_run(
        store, expected_targets=["lr_ged_sb"], expected_ensemble="fixture_ensemble"
    )
    lease = leases["lr_ged_sb"]
    assert lease.run_id == "fixture_run_0"
    assert lease.shard_file_ids == {_SHARD_NAME: "f-shard"}
    assert store.downloads == ["f-manifest"]  # manifests only — no shard bytes moved


def test_empty_store_refuses_loud():
    with pytest.raises(sel.SourceSelectionError, match="nothing has been published"):
        _resolve(FakeStore([]))


def test_missing_declared_target_refuses_at_resolve():
    with pytest.raises(sel.SourceSelectionError, match="lr_ged_ns.*awaiting all"):
        _resolve(expected_targets=["lr_ged_sb", "lr_ged_ns"])


def test_manifested_shard_missing_refuses_at_resolve():
    store = _fixture_store()
    store._records = [r for r in store._records if r[0] != "f-shard"]
    with pytest.raises(sel.SourceSelectionError, match="torn run"):
        _resolve(store)


def test_manifest_name_content_mismatch_refuses_loud():
    manifest = json.loads((_FIX / _MANIFEST_NAME).read_text())
    store = _fixture_store()
    store._records.insert(
        0,
        (
            "f-imposter",
            {**sel.HOP_A_MANIFEST_FILTERS, "name": "fixture_run_0__lr_ged_ns__manifest.json"},
            json.dumps(manifest).encode(),  # still claims target lr_ged_sb
        ),
    )
    with pytest.raises(sel.SourceSelectionError, match="content is identity"):
        _resolve(store, expected_targets=["lr_ged_sb", "lr_ged_ns"])


# --- lease loading: verified, identity-checked, curated ----------------------------


def test_lease_load_assembles_the_fixture():
    frame, headers = _resolve()["lr_ged_sb"].load()
    assert frame.n_rows == 6 and frame.sample_count == 4
    assert headers[0]["run_id"] == "fixture_run_0"


def test_lease_load_downloads_by_pinned_id_only():
    store = _fixture_store()
    leases = sel.resolve_run(
        store, expected_targets=["lr_ged_sb"], expected_ensemble="fixture_ensemble"
    )
    store.downloads.clear()
    leases["lr_ged_sb"].load()
    assert store.downloads == ["f-shard"]  # by id — never re-filtered


def test_wrong_declared_ensemble_refuses_at_load():
    leases = _resolve(expected_ensemble="rusty_bucket")
    with pytest.raises(sel.SourceSelectionError, match="rusty_bucket.*never falls back"):
        leases["lr_ged_sb"].load()


def test_lease_applies_declared_curation():
    leases = _resolve(excluded_gids=frozenset({100006}))
    frame, _ = leases["lr_ged_sb"].load()
    assert frame.n_rows == 5  # the declared exclusion is gone from the product frame
    from views_postprocessing.contract.frame_extraction import cells_of

    assert 100006 not in cells_of(frame)


def test_lease_coverage_expectation_fails_loud():
    from views_postprocessing.delivery.coverage import CoverageError

    leases = _resolve(expected_cells=7)  # fixture has 6
    with pytest.raises(CoverageError):
        leases["lr_ged_sb"].load()


def test_selection_filters_are_golden_strings():
    assert sel.HOP_A_SHARD_FILTERS == {"category": "forecast", "type": "sampled_forecast_shard"}
    assert sel.HOP_A_MANIFEST_FILTERS == {"category": "forecast", "type": "sampled_forecast_manifest"}
    assert sel.HOP_A_MANIFEST_NAME_TEMPLATE == "{run_id}__{target}__manifest.json"
