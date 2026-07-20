"""Contract-mode Hop-A inbound (wire/source_selection.py) — dict-backed fake store
serving the golden fixture; selection policy, await-all-targets, declared identity."""

import json
from pathlib import Path

import pytest

from views_postprocessing.unfao.wire import source_selection as sel

_FIX = Path(__file__).resolve().parent / "fixtures" / "wire_contract"
_MANIFEST_NAME = "fixture_run_0__lr_ged_sb__manifest.json"
_SHARD_NAME = "fixture_run_0__lr_ged_sb__m000543.tap.zip"


class FakeStore:
    """The three-method store port over a dict of (metadata, bytes) records."""

    def __init__(self, records):
        # records: list of (file_id, metadata_dict, payload_bytes); newest LAST.
        self._records = records
        self.calls = []

    def latest_file_id(self, filters):
        self.calls.append(("latest_file_id", dict(filters)))
        for file_id, meta, _ in reversed(self._records):
            if all(meta.get(k) == v for k, v in filters.items()):
                return file_id
        return None

    def file_metadata(self, file_id):
        return next(m for i, m, _ in self._records if i == file_id)

    def download(self, file_id):
        return next(b for i, _, b in self._records if i == file_id)


def _fixture_store() -> FakeStore:
    return FakeStore(
        [
            (
                "f-shard",
                {**sel.HOP_A_SHARD_FILTERS, "name": _SHARD_NAME},
                (_FIX / _SHARD_NAME).read_bytes(),
            ),
            (
                "f-manifest",
                {**sel.HOP_A_MANIFEST_FILTERS, "name": _MANIFEST_NAME},
                (_FIX / _MANIFEST_NAME).read_bytes(),
            ),
        ]
    )


def test_happy_path_assembles_the_fixture_run():
    result = sel.fetch_run(
        _fixture_store(),
        expected_targets=["lr_ged_sb"],
        expected_ensemble="fixture_ensemble",
    )
    frame, headers = result["lr_ged_sb"]
    assert frame.n_rows == 6 and frame.sample_count == 4
    assert headers[0]["run_id"] == "fixture_run_0"


def test_empty_store_refuses_loud():
    with pytest.raises(sel.SourceSelectionError, match="nothing has been published"):
        sel.fetch_run(
            FakeStore([]), expected_targets=["lr_ged_sb"], expected_ensemble="e"
        )


def test_missing_declared_target_refuses_loud():
    # The store has lr_ged_sb only; the delivery declares two targets (§4.2a).
    with pytest.raises(sel.SourceSelectionError, match="lr_ged_ns.*awaiting all"):
        sel.fetch_run(
            _fixture_store(),
            expected_targets=["lr_ged_sb", "lr_ged_ns"],
            expected_ensemble="fixture_ensemble",
        )


def test_wrong_declared_ensemble_refuses_loud():
    with pytest.raises(sel.SourceSelectionError, match="rusty_bucket.*never falls back"):
        sel.fetch_run(
            _fixture_store(),
            expected_targets=["lr_ged_sb"],
            expected_ensemble="rusty_bucket",
        )


def test_manifested_shard_missing_from_store_refuses_loud():
    store = _fixture_store()
    store._records = [r for r in store._records if r[0] != "f-shard"]
    with pytest.raises(sel.SourceSelectionError, match="torn run"):
        sel.fetch_run(
            store, expected_targets=["lr_ged_sb"], expected_ensemble="fixture_ensemble"
        )


def test_manifest_name_content_mismatch_refuses_loud():
    # A second target's manifest name serving OTHER content: names are locators,
    # content is identity (§3.3).
    manifest = json.loads((_FIX / _MANIFEST_NAME).read_text())
    imposter_name = "fixture_run_0__lr_ged_ns__manifest.json"
    store = _fixture_store()
    store._records.insert(
        0,
        (
            "f-imposter",
            {**sel.HOP_A_MANIFEST_FILTERS, "name": imposter_name},
            json.dumps(manifest).encode(),  # still claims target lr_ged_sb
        ),
    )
    with pytest.raises(sel.SourceSelectionError, match="content is identity"):
        sel.fetch_run(
            store,
            expected_targets=["lr_ged_sb", "lr_ged_ns"],
            expected_ensemble="fixture_ensemble",
        )


def test_selection_filters_are_golden_strings():
    # Pinned to pipeline-core's shipped publisher constants (re-verified 2026-07-20).
    assert sel.HOP_A_SHARD_FILTERS == {"category": "forecast", "type": "sampled_forecast_shard"}
    assert sel.HOP_A_MANIFEST_FILTERS == {"category": "forecast", "type": "sampled_forecast_manifest"}
    assert sel.HOP_A_MANIFEST_NAME_TEMPLATE == "{run_id}__{target}__manifest.json"
