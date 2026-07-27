"""Frame-native representation seam: extract primitives from a views-frames frame.

The **frame counterpart** to ``extraction.py`` (the pandas seam). It returns the *same*
primitives — sets of ints, numpy month arrays — so the representation-free
``views_postprocessing.delivery`` invariants consume them unchanged.

Per the migration design (epic #85): pandas and views-frames do **not** coexist at runtime,
so these are deliberately **siblings** of the pandas readers in ``extraction.py``, not a
replacement, and there is **no shared ``Extractor`` Protocol** (a polymorphic interface
nobody dispatches on would be speculative — YAGNI/ISP). When the forecast interior moves to a
frame (S3 / #88), the manager calls *these*; the pandas readers stay for the still-pandas
historical path (gated on C-40 / S7).

Scope: the readers the forecast interior needs — distinct cells and months from the frame's
index. Deliberately **not** here yet (no speculative code):
- the pandas→``(N, S)`` sample-array unpacker — added when rusty_bucket (#143) declares the
  layout (the seam will be *told* the layout, never sniff it);
- a frame-native ``unmapped_cell_count`` — geographic metadata lives on the pandas enriched
  frame, not the value frame, until the enrichment moves off pandas (S4 / #89);
- a frame-native ``drop_months_above`` — the observed-range clip is on the *historical*
  frame, which is gated on the inbound retirement (S7 / #92).
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from views_frames import PredictionFrame


def cells_of(frame: PredictionFrame) -> set[int]:
    """The set of PRIO-GRID cell ids present in the frame (its index ``unit`` axis)."""
    return {int(x) for x in np.unique(frame.index.unit)}


def months_of(frame: PredictionFrame) -> NDArray[np.int64]:
    """The distinct month ids present in the frame, ascending (its index ``time`` axis)."""
    return np.unique(np.asarray(frame.index.time, dtype=np.int64))


def drop_months_above(frame, last_valid_month_id: int):
    """The frame clipped to observed months (``time <= last_valid_month_id``).

    Frame-native sibling of ``extraction.drop_months_above`` (S7/#92): works on
    any frame sharing the ``SpatioTemporalIndex`` surface (PredictionFrame,
    FeatureFrame) via ``.select`` on a boolean row mask. The boundary value is
    declared by the caller (producer-sourced, C-26) — never inferred here.
    """
    time = np.asarray(frame.index.time, dtype=np.int64)
    mask = time <= int(last_valid_month_id)
    if mask.all():
        return frame
    return frame.select(mask)


def drop_units(frame: PredictionFrame, excluded: frozenset) -> PredictionFrame:
    """The frame without the DECLARED excluded cells (row filter on ``unit``).

    Product curation as a seam concern (ADR-013 anti-corruption role): the producer
    publishes its full model grid; the delivery restricts it to the declared
    partner region using an explicit exclusion set (e.g.
    ``delivery.coverage.excluded_for(region)``) — never inferred. Empty exclusion
    returns the frame unchanged.
    """
    if not excluded:
        return frame
    unit = np.asarray(frame.index.unit, dtype=np.int64)
    keep = ~np.isin(unit, np.fromiter(excluded, dtype=np.int64))
    if keep.all():
        return frame
    time = np.asarray(frame.index.time, dtype=np.int64)
    from views_postprocessing.unfao.frames import build_prediction_frame

    return build_prediction_frame(frame.values[keep], time[keep], unit[keep])


def month_slice(
    frame: PredictionFrame, month_id: int
) -> tuple[NDArray[np.float32], NDArray[np.int64], NDArray[np.int64]]:
    """One month's ``(values, time, unit)`` primitives, row order preserved.

    The per-(target, month) sharding cut (ADR-013 §4.1) as a seam concern: the
    shard writer stays frame-API-free by receiving primitives. A month absent
    from the frame fails loud — the caller declared it, the frame must carry it.
    """
    time = np.asarray(frame.index.time, dtype=np.int64)
    mask = time == month_id
    if not mask.any():
        raise ValueError(f"month {month_id} not present in frame (months: {months_of(frame)}).")
    unit = np.asarray(frame.index.unit, dtype=np.int64)
    return frame.values[mask], time[mask], unit[mask]
