"""End-to-end input-integrity suite (epic #51) — the integration layer above each
story's primitives unit tests.

``UNFAOPostProcessorManager`` cannot be instantiated here (it needs views-pipeline-core
+ Appwrite env — register C-40), so each test drives the **delivery invariant** directly
and proves the guard fires.

**These tests feed primitives, deliberately (#151).** Until S3 they built synthetic
pandas frames and pushed them through ``unfao/extraction.py`` to reach the invariants.
That mirrored a delivery chain which no longer exists: the rules in
``views_postprocessing/delivery/`` are *representation-free* — they take a set of cell
ids, an array of months, and scalars — and the live delivery reaches them from a
``views_frames.FeatureFrame`` via ``frame_extraction``, never from pandas. Feeding them
pandas was testing a fiction and holding the last pandas import in this file hostage to
it.

Where the representation-specific halves are covered instead:

    frame -> primitives      tests/test_frame_extraction.py
    arrow table -> counts    tests/test_historical_builder.py  (unmapped_cell_count)
    store doc -> identity    tests/test_store_metadata.py      (file_metadata)

    S1 coverage           _check_coverage                assert_complete_coverage
    S2 observed range     _read_historical_frame         fabricated_months
    S3 forecast identity  RE-HOMED to the wire layer (#150) — the rule "refuse a forecast
                          that is not the launched ensemble's" now lives in
                          `wire/source_selection.py:73-81`, checked per shard header
                          against DECLARED provenance rather than one document's metadata
                          field. Covered by
                          `test_wire_source_selection.py::test_wrong_declared_ensemble_refuses_at_load`.
    S4 land_gaul          _check_coverage                assert_no_excluded_cells
    S5 provenance         _historical_frame_description  build_provenance
"""

import json

import numpy as np
import pytest

from views_postprocessing.delivery import coverage, observed_range, provenance


# S1 — coverage (C-34) --------------------------------------------------------------
def test_s1_coverage_correct_count_passes():
    assert coverage.assert_complete_coverage({1, 2, 3}, 3, label="historical") is None


def test_s1_coverage_under_and_over_raise():
    cells = {1, 2, 3}
    with pytest.raises(coverage.CoverageError, match="under-coverage"):
        coverage.assert_complete_coverage(cells, 4)
    with pytest.raises(coverage.CoverageError, match="over-coverage"):
        coverage.assert_complete_coverage(cells, 2)


# S2 — observed range (C-26) --------------------------------------------------------
def test_s2_months_beyond_the_boundary_are_identified_as_fabricated():
    """The producer observed through 101; the request was padded to 103.

    The padding must be identified so it is dropped rather than delivered to the
    partner as observed zeros. Dropping itself is the representation's job — see
    `test_frame_extraction.py::drop_months_above`.
    """
    requested = np.array([100, 101, 102, 103], dtype=np.int64)
    fabricated = observed_range.fabricated_months(requested, last_valid_month_id=101)
    assert set(fabricated.tolist()) == {102, 103}


def test_s2_nothing_is_fabricated_when_the_request_stops_at_the_boundary():
    requested = np.array([100, 101], dtype=np.int64)
    assert observed_range.fabricated_months(requested, last_valid_month_id=101).size == 0


# S3 — forecast identity: RE-HOMED to the wire layer (#150) -------------------------
# The invariant is neither gone nor weaker; it moved to where the evidence is.
# `TargetLease.load()` checks EVERY shard header's declared `provenance.ensemble`
# against the launched ensemble (`wire/source_selection.py:73-81`), so identity is
# established from the artifact's own content rather than from one store document's
# metadata field, and per shard rather than once per run.
# Exercised by `test_wire_source_selection.py::test_wrong_declared_ensemble_refuses_at_load`.


# S4 — land_gaul exclusions (C-30) --------------------------------------------------
def test_s4_injected_unassigned_cell_crashes_loud():
    # 62356 is a real sub-Antarctic gid in the land_gaul exclusion manifest.
    excluded = coverage.excluded_for("land_gaul")
    with pytest.raises(coverage.CoverageError, match="62356"):
        coverage.assert_no_excluded_cells({1, 2, 62356}, excluded, label="forecast")


def test_s4_clean_land_gaul_delivery_passes():
    assert coverage.assert_no_excluded_cells({1, 2, 3}, coverage.excluded_for("land_gaul")) is None


# S5 — provenance (C-15) ------------------------------------------------------------
def test_s5_upload_description_carries_structured_provenance():
    prov = provenance.build_provenance(
        lookup_version="v1.4.0",
        region="land_gaul",
        expected_cell_count=coverage.expected_for("land_gaul"),
        actual_cell_count=3,
        unmapped_count=0,
        observed_through=559,
    )
    description = f"Enriched ... provenance={json.dumps(prov, separators=(',', ':'))}"

    # the consumer can recover the structured fields from the description carrier
    payload = json.loads(description.split("provenance=", 1)[1])
    assert payload["lookup_version"] == "v1.4.0"
    assert payload["region"] == "land_gaul"
    assert payload["expected_cell_count"] == 64_742
    assert payload["actual_cell_count"] == 3
    assert payload["unmapped_count"] == 0


def test_s5_provenance_records_unmapped_cells_when_present():
    """An unmapped cell is counted for audit before the null-gate would reject it."""
    prov = provenance.build_provenance(
        lookup_version="v1",
        region="land_gaul",
        expected_cell_count=coverage.expected_for("land_gaul"),
        actual_cell_count=3,
        unmapped_count=1,
        observed_through=559,
    )
    assert prov["unmapped_count"] == 1
