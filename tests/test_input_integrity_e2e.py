"""End-to-end input-integrity suite (S6 / epic #51) — the integration layer above each
story's primitives unit tests.

``UNFAOPostProcessorManager`` cannot be instantiated here (it needs views-pipeline-core +
Appwrite env — register C-40), so — exactly as ``test_validation.py`` does — each test
**replicates the delivery's extraction→invariant chain** on a synthetic frame and proves
the guard fires.

What these prove is the **invariants in** ``views_postprocessing/delivery/``, which is
why they survived #149 untouched: the rules are representation-free, so retiring the
pandas delivery changed which module *calls* them, not whether they hold. The mapping to
manager methods below is therefore informational, and updated for the post-#149 tree:

    S1 coverage          _check_coverage             cells_of  -> assert_complete_coverage
    S2 observed range    _read_historical_frame      months_of -> fabricated_months -> drop_months_above
    S3 forecast identity (RETIRED with the legacy reader, #149 — selection is by run
                          manifest; `delivery/identity.py` itself is retired in #150)
    S4 land_gaul         _check_coverage             cells_of  -> assert_no_excluded_cells
    S5 provenance        _historical_frame_description  build_provenance(<- cells_of/unmapped_cell_count)
"""

import json

import pandas as pd
import pytest

from views_postprocessing.delivery import coverage, identity, observed_range, provenance
from views_postprocessing.unfao import extraction
from views_postprocessing.unfao.gaul_schema import METADATA_COLS

_TIME_ID = "month_id"
_ENTITY_ID = "priogrid_gid"


def _delivery_frame(gids, months=(100, 101), *, unmapped_gids=()):
    """A synthetic delivery frame: MultiIndex (month, gid) + a pred col + the 9 GAUL cols."""
    rows = [(m, g) for m in months for g in gids]
    idx = pd.MultiIndex.from_tuples(rows, names=[_TIME_ID, _ENTITY_ID])
    df = pd.DataFrame({"pred_ln_sb_best": 0.0}, index=idx)
    for c in METADATA_COLS:
        df[c] = "X"
    if unmapped_gids:
        mask = df.index.get_level_values(_ENTITY_ID).isin(unmapped_gids)
        df.loc[mask, list(METADATA_COLS)] = None
    return df


class _FakeMetaResult:
    """Stands in for a DatastoreModule.get_file_metadata OperationResult (S3)."""

    def __init__(self, document):
        self._document = document

    def to_dict(self):
        return {"data": self._document, "code": "FOUND"}


# S1 — coverage (C-34) --------------------------------------------------------------
def test_s1_coverage_correct_count_passes_through_seam():
    df = _delivery_frame([1, 2, 3])
    cells = extraction.cells_of(df)
    assert coverage.assert_complete_coverage(cells, 3, label="historical") is None


def test_s1_coverage_under_and_over_raise_through_seam():
    df = _delivery_frame([1, 2, 3])
    cells = extraction.cells_of(df)
    with pytest.raises(coverage.CoverageError, match="under-coverage"):
        coverage.assert_complete_coverage(cells, 4)
    with pytest.raises(coverage.CoverageError, match="over-coverage"):
        coverage.assert_complete_coverage(cells, 2)


# S2 — observed range (C-26) --------------------------------------------------------
def test_s2_month_beyond_boundary_is_not_delivered_as_zero():
    # historical request padded to month 103; producer observed only through 101.
    df = _delivery_frame([1, 2], months=(100, 101, 102, 103))
    last_valid = 101
    fabricated = observed_range.fabricated_months(extraction.months_of(df), last_valid)
    assert set(fabricated.tolist()) == {102, 103}
    clipped = extraction.drop_months_above(df, last_valid)
    delivered = set(extraction.months_of(clipped).tolist())
    assert delivered == {100, 101}
    assert 102 not in delivered and 103 not in delivered  # not shipped as observed zero


# S3 — forecast identity (C-25) -----------------------------------------------------
def test_s3_decoy_forecast_file_is_rejected_through_seam():
    decoy = _FakeMetaResult({"name": "stray_model", "loa": "pgm", "category": "forecast"})
    selected = extraction.file_metadata(decoy)
    expected = {"name": "fatalities_ensemble", "loa": "pgm"}
    with pytest.raises(identity.ForecastIdentityError, match="stray_model"):
        identity.assert_forecast_identity(selected, expected)


def test_s3_matching_forecast_file_passes_through_seam():
    good = _FakeMetaResult({"name": "fatalities_ensemble", "loa": "pgm", "category": "forecast"})
    selected = extraction.file_metadata(good)
    expected = {"name": "fatalities_ensemble", "loa": "pgm"}
    assert identity.assert_forecast_identity(selected, expected) is None


# S4 — land_gaul exclusions (C-30) --------------------------------------------------
def test_s4_injected_unassigned_cell_crashes_loud():
    # 62356 is a real sub-Antarctic gid in the land_gaul exclusion manifest.
    df = _delivery_frame([1, 2, 62356])
    cells = extraction.cells_of(df)
    excluded = coverage.excluded_for("land_gaul")
    with pytest.raises(coverage.CoverageError, match="62356"):
        coverage.assert_no_excluded_cells(cells, excluded, label="forecast")


def test_s4_clean_land_gaul_delivery_passes():
    df = _delivery_frame([1, 2, 3])
    cells = extraction.cells_of(df)
    assert coverage.assert_no_excluded_cells(cells, coverage.excluded_for("land_gaul")) is None


# S5 — provenance (C-15) ------------------------------------------------------------
def test_s5_upload_description_carries_structured_provenance():
    df = _delivery_frame([1, 2, 3])
    # replica of _delivery_description's chain
    prov = provenance.build_provenance(
        lookup_version="v1.4.0",
        region="land_gaul",
        expected_cell_count=coverage.expected_for("land_gaul"),
        actual_cell_count=len(extraction.cells_of(df)),
        unmapped_count=extraction.unmapped_cell_count(df, METADATA_COLS),
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
    # a cell with null metadata is counted (audit value), before _validate would reject it.
    df = _delivery_frame([1, 2, 3], unmapped_gids=(3,))
    prov = provenance.build_provenance(
        lookup_version="v1",
        region="land_gaul",
        expected_cell_count=coverage.expected_for("land_gaul"),
        actual_cell_count=len(extraction.cells_of(df)),
        unmapped_count=extraction.unmapped_cell_count(df, METADATA_COLS),
    )
    assert prov["unmapped_count"] == 1
