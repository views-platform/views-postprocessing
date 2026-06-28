"""FAO-local representation seam: extract primitives from the delivery's external
representations for the ``views_postprocessing.delivery`` invariants.

This is the **only** pandas-aware module the delivery invariants are fed from: it turns
the pandas ``DataFrame`` representation into plain primitives (sets of ints, numpy
arrays). It also normalizes the prediction-store **metadata record** into a plain dict
for the forecast-identity invariant (``file_metadata`` below) — keeping all knowledge of
external representations here, so the invariants stay representation-free.

When the delivery representation migrates from pandas to views-frames (gated on
pipeline-core's DataFrame retirement, register C-40), **only this module changes** —
a sibling ``extraction`` for the new representation is added and the manager calls it;
the invariants in ``views_postprocessing/delivery/`` are untouched (OCP).

Per the epic design contract (views-postprocessing#51) there is deliberately **no
``Extractor`` Protocol** — pandas and views-frames do not coexist at runtime (it is a
migration), so a polymorphic interface would be speculative (YAGNI/ISP).
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

import numpy as np
import pandas as pd
from numpy.typing import NDArray

logger = logging.getLogger(__name__)

# VIEWS PRIO-GRID-month identifier conventions (index levels or flat columns).
_PG_ID = "priogrid_gid"
_TIME_ID = "month_id"


def _level_or_column(df: pd.DataFrame, name: str) -> NDArray:
    """Return ``name`` as a flat array whether it is an index level or a column."""
    if name in (df.index.names or []):
        return np.asarray(df.index.get_level_values(name))
    if name in df.columns:
        return np.asarray(df[name])
    err_msg = (
        f"'{name}' is neither an index level nor a column "
        f"(have index={list(df.index.names or [])}, columns={list(df.columns)[:8]}...)"
    )
    logger.error(err_msg)
    raise KeyError(err_msg)


def cells_of(df: pd.DataFrame, pg_id: str = _PG_ID) -> set[int]:
    """The set of PRIO-GRID cell ids present in the delivery frame."""
    return {int(x) for x in np.unique(_level_or_column(df, pg_id))}


def months_of(df: pd.DataFrame, time_id: str = _TIME_ID) -> NDArray[np.int64]:
    """The distinct month ids present in the delivery frame, ascending."""
    return np.unique(_level_or_column(df, time_id).astype(np.int64))


def unmapped_cell_count(
    df: pd.DataFrame, metadata_cols: Sequence[str], pg_id: str = _PG_ID
) -> int:
    """Distinct cells with a null in any metadata column (the post-enrich unmapped count).

    Feeds the provenance invariant (``delivery.provenance``). 0 once ``_validate`` passes,
    but recorded as an explicit audit value rather than assumed.
    """
    cols = [c for c in metadata_cols if c in df.columns]
    if not cols:
        return 0
    mask = df[cols].isnull().any(axis=1)
    if not bool(mask.any()):
        return 0
    return len(cells_of(df[mask], pg_id))


def drop_months_above(
    df: pd.DataFrame, last_valid_month_id: int, time_id: str = _TIME_ID
) -> pd.DataFrame:
    """Return ``df`` with rows whose month exceeds ``last_valid_month_id`` removed.

    The representation-specific half of the S2 observed-range clip: the *decision*
    (which months are fabricated) is made by ``delivery.observed_range``; this applies
    it to the pandas frame.
    """
    months = _level_or_column(df, time_id).astype(np.int64)
    return df[months <= int(last_valid_month_id)]


# Prediction-store identity fields (written by pipeline-core's FileMetadata on upload).
_FILE_META_KEYS = ("name", "loa", "category", "targets")


def file_metadata(record) -> dict:
    """The identity metadata of a selected prediction-store file, as a plain dict.

    ``record`` is the ``get_file_metadata`` result from pipeline-core's ``DatastoreModule``;
    its ``.to_dict()["data"]`` is the Appwrite metadata document. This is the only place
    that knows that shape — the forecast-identity invariant
    (``views_postprocessing.delivery.identity``) consumes the returned primitives.
    """
    doc = record.to_dict().get("data", {}) or {}
    return {key: doc.get(key) for key in _FILE_META_KEYS}
