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


def test_a_store_that_raises_keyerror_is_not_blamed_on_the_manifest():
    """A store fault must not be relabelled as a missing manifest entry.

    ``frames_for_target`` reads a ``KeyError`` from the fetch callback as *"this shard
    was never pinned"*. The lease's callback calls into the store, so before this guard
    a ``KeyError`` thrown anywhere inside the client — a response shape indexed with
    ``[]`` rather than ``.get()``, which is how C-99 happened one layer down — would
    surface as *"manifest lists shard X but its bytes were not provided"*, blaming the
    manifest for a store failure. ``raise ... from None`` would have discarded the
    traceback that said otherwise.

    The shard here IS pinned, so "not provided" would be a false diagnosis.
    """
    manifest = json.loads((_FIX / _MANIFEST_NAME).read_text())

    class KeyErroringStore:
        def download(self, file_id):
            raise KeyError("data")

    lease = sel.TargetLease(
        target=manifest["target"],
        manifest=manifest,
        shard_file_ids={entry["name"]: "pinned-id" for entry in manifest["shards"]},
        store=KeyErroringStore(),
        expected_ensemble="fixture_ensemble",
    )
    with pytest.raises(sel.SourceSelectionError) as excinfo:
        lease.load()
    message = str(excinfo.value)
    assert "store fault" in message, "the refusal must say where the fault is"
    assert "not provided" not in message, (
        "a store KeyError must not be reported as a missing manifest entry"
    )
    assert excinfo.value.__cause__ is not None, (
        "the store's own KeyError must be chained, not discarded"
    )


# --- C-113, the forecast leg: an unpinned region leaves evidence -------------------
#
# Found by review 2026-11-18. The managers' `_check_coverage` was fixed to call both
# gates unconditionally, but forecast coverage is asserted HERE, inside the lease's
# `load()`, behind two caller-side `if`s. For an unpinned region those `if`s were both
# false, so every target loaded with both gates skipped and NOTHING in the run log —
# the larger half of the defect the managers' fix claimed to have closed.


def test_an_unpinned_region_reports_both_skipped_gates_on_the_forecast_leg(caplog):
    import logging

    with caplog.at_level(logging.WARNING, logger="views_postprocessing.delivery.coverage"):
        leases = _resolve()  # no excluded_gids, no expected_cells: the unpinned region
        leases["lr_ged_sb"].load()
    messages = [r.getMessage() for r in caplog.records]
    assert any("exclusion-gate SKIPPED" in m for m in messages), messages
    assert any("count-gate SKIPPED" in m for m in messages), messages
    # Both name the leg, so a two-target run says which target was unchecked.
    assert all("forecast[lr_ged_sb]" in m for m in messages if "SKIPPED" in m), messages


def test_a_pinned_region_still_enforces_both_gates_and_reports_no_skip(caplog):
    import logging

    from views_postprocessing.delivery.coverage import CoverageError

    with caplog.at_level(logging.WARNING, logger="views_postprocessing.delivery.coverage"):
        leases = _resolve(excluded_gids=frozenset({100006}), expected_cells=5)
        leases["lr_ged_sb"].load()  # 6 cells, one excluded -> 5 delivered: passes
    assert not [r for r in caplog.records if "SKIPPED" in r.getMessage()]

    # The count gate still refuses when the pinned count does not match. This says
    # "count gate" and not "exclusion gate" on purpose: `drop_units` removes the
    # excluded cell on the line directly above the gates, so on THIS leg the
    # exclusion gate is a post-condition on that call and cannot fire from a
    # declared exclusion alone. An earlier version of this test claimed otherwise
    # and a guard audit disproved it by making the exclusion gate blind and keeping
    # the test green (2026-11-18, MF4). The exclusion gate's own refusal is tested
    # where it can actually fire: tests/test_delivery_coverage.py.
    leases = _resolve(excluded_gids=frozenset({100006}), expected_cells=6)
    with pytest.raises(CoverageError, match="under-coverage"):
        leases["lr_ged_sb"].load()


def test_the_exclusion_gate_is_a_post_condition_on_the_curation_it_follows():
    """What the exclusion gate is FOR on this leg: catching a `drop_units` that did
    not drop. Proven by feeding the gate the uncurated cell set directly, which is
    the state the gate exists to refuse.
    """
    from views_postprocessing.contract.frame_extraction import cells_of
    from views_postprocessing.delivery.coverage import (
        CoverageError,
        assert_no_excluded_cells,
    )

    leases = _resolve()  # no curation: the raw producer frame, 100006 included
    frame, _ = leases["lr_ged_sb"].load()
    assert 100006 in cells_of(frame)
    with pytest.raises(CoverageError, match="100006"):
        assert_no_excluded_cells(cells_of(frame), frozenset({100006}), label="forecast")


def test_the_gates_run_exclusion_before_count(monkeypatch):
    """The order is load-bearing and was stated only in a comment: a leaked island
    must name itself rather than arriving as "over-coverage by 1" (S4/C-30). A guard
    audit swapped the two calls with the whole suite green (2026-11-18, MF3).
    """
    from views_postprocessing.delivery import coverage as cov

    called = []
    monkeypatch.setattr(cov, "assert_no_excluded_cells", lambda *a, **k: called.append("exclusion"))
    monkeypatch.setattr(cov, "assert_complete_coverage", lambda *a, **k: called.append("count"))
    leases = _resolve(excluded_gids=frozenset({100006}), expected_cells=5)
    leases["lr_ged_sb"].load()
    assert called == ["exclusion", "count"]
