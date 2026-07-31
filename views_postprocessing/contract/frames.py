"""views-frames constructors — build views-frames value objects from **declared primitives**.

This module is the boundary where this repo hands data to the views-frames foundation. It
takes explicit, declared primitives — a 2D ``(N, S)`` value array plus the ``(time, unit)``
identifier arrays — and constructs the corresponding views-frames value object.

**Declare, don't guess.** The caller states the shape: a point prediction is simply
``S = 1`` (an ``(N, 1)`` array); a sampled prediction is ``(N, S)``. This module does **not**
inspect dtypes to infer the sample axis and does **not** reshape a 1-D column or stack
object-dtype cells — a mismatched input fails loud (views-frames rejects anything that is
not an explicit 2-D ``(N, S)`` array). Producing these primitives *from* this repo's pandas
tables is the job of the extraction seam (the one pandas-aware place); keeping that knowledge
out of here leaves this module **representation-free**, like ``views_postprocessing/delivery/``.

    forecasts        -> build_prediction_frame(values (N, S), time, unit)   # S >= 1
    observed actuals -> build_target_frame(values (N, 1), time, unit)       # S == 1

Both sit at PGM level (``time = month_id``, ``unit = priogrid_gid``). These constructors
convert + validate the *shape* (via views-frames' contract); they do not null-guard —
that remains the manager's ``_validate`` gate.
"""

from __future__ import annotations

import numpy as np

from views_frames import (
    FrameMetadata,
    PredictionFrame,
    SpatialLevel,
    SpatioTemporalIndex,
    TargetFrame,
)


def _pgm_index(time, unit) -> SpatioTemporalIndex:
    """A PGM ``SpatioTemporalIndex`` from declared ``(time, unit)`` arrays (int64)."""
    return SpatioTemporalIndex(
        time=np.asarray(time, dtype=np.int64),
        unit=np.asarray(unit, dtype=np.int64),
        level=SpatialLevel.PGM,
    )


def build_prediction_frame(
    values, time, unit, *, metadata: FrameMetadata | None = None
) -> PredictionFrame:
    """Build a PGM ``PredictionFrame`` from a declared ``(N, S)`` array + ``(time, unit)``.

    ``values`` must be a 2-D array with one row per ``(time, unit)`` and an explicit trailing
    sample axis ``S`` (a point prediction declares ``S = 1``). A 1-D array, an object-dtype
    array of per-cell sample arrays, or a row-count that disagrees with the index all **raise**
    — the caller must declare the ``(N, S)`` shape, this constructor will not infer it.
    """
    return PredictionFrame(np.asarray(values, dtype=np.float32), _pgm_index(time, unit), metadata)


def build_target_frame(
    values, time, unit, *, metadata: FrameMetadata | None = None
) -> TargetFrame:
    """Build a PGM ``TargetFrame`` from a declared ``(N, 1)`` array + ``(time, unit)``.

    Ground truth is single-valued: ``values`` must be ``(N, 1)`` (``S == 1``); any other shape
    raises (views-frames' ``TargetFrame`` contract).
    """
    return TargetFrame(np.asarray(values, dtype=np.float32), _pgm_index(time, unit), metadata)
