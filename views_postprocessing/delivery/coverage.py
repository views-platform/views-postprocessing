"""Delivery coverage invariant: a delivery must cover exactly its region's cells.

Representation-free — primitives only (a set of cell ids + an int). No pandas, no
views_frames. The manager feeds it primitives via
``views_postprocessing/contract/frame_extraction.py``; the rule lives here
(S1 / register C-34). *(This pointed at ``unfao/extraction.py``, deleted in #151,
until 2026-11-12 — one of the two stale docstring pointers register C-107 names.)*

**A region must be DECLARED to reach either gate.** ``expected_for`` and
``excluded_for`` refuse ``None``, because the gates are chosen by region and an
absent one used to select "check nothing" while reading as a supported
configuration (register C-113). A region that is declared but not yet *pinned* is
supported and different: it returns ``None``/empty, and the caller reports a
skipped gate. The launcher-facing refusal is
``contract.launch_config.assert_region_declared``; these two are the same rule held
at the invariant, for every other caller.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class CoverageError(ValueError):
    """A delivery did not cover exactly the expected set of cells."""


class RegionNotDeclaredError(ValueError):
    """No region was declared, so neither coverage gate can be chosen.

    A sibling of ``CoverageError`` rather than a subclass, deliberately: nothing has
    been delivered wrongly here. The *question* could not be asked, which is a
    different fault with a different fix, and a caller catching ``CoverageError`` to
    report a coverage failure must not catch this and mislabel it as one.
    """


def _declared(region: str | None) -> str:
    """The region, or refuse. Chosen by region means absent-region checks nothing."""
    if not isinstance(region, str) or not region.strip():
        raise RegionNotDeclaredError(
            f"no region declared (got {region!r}): the completeness target and the "
            "cell-curation manifest are both selected BY the region, so there is "
            "nothing to check and nothing to curate. This is not the same as a "
            "region that is declared but unpinned — that is supported, returns no "
            "target, and is reported as a skipped gate by the caller. Pinned "
            f"regions: {sorted(EXPECTED_CELLS)}. Declared at launch; see "
            "contract.launch_config.assert_region_declared (register C-113)."
        )
    return region


def assert_complete_coverage(
    received_gids: set[int], expected_count: int | None, *, label: str = "delivery"
) -> None:
    """Raise unless exactly ``expected_count`` distinct cells were delivered.

    ``expected_count=None`` means the region is declared but **not pinned**, which is
    supported: the gate cannot run, so it says so and returns. Reporting that here
    rather than at the call site is what keeps the two managers from each carrying
    their own copy of the rule — and it is the half of C-113 that was **silently**
    skipped on the exclusion side while this side logged.

    An *undeclared* region never reaches this function: ``expected_for`` refuses it.

    Args:
        received_gids: the distinct PRIO-GRID cell ids actually delivered.
        expected_count: the number of cells the configured region must cover, or
            ``None`` for a declared-but-unpinned region.
        label: short tag for the message (e.g. ``"historical"`` / ``"forecast"``).

    Raises:
        CoverageError: on under- or over-coverage.
    """
    if expected_count is None:
        logger.warning(
            "%s: coverage count-gate SKIPPED — the declared region pins no cell count "
            "in delivery.coverage.EXPECTED_CELLS, so completeness was not enforced. "
            "Verify and pin the count before relying on this delivery being complete.",
            label,
        )
        return
    actual = len(received_gids)
    if actual != expected_count:
        kind = "under-coverage" if actual < expected_count else "over-coverage"
        raise CoverageError(
            f"{label}: {kind} — delivered {actual} cells, expected {expected_count} "
            f"(diff {actual - expected_count:+d}). A wrong/stale region or dropped "
            f"cells would ship partial coverage to the partner."
        )


# Region -> expected complete cell count.
#
# SSOT CAVEAT: these are *views-datafactory* facts (it defines the region cell-sets:
# regions.py / *_pgids.json). They are declared here as the delivery's statement of
# intent; source them from datafactory region metadata once it publishes a count
# (the same companion shape as S2's `last_valid_month_id`). Until then only a region
# whose count is *verified* is pinned — an unpinned region logs a skipped gate, never
# a guess.
#
#   land_gaul        : 64,742 = the cells in the datafactory `land_gaul` curated region
#                      (land 64,818 − 76 GAUL-uncovered, register C-30/D-10). The 76
#                      excluded gids are pinned below (S4 / #55). NB this was 64,736 / 82
#                      excluded until datafactory #163 (ADR-043) supplemented 6 Azorean
#                      cells into land_gaul — see EXCLUDED_GIDS_BY_REGION.
#   africa_me_legacy : intentionally NOT pinned — the register cites 13,110 region
#                      cells with 5 pure-ocean cells unassigned, so "complete" is
#                      ambiguous (13,110 vs 13,105). Verify against a real run first.
EXPECTED_CELLS: dict[str, int] = {
    "land_gaul": 64_742,
}


def expected_for(region: str | None) -> int | None:
    """The pinned expected cell count for ``region``.

    Returns:
        The pinned count, or ``None`` for a region that is declared but not pinned
        (``africa_me_legacy``) — a supported state the caller reports as a skipped
        count-gate.

    Raises:
        RegionNotDeclaredError: no region was declared at all. Until 2026-11-12 this
            returned ``None`` too, which made the two indistinguishable (C-113).
    """
    return EXPECTED_CELLS.get(_declared(region))


# Region -> the GAUL-uncovered cells the curated region deliberately drops.
#
# A *views-datafactory* fact: EXCLUDED = land − land_gaul (the producer's published
# region complement). Frozen here as an explicit manifest — a tripwire, per C-30/D-10:
# if the producer's coverage drifts, this frozen set diverges *loudly* rather than a
# generic `gaul0_code != -1` filter silently absorbing the change. Re-derive and re-pin
# when the land_gaul region version changes; tests/test_delivery_coverage.py cross-checks
# this against the datafactory sibling checkout when one is present.
#
#   land_gaul: 76 remote sub-Antarctic island cells (Macquarie, Auckland Islands, Prince
#   Edward, South Sandwich, ...) outside FAO GAUL 2024 coverage. Derived from datafactory
#   v1.4.0 (land 64,818 − land_gaul 64,742 = 76). The earlier "82" (register C-30,
#   pre-ADR-043) dropped to 76 when datafactory #163 supplemented 6 Azorean cells into
#   land_gaul. Disclosed to FAO in docs/fao_excluded_cells.md.
_LAND_GAUL_EXCLUDED: frozenset[int] = frozenset({
    51078, 51798, 53979, 54699, 56852, 56853, 58318, 62356,
    94776, 99027, 107733, 107742, 110367, 112944, 114769, 116931,
    118753, 121625, 123748, 124038, 124425, 124759, 126561, 126624,
    128012, 129079, 129387, 129574, 130919, 131639, 132525, 146125,
    153966, 157829, 159987, 160708, 173423, 179900, 190724, 201850,
    202249, 203404, 206592, 208007, 210596, 212353, 212774, 221061,
    223941, 225390, 227961, 229161, 229429, 229430, 229866, 233436,
    233743, 234640, 235586, 235942, 235943, 235951, 235954, 236054,
    237351, 238123, 238231, 238954, 239705, 240318, 240319, 240975,
    240977, 241153, 247862, 248595,
})

EXCLUDED_GIDS_BY_REGION: dict[str, frozenset[int]] = {
    "land_gaul": _LAND_GAUL_EXCLUDED,
}


def excluded_for(region: str | None) -> frozenset[int]:
    """The GAUL-uncovered gids the region must exclude.

    Returns:
        The frozen manifest, or an empty set for a region that is declared but not
        pinned (``africa_me_legacy`` keeps its ocean cells) — supported, and a no-op
        at the call site.

    Raises:
        RegionNotDeclaredError: no region was declared at all. Until 2026-11-12 this
            returned an empty set too, so an undeclared region curated nothing and
            looked exactly like the region that is meant to curate nothing (C-113).
    """
    return EXCLUDED_GIDS_BY_REGION.get(_declared(region), frozenset())


def assert_no_excluded_cells(
    received_gids: set[int], excluded_gids: frozenset[int], *, label: str = "delivery"
) -> None:
    """Raise if the delivery includes any GAUL-uncovered cell the region must drop.

    More specific than the count gate: it names *which* uncovered cells leaked, so a
    coverage regression is diagnosed rather than read as generic over-coverage.

    Args:
        received_gids: the distinct cell ids actually delivered.
        excluded_gids: the cells the configured region must exclude (see ``excluded_for``).
        label: short tag for the message (e.g. ``"historical"`` / ``"forecast"``).

    An empty ``excluded_gids`` means the declared region pins no curation manifest
    (``africa_me_legacy`` keeps its ocean cells) — supported, and the skip is
    **reported** rather than passed over in silence. That silence was half of C-113:
    the count gate logged its skip and this one did not, so a delivery could be
    uncurated with only half the evidence reaching the run log.

    An *undeclared* region never reaches this function: ``excluded_for`` refuses it.

    Raises:
        CoverageError: naming the leaked cells (these have no GAUL assignment, so
            shipping them would attribute partner rows to a non-country).
    """
    if not excluded_gids:
        logger.warning(
            "%s: coverage exclusion-gate SKIPPED — the declared region pins no "
            "excluded-cell manifest in delivery.coverage.EXCLUDED_GIDS_BY_REGION, so "
            "no cell curation was enforced.",
            label,
        )
        return
    leaked = sorted(received_gids & excluded_gids)
    if leaked:
        shown = leaked[:10]
        more = "" if len(leaked) <= 10 else f" (+{len(leaked) - 10} more)"
        raise CoverageError(
            f"{label}: {len(leaked)} GAUL-uncovered cell(s) the curated region must "
            f"exclude were delivered: {shown}{more}. These cells have no GAUL "
            f"assignment; shipping them attributes partner rows to a non-country."
        )
