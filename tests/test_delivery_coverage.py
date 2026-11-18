"""Unit tests for the representation-free coverage invariant (S1 / C-34).

Pure primitives in, raise-or-pass out — no framework, no pandas.
"""

import json

import pytest

from tests.conftest import sibling_repo

from views_postprocessing.delivery.coverage import (
    EXPECTED_CELLS,
    KNOWN_REGIONS,
    CoverageError,
    RegionNotDeclaredError,
    UnknownRegionError,
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


def test_an_unrecognised_region_is_refused_not_treated_as_unpinned():
    """C-113 one level in: `expected_for("does_not_exist")` used to return None.

    This test asserted that return value until 2026-11-18 — it pinned the defect.
    A name this delivery does not recognise is not the supported unpinned case: it
    misses both dictionary lookups, so BOTH gates skip and the delivery reports
    itself as a configuration someone chose. One mistyped letter did that.
    """
    for unknown in ("does_not_exist", "lnd_gaul", "land_gaul ", "LAND_GAUL"):
        with pytest.raises(UnknownRegionError, match="not one this delivery recognises"):
            expected_for(unknown)


def test_the_two_region_refusals_are_different_faults():
    # Different fixes: add the config key, versus correct a name or declare a region.
    # Neither is a CoverageError — nothing was delivered wrongly in either case.
    assert not issubclass(UnknownRegionError, RegionNotDeclaredError)
    assert not issubclass(RegionNotDeclaredError, UnknownRegionError)
    assert not issubclass(UnknownRegionError, CoverageError)


def test_every_pinned_region_is_a_known_region():
    # A region pinned in either table but absent from KNOWN_REGIONS would be
    # unreachable: `_declared` refuses it before the lookup runs.
    from views_postprocessing.delivery.coverage import EXCLUDED_GIDS_BY_REGION

    assert set(EXPECTED_CELLS) <= set(KNOWN_REGIONS)
    assert set(EXCLUDED_GIDS_BY_REGION) <= set(KNOWN_REGIONS)


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


def test_an_unrecognised_region_is_refused_by_the_exclusion_side_too():
    # The same hole on the curation side: a misspelling returned frozenset(), so
    # nothing was curated and it read as the region that is MEANT to curate nothing.
    with pytest.raises(UnknownRegionError):
        excluded_for("lnd_gaul")


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


# --- the SHELLS' remaining obligation: call both gates, unconditionally, in order ---
#
# The skip-reporting rule lives in this module, not in the two managers (C-40(a)).
# That leaves each manager one obligation — call both gates and wrap neither in a
# condition — and nothing verified it: a guard audit restored `if excluded:` /
# `if expected is not None:` in BOTH managers and the whole suite stayed green
# (2026-11-18, ME2). That mutation reopens exactly the silence C-113 is about, on
# the historical leg. A manager cannot be imported without the full pipeline-core
# framework, so this reads the source — the repo's standing pattern for manager
# shape (see tests/test_launch_config.py, tests/test_doc_accuracy.py).


def _check_coverage_body(partner: str):
    import ast
    from pathlib import Path

    source = (
        Path(__file__).resolve().parent.parent
        / "views_postprocessing" / partner / "managers" / f"{partner}.py"
    ).read_text()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.FunctionDef) and node.name == "_check_coverage":
            return node
    raise AssertionError(f"{partner}: no _check_coverage to inspect")


def _gate_calls(node):
    """(attribute name, lineno) for each coverage gate call, and whether an `if`
    encloses it — walking down from the function body so enclosure is observed, not
    inferred from indentation."""
    import ast

    found = []

    def walk(n, under_if):
        for child in ast.iter_child_nodes(n):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                if child.func.attr in ("assert_no_excluded_cells", "assert_complete_coverage"):
                    found.append((child.func.attr, child.lineno, under_if))
            walk(child, under_if or isinstance(child, ast.If))

    walk(node, False)
    return found


