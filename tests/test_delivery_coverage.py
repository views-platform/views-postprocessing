"""Unit tests for the representation-free coverage invariant (S1 / C-34).

Pure primitives in, raise-or-pass out — no framework, no pandas.
"""

import json

import pytest

from tests.conftest import sibling_repo

from views_postprocessing.delivery.coverage import (
    EXPECTED_CELLS,
    CoverageError,
    RegionNotDeclaredError,
    assert_complete_coverage,
    assert_no_excluded_cells,
    excluded_for,
    expected_for,
)


def test_correct_count_passes():
    assert assert_complete_coverage({1, 2, 3}, 3) is None


def test_under_coverage_raises():
    with pytest.raises(CoverageError, match="under-coverage"):
        assert_complete_coverage({1, 2}, 3)


def test_over_coverage_raises():
    with pytest.raises(CoverageError, match="over-coverage"):
        assert_complete_coverage({1, 2, 3, 4}, 3)


def test_label_appears_in_message():
    with pytest.raises(CoverageError, match="forecast"):
        assert_complete_coverage(set(), 1, label="forecast")


def test_land_gaul_is_pinned():
    # 64,742 after datafactory #163 (ADR-043) supplemented 6 Azorean cells; was 64,736.
    assert expected_for("land_gaul") == 64_742
    assert EXPECTED_CELLS["land_gaul"] == 64_742


def test_a_declared_but_unpinned_region_has_no_target_and_does_not_raise():
    # africa_me_legacy is deliberately unpinned (ambiguous count). It must stay
    # launchable: the count gate reports a skip, it does not refuse.
    assert expected_for("africa_me_legacy") is None
    assert expected_for("does_not_exist") is None


def test_an_undeclared_region_is_refused_and_not_reported_as_unpinned():
    """C-113. ``expected_for(None)`` returned None, exactly like an unpinned region.

    The two must not share a representation: one means "this delivery has no
    completeness target, which we accept", the other means "nobody said what this
    delivery is supposed to cover". The second shipped as the first.
    """
    for undeclared in (None, "", "   ", 0, ["land_gaul"]):
        with pytest.raises(RegionNotDeclaredError, match="no region declared"):
            expected_for(undeclared)


def test_the_refusal_is_not_a_coverage_error():
    # Nothing was delivered wrongly; the question could not be asked. A caller
    # catching CoverageError to report a coverage failure must not catch this.
    assert not issubclass(RegionNotDeclaredError, CoverageError)
    with pytest.raises(RegionNotDeclaredError):
        expected_for(None)


# --- S4 / C-30: the GAUL-uncovered exclusion manifest -------------------------------


def test_land_gaul_exclusions_count_is_pinned():
    # land 64,818 − land_gaul 64,742 = 76 sub-Antarctic cells (was 82 pre-ADR-043).
    assert len(excluded_for("land_gaul")) == 76


def test_a_declared_but_unpinned_region_has_no_exclusions():
    # africa_me_legacy keeps its 5 ocean cells today — they must NOT be force-excluded.
    assert excluded_for("africa_me_legacy") == frozenset()
    assert excluded_for("does_not_exist") == frozenset()


def test_an_undeclared_region_is_refused_by_the_exclusion_side_too():
    # C-113: this returned frozenset(), so an undeclared region curated nothing and
    # looked exactly like the region that is MEANT to curate nothing.
    for undeclared in (None, "", "  "):
        with pytest.raises(RegionNotDeclaredError, match="no region declared"):
            excluded_for(undeclared)


def test_known_sub_antarctic_gids_are_excluded():
    # Sample gids from register C-30 (and the africa_me ocean cells, a subset).
    for gid in (62356, 94776, 99027, 107733, 107742, 51078):
        assert gid in excluded_for("land_gaul")


