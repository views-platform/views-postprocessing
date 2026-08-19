"""A run that dies mid-upload must say what it left behind (register C-105).

The contract already handles the **consumer's** side of a torn run correctly and by
design: the manifest is uploaded last, so an attempt that dies before it has no commit
marker and is invisible rather than half-visible (ADR-013 §4.2). Nothing partial is
served.

What was missing is our side. The objects that *did* land stay in the partner store,
and until 2026-08-19 nothing recorded that they had — an operator was left to diff the
bucket by hand. At run-0 scale a retry adds ~110 more under the same names.

**Nothing is deleted, deliberately.** Removing objects from a partner bucket is
irreversible and an operator decision; the neighbouring delete surface is its own open
question (C-58, views-pipeline-core #333, blocked on a test key). These tests pin the
part this repository can honestly own: turning an invisible mess into a documented one.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import pyarrow as pa

from views_postprocessing.contract.frames import build_prediction_frame
from views_postprocessing.contract.gaul_schema import CODE_COLS, COORD_COLS, METADATA_COLS
from views_postprocessing.contract.wire import sink
from views_postprocessing.unfao import product

_GIDS = [100001, 100002, 100003, 100004, 100005, 100006]


class FakeLease:
    """Preloaded values — this file tests the upload phase, not the inbound chain."""

    def __init__(self, run_id, frame, headers):
        self.run_id = run_id
        self._value = (frame, headers)

    def load(self):
        return self._value


def _synthetic_lookup() -> pa.Table:
    """A lookup covering exactly `_GIDS`, built from the declared schema.

    Derived from `gaul_schema` rather than copied as a literal table: the columns are
    the contract's, and a table hand-written here would drift from it silently. Built
    locally rather than imported from another test module — reaching into a sibling
    test's private helper couples two files that should be able to change apart.
    """
    columns = {"priogrid_gid": pa.array(_GIDS, pa.int64())}
    for col in METADATA_COLS:
        if col in COORD_COLS:
            columns[col] = pa.array([10.25 + i for i in range(len(_GIDS))], pa.float64())
        elif col in CODE_COLS:
            columns[col] = pa.array(list(range(1, len(_GIDS) + 1)), pa.int64())
        else:
            columns[col] = pa.array([f"{col}-{i}" for i in range(len(_GIDS))])
    return pa.table(columns)
_PRODUCT = {"consumer_name": product.CONSUMER_DOCUMENT_NAME, "s_min": product.S_MIN}


class FailAfter:
    """Uploads `n` objects, then refuses — the C-79 shape mid-run."""

    def __init__(self, n: int):
        self.n = n
        self.calls: list[str] = []

    def upload(self, file_path, **kwargs):
        if len(self.calls) >= self.n:
            raise RuntimeError("store said no")
        self.calls.append(Path(file_path).name)
        return f"id-{len(self.calls)}"


def _one_target_leases():
    values = np.tile(np.array([[1.0, 2.0, 3.0, 4.0]], dtype=np.float32), (6, 1))
    time = np.full(6, 543, dtype=np.int64)
    unit = np.array(_GIDS, dtype=np.int64)
    frame = build_prediction_frame(values, time, unit)
    headers = [{
        "run_id": "fixture_run_0", "target": "lr_ged_sb", "time_id": 543,
        "sample_count": 4, "provenance": {"ensemble": "fixture_ensemble"},
    }]
    return {"lr_ged_sb": FakeLease("fixture_run_0", frame, headers)}


def _deliver(store, tmp_path):
    return sink.deliver_run(
        _one_target_leases(), lookup=_synthetic_lookup(), staging_dir=tmp_path,
        **_PRODUCT, store=store, upload_enabled=True,
    )


def test_a_torn_run_refuses_and_names_what_already_landed(tmp_path):
    store = FailAfter(1)  # the shard lands; the sidecar does not
    with pytest.raises(sink.TornRunError) as excinfo:
        _deliver(store, tmp_path)
    message = str(excinfo.value)
    assert "TORN" in message
    assert "fixture_run_0" in message, "the refusal must name the run"
    assert store.calls[0] in message, (
        "the refusal must name the objects already in the partner store; without them "
        "an operator has to diff the bucket by hand (C-105)"
    )
    assert "id-1" in message, "and their file ids, so they can be found again"


def test_it_says_how_many_of_how_many(tmp_path):
    store = FailAfter(1)
    with pytest.raises(sink.TornRunError) as excinfo:
        _deliver(store, tmp_path)
    # one shard + sidecar + manifest = 3 objects for this single-target run
    assert "1 of 3" in str(excinfo.value)


def test_it_says_the_consumer_is_unaffected_and_nothing_was_removed(tmp_path):
    """Both halves matter: no partial serve, and no silent cleanup either."""
    with pytest.raises(sink.TornRunError) as excinfo:
        _deliver(FailAfter(1), tmp_path)
    message = str(excinfo.value)
    assert "almost certainly" in message and "cannot see this run" in message, (
        "an operator's first question is whether the partner is being served garbage. "
        "The §4.2 commit marker means almost certainly not — but the code cannot KNOW "
        "it, because a manifest upload can fail after the store committed the document. "
        "Asserting it categorically would steer a re-run that duplicates every object."
    )
    assert "NOT removed" in message, (
        "the refusal must be explicit that it deleted nothing — a reader who assumes "
        "cleanup happened will not go looking"
    )
    assert "correction_procedure.md" in message and "C-105" in message


def test_a_failure_on_the_manifest_is_still_torn(tmp_path):
    """The last upload is the commit marker; losing it is the canonical torn run."""
    store = FailAfter(2)  # shard + sidecar land, manifest does not
    with pytest.raises(sink.TornRunError) as excinfo:
        _deliver(store, tmp_path)
    assert "2 of 3" in str(excinfo.value)


def test_a_clean_run_reports_no_tear(tmp_path):
    store = FailAfter(99)
    summary = _deliver(store, tmp_path)
    assert summary["uploaded"] is True
    assert summary["manifest_file_id"] == "id-3"
    assert len(store.calls) == 3


def test_the_object_that_failed_is_named_as_the_likeliest_orphan(tmp_path):
    """The failing object is the one most likely to be an orphan, and it is not in the
    confirmed list — because the list only holds uploads that returned.

    `_ContractStorePort.upload` raises precisely in the case its own comment documents:
    the store "RETURNS success=False with the file already uploaded". So the object that
    failed is the C-79 shape, sitting in the bucket with no metadata document. Listing
    only the successes and calling it what remains would send an operator past the very
    orphan this exists to surface.
    """
    store = FailAfter(1)
    with pytest.raises(sink.TornRunError) as excinfo:
        _deliver(store, tmp_path)
    message = str(excinfo.value)
    assert "MAY ALSO HAVE LANDED" in message
    assert "C-79" in message, "and say which shape to look for"
    # the sidecar is what failed here; it must appear even though it is not "confirmed"
    assert "sidecar" in message


def test_a_failure_on_the_very_first_upload_does_not_claim_an_empty_list(tmp_path):
    """The commonest infrastructure failure: credentials expire, upload #1 refuses.

    The first draft printed "Already in the partner store, and NOT removed: ." — an
    empty list with a dangling period, presented as a bucket to audit.
    """
    with pytest.raises(sink.TornRunError) as excinfo:
        _deliver(FailAfter(0), tmp_path)
    message = str(excinfo.value)
    assert "Nothing is confirmed in the partner store" in message
    assert "NOT removed: ." not in message, "no dangling empty list"
    # even here the failing object may have landed, so the caveat must still be present
    assert "MAY ALSO HAVE LANDED" in message


def test_a_tear_is_not_a_malformed_run(tmp_path):
    """Opposite retry semantics: SinkError means do-not-retry, a tear is transient."""
    with pytest.raises(sink.TornRunError) as excinfo:
        _deliver(FailAfter(1), tmp_path)
    assert not isinstance(excinfo.value, sink.SinkError), (
        "TornRunError must not share a base with the malformed-run family, or an "
        "orchestration layer treating SinkError as do-not-retry would silently swallow "
        "store outages — and test_hop_b_sink_e2e already asserts SinkError for malformed"
    )