@pytest.mark.parametrize("partner", ["unfao", "crafd"])
def test_the_manager_calls_both_gates_unconditionally(partner):
    calls = _gate_calls(_check_coverage_body(partner))
    names = [name for name, _, _ in calls]
    assert names.count("assert_no_excluded_cells") == 1, calls
    assert names.count("assert_complete_coverage") == 1, calls
    conditional = [(name, line) for name, line, under_if in calls if under_if]
    assert not conditional, (
        f"{partner}: {conditional} sits inside an `if`. Each gate owns its own skip "
        "report for an unpinned region; a caller-side condition skips the gate AND "
        "the report, which is the silent skip C-113 exists for."
    )


@pytest.mark.parametrize("partner", ["unfao", "crafd"])
def test_the_manager_runs_exclusion_before_count(partner):
    # So a leaked island names itself instead of arriving as "over-coverage by 1"
    # (S4/C-30). Stated in a comment in both managers and in nothing executable
    # until now; a guard audit swapped the pair with the suite green (MF3).
    lines = {name: line for name, line, _ in _gate_calls(_check_coverage_body(partner))}
    assert lines["assert_no_excluded_cells"] < lines["assert_complete_coverage"], lines


# --- the declaration itself: KNOWN_REGIONS must name regions that exist -------------
#
# `test_every_pinned_region_is_a_known_region` checks conformance to the declaration
# in one direction. A guard audit added "atlantis" to KNOWN_REGIONS and the whole
# suite stayed green (2026-11-18, MA6) — a region nobody curated would then launch,
# pin no count and no manifest, and skip both gates: C-113's shape re-entered through
# the declaration instead of through an omission. Which regions exist is a
# views-datafactory fact, so this is the direction only a cross-check can hold.


def _datafactory_declared_regions() -> set[str] | None:
    """The region names views-datafactory's `regions.py` says it serves.

    Read with `ast` rather than imported: `datafactory_query` is not a dependency of
    this package and is absent from the project venv, which is why the sibling
    cross-check above reads its JSON files directly instead.
    """
    import ast

    if _DATAFACTORY is None:
        return None
    path = _DATAFACTORY / "src" / "datafactory_query" / "regions.py"
    if not path.exists():
        return None
    tree = ast.parse(path.read_text())
    names: set[str] = set()
    for node in ast.walk(tree):
        # `list_regions()` returns the special values plus REGIONS' keys.
        if isinstance(node, ast.FunctionDef) and node.name == "list_regions":
            doc = ast.get_docstring(node, clean=False)
            names |= {
                n.value for n in ast.walk(node)
                if isinstance(n, ast.Constant)
                and isinstance(n.value, str)
                and n.value != doc
            }
        # `REGIONS: dict[str, list[str]] = {...}` is an AnnAssign, not an Assign.
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(x, ast.Name) and x.id == "REGIONS" for x in targets):
                names |= {
                    k.value for k in getattr(node.value, "keys", [])
                    if isinstance(k, ast.Constant) and isinstance(k.value, str)
                }
    return names or None


@pytest.mark.skipif(
    _datafactory_declared_regions() is None,
    reason=(
        "views-datafactory checkout not found, or its "
        "src/datafactory_query/regions.py declares no region names — set "
        "VIEWS_DATAFACTORY=/path/to/views-datafactory, or place it alongside this "
        "repo (this runs in CI)"
    ),
)
def test_every_known_region_is_one_views_datafactory_actually_serves():
    declared = _datafactory_declared_regions()
    assert declared is not None
    unknown_upstream = sorted(set(KNOWN_REGIONS) - declared)
    assert not unknown_upstream, (
        f"delivery.coverage.KNOWN_REGIONS names {unknown_upstream}, which "
        "views-datafactory's regions.py does not serve. A region declared here but "
        "absent upstream launches, pins nothing, and skips both coverage gates. "
        f"Upstream serves: {sorted(declared)}."
    )
    # The reverse must NOT hold: this delivery supports a subset deliberately
    # (it does not deliver "global" or bare "land"), so an upstream region missing
    # from KNOWN_REGIONS is a choice, not drift.
    assert set(KNOWN_REGIONS) <= declared
