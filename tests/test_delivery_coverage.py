"""Unit tests for the representation-free coverage invariant (S1 / C-34).

Pure primitives in, raise-or-pass out — no framework, no pandas.
"""

import json

import pytest

from tests.conftest import sibling_repo

from views_postprocessing.delivery.coverage import (
    EXPECTED_CELLS,
    CoverageError,
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


def test_unpinned_or_missing_region_is_none():
    # africa_me_legacy is deliberately unpinned (ambiguous count); None must not raise.
    assert expected_for("africa_me_legacy") is None
    assert expected_for(None) is None
    assert expected_for("does_not_exist") is None


# --- S4 / C-30: the GAUL-uncovered exclusion manifest -------------------------------


def test_land_gaul_exclusions_count_is_pinned():
    # land 64,818 − land_gaul 64,742 = 76 sub-Antarctic cells (was 82 pre-ADR-043).
    assert len(excluded_for("land_gaul")) == 76


def test_unpinned_region_has_no_exclusions():
    # africa_me_legacy keeps its 5 ocean cells today — they must NOT be force-excluded.
    assert excluded_for("africa_me_legacy") == frozenset()
    assert excluded_for(None) == frozenset()
    assert excluded_for("does_not_exist") == frozenset()


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
