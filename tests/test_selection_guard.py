"""The Hop-A legacy transition guard (ADR-013 §11.4) — retired, and pinned as retired.

**What these tests used to do.** Until #149 they pinned a golden string in the
manager: `LEGACY_FORECAST_FILTERS = {"category": "forecast", "type": "ensemble"}`.
Pinning the legacy `type` was what made pipeline-core#269's contract uploads
(`sampled_forecast_*`) unselectable by the deployed legacy reader — the
disjointness §11.4's sequencing constraint turned on.

**Why they changed.** §11.4 required that guard live *before the first contract
artifact was uploaded*; both guards merged 2026-07-15 and run-0 uploaded
2026-07-27, so the constraint was satisfied and the transition closed. #149 then
deleted the reader the guard protected. A golden string pinning deleted code is
not a guarantee — it is a test that can only ever fail.

**So the guarantee moved rather than lapsed.** The historical fact now lives where
facts about the contract belong: ADR-013's post-adoption record. These tests pin
it *there*, and add the invariant that replaces it — the legacy selection must not
come back.

Source-level, like the design-contract tests: the manager pulls the full
pipeline-core framework and cannot be imported in every test environment.
"""

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SRC = (_ROOT / "views_postprocessing" / "unfao" / "managers" / "unfao.py").read_text()
_ADR = (_ROOT / "docs" / "ADRs" / "013_sampled_forecast_wire_contract.md").read_text()


def test_the_legacy_reader_is_gone():
    """The retired reader must not creep back — this is the live invariant now.

    Note what is NOT asserted: `_ContractStorePort.latest_file_id` forwards a
    `filters` argument, and that is correct — it is the DIP adapter through which
    `wire/source_selection` runs its *manifest* queries. The defect was never
    "filters exist"; it was a hardcoded category-scoped filter selecting the newest
    upload in the whole bucket. That is what the next test pins.
    """
    assert "LEGACY_FORECAST_FILTERS" not in _SRC, (
        "LEGACY_FORECAST_FILTERS is back in the manager. The Hop-A legacy reader was "
        "retired in #149; forecasts are selected by run manifest, never by a category "
        "filter over the whole bucket."
    )


def test_no_category_only_selection_anywhere_in_the_manager():
    """C-25's original hazard: 'newest category=forecast wins regardless of producer'.

    Manifest selection makes it structurally impossible, but an inline filter dict
    on any store call would reintroduce it.
    """
    assert not re.search(r'get_latest_file_id\(\s*filters\s*=\s*\{', _SRC), (
        "inline selection-filter dict in the manager — selection belongs to "
        "wire/source_selection, keyed on the run manifest."
    )


def test_the_retired_guard_is_recorded_in_the_adr():
    """The disjointness fact outlives the code that carried it.

    A future reader asking "how was the transition made safe?" must find the
    answer, and after #149 the only place it can live is the contract's own record.
    """
    assert "Hop-A LEGACY READER IS RETIRED" in _ADR, (
        "ADR-013's post-adoption record does not record the Hop-A retirement — the "
        "§11.4 transition fact would have no home."
    )
    # The retired filter values, so the historical claim stays checkable.
    assert '{"category": "forecast", "type": "ensemble"}' in _ADR
    # And what made them safe: disjointness from the contract vocabulary.
    assert "sampled_forecast_shard" in _ADR


def test_hop_b_half_of_the_transition_rule_still_binds():
    """Retiring OUR reader must not be read as relaxing the consumer's obligation.

    §11.4 governs BOTH hops. views-faoapi's deployed selector is a separate
    deployment on its own schedule; nothing about #149 touches it.
    """
    assert "Its Hop-B clause" in _ADR and "still binds" in _ADR, (
        "the ADR must state that retiring the Hop-A reader leaves the Hop-B "
        "constraint intact — otherwise the entry reads as a blanket relaxation."
    )


def test_compact_description_fits_the_store_limit():
    """Run-0 lesson (2026-07-27): Appwrite's description attribute caps at 255
    chars; the old prose-prefixed provenance exceeded it and stranded the
    historical upload as an orphan file without a metadata document."""
    from views_postprocessing.delivery import provenance
    from views_postprocessing.delivery.provenance import DESCRIPTION_MAX, compact_description

    prov = provenance.build_provenance(
        lookup_version="land_gaul@272cdb01",
        region="land_gaul",
        expected_cell_count=64742,
        actual_cell_count=64742,
        unmapped_count=0,
    )
    text = compact_description(prov)
    assert len(text) <= DESCRIPTION_MAX
    assert "land_gaul@272cdb01" in text  # provenance survives, prose does not