def test_supplemented_azorean_cells_are_NOT_excluded():
    # The 6 cells datafactory #163 added to land_gaul must be delivered, not dropped.
    for gid in (182470, 183190, 183909, 183910, 186058, 186778):
        assert gid not in excluded_for("land_gaul")


def test_no_excluded_cells_passes_on_clean_delivery():
    assert assert_no_excluded_cells({1, 2, 3}, frozenset({999})) is None


def test_leaked_excluded_cell_raises_naming_the_gid():
    with pytest.raises(CoverageError, match="62356"):
        assert_no_excluded_cells({1, 62356, 3}, excluded_for("land_gaul"), label="forecast")


def test_no_excluded_cells_is_noop_when_region_unpinned():
    # Empty exclusion set (e.g. africa_me_legacy) never raises, even on ocean cells.
    assert assert_no_excluded_cells({62356, 94776}, excluded_for("africa_me_legacy")) is None


# --- C-113: a skipped gate must say so, and both gates must say it ------------------


def test_a_skipped_exclusion_gate_is_reported(caplog):
    """This skip was silent, while the count gate's was logged.

    Half the evidence that a delivery had been curated by nothing never reached the
    run log. Asserted on the WARNING record, not on the return, because returning
    None is what the old silent version did too.
    """
    with caplog.at_level("WARNING"):
        assert assert_no_excluded_cells({1, 2}, frozenset(), label="historical") is None
    assert any(
        r.levelname == "WARNING" and "exclusion-gate SKIPPED" in r.getMessage()
        and "historical" in r.getMessage()
        for r in caplog.records
    ), caplog.text


def test_a_skipped_count_gate_is_reported(caplog):
    # The count gate now owns the skip the managers used to each report themselves,
    # so it can be proven here without a manager or an Appwrite environment (C-40(a)).
    with caplog.at_level("WARNING"):
        assert assert_complete_coverage({1, 2}, None, label="forecast") is None
    assert any(
        r.levelname == "WARNING" and "count-gate SKIPPED" in r.getMessage()
        and "forecast" in r.getMessage()
        for r in caplog.records
    ), caplog.text


def test_a_pinned_region_still_enforces_both_gates():
    # The skip paths must not have made the gates themselves optional.
    with pytest.raises(CoverageError, match="under-coverage"):
        assert_complete_coverage({1, 2}, expected_for("land_gaul"), label="historical")
    with pytest.raises(CoverageError, match="62356"):
        assert_no_excluded_cells({62356}, excluded_for("land_gaul"), label="historical")


# Cross-check the frozen manifest against the live producer. This is the drift tripwire
# C-30 asks for, and since 2026-08-17 it RUNS IN CI: `run_pytest.yml` fetches
# views-datafactory, and both pgid lists below are tracked there. It backs a guarantee
# given to FAO in writing, so it must fail as an assertion rather than as a traceback —
# hence the gate names both files the body reads, not just the first.
_DATAFACTORY = sibling_repo("views-datafactory")
_DF = None if _DATAFACTORY is None else _DATAFACTORY / "src" / "datafactory_query"


@pytest.mark.skipif(
    _DF is None or not all((_DF / f"{n}_pgids.json").exists() for n in ("land", "land_gaul")),
    reason=(
        "views-datafactory checkout not found, or it does not carry both "
        "src/datafactory_query/{land,land_gaul}_pgids.json — set VIEWS_DATAFACTORY="
        "/path/to/views-datafactory, or place it alongside this repo. Both files are "
        "tracked upstream, so a plain checkout is enough (this runs in CI)"
    ),
)
def test_manifest_matches_datafactory_land_minus_land_gaul():
    land = {int(x) for x in json.loads((_DF / "land_pgids.json").read_text())}
    land_gaul = {int(x) for x in json.loads((_DF / "land_gaul_pgids.json").read_text())}
    assert excluded_for("land_gaul") == frozenset(land - land_gaul)
    assert EXPECTED_CELLS["land_gaul"] == len(land_gaul)
