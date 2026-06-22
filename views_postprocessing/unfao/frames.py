"""views-frames adapters — phase 1 of the numpy/views-frames migration.

Turn this repo's pandas prediction/target tables into ``views-frames`` value
objects so they can be checked against the published views-frames data contract
(``assert_frame_contract``). This is the **seam** through which frames enter
views-postprocessing; nothing in the live delivery path calls it yet (the
manager still moves pandas DataFrames — that is wired in a later phase).

The repo carries two kinds of data, which map to two frame types:

    forecasts        (``pred_ln_*``)  -> PredictionFrame  (N, 1)   point preds
    observed actuals (``ged_*``)      -> TargetFrame      (N, 1)   ground truth

Both sit at PGM level: ``time = month_id``, ``unit = priogrid_gid``. Our
forecasts are scalar point values, so the explicit trailing sample axis is
``S = 1`` (ADR-012); a ``TargetFrame`` is ``(N, 1)`` by definition.

numpy-at-the-boundary: this module reads a few columns out of a pandas frame
and hands numpy arrays to views-frames. It performs no merges and adds no
geography — that stays in :mod:`enrichment` until a later migration phase.

These adapters **convert**, they do not **validate**: a NaN value flows through
into the frame (the views-frames contract permits NaN — only object dtype is
banned). Null-guarding remains the manager's ``_validate`` gate, the single
fail-loud place a delivery is refused; an adapter is not that gate.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from views_frames import (
    FrameMetadata,
    PredictionFrame,
    SpatialLevel,
    SpatioTemporalIndex,
    TargetFrame,
)

_TIME_ID = "month_id"
_PG_ID = "priogrid_gid"


def _extract_ids(
    df: pd.DataFrame, time_id_col: str, pg_id_col: str
) -> tuple[np.ndarray, np.ndarray]:
    """Pull ``(time, unit)`` arrays from columns *or* a MultiIndex.

    Accepts both shapes the repo produces: the manager's index-keyed frame
    (``MultiIndex[(month_id, priogrid_gid)]``) and a ``reset_index()`` flat frame.
    """
    if time_id_col in df.columns and pg_id_col in df.columns:
        return df[time_id_col].to_numpy(), df[pg_id_col].to_numpy()
    names = list(df.index.names)
    if time_id_col in names and pg_id_col in names:
        return (
            df.index.get_level_values(time_id_col).to_numpy(),
            df.index.get_level_values(pg_id_col).to_numpy(),
        )
    raise ValueError(
        f"DataFrame must carry '{time_id_col}' and '{pg_id_col}' as columns or "
        f"index levels; got columns={list(df.columns)}, index names={names}"
    )


def _pgm_index(
    df: pd.DataFrame, time_id_col: str, pg_id_col: str
) -> SpatioTemporalIndex:
    """A PGM ``SpatioTemporalIndex`` from this frame's ``(month_id, priogrid_gid)``."""
    time, unit = _extract_ids(df, time_id_col, pg_id_col)
    return SpatioTemporalIndex(
        time=np.asarray(time, dtype=np.int64),
        unit=np.asarray(unit, dtype=np.int64),
        level=SpatialLevel.PGM,
    )


def _column_2d(df: pd.DataFrame, value_col: str) -> np.ndarray:
    """One value column as an ``(N, 1)`` array (the explicit trailing axis)."""
    if value_col not in df.columns:
        raise ValueError(
            f"value column '{value_col}' not found; columns={list(df.columns)}"
        )
    return df[value_col].to_numpy().reshape(-1, 1)


def to_prediction_frame(
    df: pd.DataFrame,
    value_col: str,
    *,
    time_id_col: str = _TIME_ID,
    pg_id_col: str = _PG_ID,
    metadata: FrameMetadata | None = None,
) -> PredictionFrame:
    """Wrap one forecast column as a ``PredictionFrame`` ``(N, 1)`` at PGM level.

    The values coerce to float32 inside views-frames; scalar point predictions
    become a single-sample axis (``sample_count == 1``).
    """
    index = _pgm_index(df, time_id_col, pg_id_col)
    return PredictionFrame(_column_2d(df, value_col), index, metadata)


def to_target_frame(
    df: pd.DataFrame,
    value_col: str,
    *,
    time_id_col: str = _TIME_ID,
    pg_id_col: str = _PG_ID,
    metadata: FrameMetadata | None = None,
) -> TargetFrame:
    """Wrap one observed-actuals column (e.g. ``ged_sb_best``) as a ``TargetFrame``."""
    index = _pgm_index(df, time_id_col, pg_id_col)
    return TargetFrame(_column_2d(df, value_col), index, metadata)
