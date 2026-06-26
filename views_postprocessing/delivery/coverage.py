"""Delivery coverage invariant: a delivery must cover exactly its region's cells.

Representation-free — primitives only (a set of cell ids + an int). No pandas, no
views_frames. The manager feeds it primitives via
``views_postprocessing/unfao/extraction.py``; the rule lives here (S1 / register C-34).
"""

from __future__ import annotations


class CoverageError(ValueError):
    """A delivery did not cover exactly the expected set of cells."""


def assert_complete_coverage(
    received_gids: set[int], expected_count: int, *, label: str = "delivery"
) -> None:
    """Raise unless exactly ``expected_count`` distinct cells were delivered.

    Args:
        received_gids: the distinct PRIO-GRID cell ids actually delivered.
        expected_count: the number of cells the configured region must cover.
        label: short tag for the message (e.g. ``"historical"`` / ``"forecast"``).

    Raises:
        CoverageError: on under- or over-coverage.
    """
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
#   land_gaul        : 64,736 = land ∩ gaul0_code != -1 (register C-30/D-10).
#                      The 82 excluded sub-Antarctic gids are pinned in S4 (#55).
#   africa_me_legacy : intentionally NOT pinned — the register cites 13,110 region
#                      cells with 5 pure-ocean cells unassigned, so "complete" is
#                      ambiguous (13,110 vs 13,105). Verify against a real run first.
EXPECTED_CELLS: dict[str, int] = {
    "land_gaul": 64_736,
}


def expected_for(region: str | None) -> int | None:
    """The pinned expected cell count for ``region``, or None if unpinned/unknown."""
    return EXPECTED_CELLS.get(region) if region else None
