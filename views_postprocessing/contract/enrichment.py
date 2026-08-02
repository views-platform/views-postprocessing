"""Lookup-based geographic enrichment (ADR-011).

Drop-in replacement for the runtime spatial mapper's
``enrich_dataframe_with_pg_info``. Instead of loading 774 MB of shapefiles and
computing spatial intersections at run time, it merges a precomputed lookup
table (built by ``scripts/build_gaul_lookup.py`` from the views-datafactory's
area-majority GAUL parquets) onto the input DataFrame by PRIO-GRID cell id.

No geopandas, no shapefiles, no spatial computation. The lookup contains only
fully-complete cells; an unknown or incomplete cell id gathers to null, so the
delivery's null gate still crashes (fail-loud) rather than shipping a hole. This
is intentional and matches the old mapper's behaviour (it returned ``None`` for
such cells).

**The lookup side is pandas-free (S4 / #89, epic #85).** It is read with pyarrow
and held as numpy arrays plus a sorted key index; attaching metadata to a frame is
a **keyed gather**, not frame algebra, and it never needed a pandas merge. The
input frame is still whatever the caller passes — this class is the *build and
verification* path's object, and its callers hand it DataFrames. What changed is
that the 888 KB artifact is no longer materialised as a pandas frame, and the
join no longer depends on the artifact carrying pandas index metadata — which is
what unblocks S5 (#90) making the builder pyarrow-native.

Produces exactly the 9-column contract enforced at
the delivery's artifact builders and at
views-faoapi ``handlers.py`` (``FAO_PGMDataset._METADATA_COLS``).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pyarrow as pa

from views_postprocessing.contract import gaul_lookup

if TYPE_CHECKING:  # pragma: no cover — pandas is in this module's INTERFACE, not its
    import pandas as pd  # implementation. Callers hand it DataFrames; nothing here
    # constructs, reads or joins one. Removing the runtime import is the point of
    # S4 (#89): the 888 KB lookup is no longer materialised as a pandas frame, and the
    # join no longer needs the artifact to carry pandas index metadata.
from views_postprocessing.contract.gaul_schema import METADATA_COLS

logger = logging.getLogger(__name__)

# The artifact's identity lives in `gaul_lookup` (#152, C-68) — this alias keeps the
# enricher's own default working without re-deriving the path.
_DEFAULT_LOOKUP = gaul_lookup.LOOKUP_PATH

#: The lookup's key column. Named once — the artifact calls it `priogrid_gid`, the
#: wire calls it `priogrid_id` (§5.1), and confusing the two is a silent join failure.
_KEY = "priogrid_gid"


class GaulLookupEnricher:
    """Merge precomputed GAUL metadata onto an input DataFrame by cell id."""

    def __init__(self, lookup_path: str | Path | None = None) -> None:
        self._lookup_path = Path(lookup_path) if lookup_path else _DEFAULT_LOOKUP
        if not self._lookup_path.exists():
            err_msg = (
                f"GAUL lookup table not found at {self._lookup_path}. "
                f"Build it with scripts/build_gaul_lookup.py."
            )
            logger.error(err_msg)
            raise FileNotFoundError(err_msg)
        table = gaul_lookup.load(self._lookup_path)
        missing = [c for c in (_KEY, *METADATA_COLS) if c not in table.column_names]
        if missing:
            err_msg = f"Lookup table is missing contract columns: {missing}"
            logger.error(err_msg)
            raise ValueError(err_msg)

        # Sort the whole table once by key, in arrow, so the gather below is a binary
        # search per row rather than a scan. `take` reorders every column together —
        # doing it column-by-column in python was measurably quadratic and is exactly
        # the mistake this comment exists to stop the next person repeating.
        keys = table.column(_KEY).to_numpy(zero_copy_only=False).astype(np.int64)
        order = np.argsort(keys, kind="stable")
        table = table.take(pa.array(order))
        self._keys = keys[order]
        # One `to_pylist` per column, not per row. Lists rather than numpy arrays
        # because the columns are of mixed kind (float codes, string names) and the
        # output is assembled per column anyway.
        self._values = {col: table.column(col).to_pylist() for col in METADATA_COLS}
        self._n_cells = table.num_rows
        self.lookup_version = self._read_version(self._lookup_path)
        logger.info(
            "Loaded GAUL lookup: %d cells from %s (version=%s)",
            self._n_cells, self._lookup_path, self.lookup_version,
        )

    def _gather(self, gids) -> tuple[dict, np.ndarray]:
        """Metadata for each gid, plus a mask of the ones absent from the lookup.

        A sorted-key ``searchsorted`` rather than a hash map: the lookup is 64,742
        rows read once per process, and the gather is over the delivery's row count.
        Absent gids yield ``None`` in every column — the null the downstream gate
        exists to catch, not a sentinel it would pass.
        """
        wanted = np.asarray(gids, dtype=np.int64)
        pos = np.searchsorted(self._keys, wanted)
        clipped = np.clip(pos, 0, max(len(self._keys) - 1, 0))
        found = (len(self._keys) > 0) & (self._keys[clipped] == wanted)
        idx = clipped
        out = {
            col: [vals[i] if hit else None for i, hit in zip(idx, found)]
            for col, vals in self._values.items()
        }
        return out, ~found

    @staticmethod
    def _read_version(path: Path) -> str:
        """The lookup's build stamp. Delegates to ``gaul_lookup.version`` (#152) —
        this was a ``@staticmethod`` that never touched the instance, i.e. a fact
        about the artifact, not about the enricher."""
        return gaul_lookup.version(path)

    def enrich_dataframe_with_pg_info(
        self,
        df: pd.DataFrame,
        pg_id_col: str = "priogrid_gid",
        time_id_col: str = "month_id",
        only_metadata: bool = True,
        **ignored_mapper_kwargs,
    ) -> pd.DataFrame:
        """Return ``df`` with the 9 metadata columns merged in by cell id.

        Signature mirrors the mapper's method so the manager call site changes
        minimally. Mapper-only kwargs (``batch_size``, ``use_multiprocessing``,
        ``show_progress`` …) are accepted and ignored — a table join needs none
        of them — but any unrecognised kwarg is logged at debug so a genuine
        caller mistake is not wholly silent.

        Cells absent from the lookup get NaN metadata (fail-loud downstream).
        """
        if ignored_mapper_kwargs:
            logger.debug(
                "GaulLookupEnricher ignoring mapper-only kwargs: %s",
                sorted(ignored_mapper_kwargs),
            )
        if pg_id_col not in df.columns:
            err_msg = f"Column '{pg_id_col}' not found in DataFrame"
            logger.error(err_msg)
            raise ValueError(err_msg)

        if only_metadata:
            keep = [pg_id_col]
            if time_id_col in df.columns:
                keep.append(time_id_col)
            base = df[keep].copy()
        else:
            base = df.copy()

        gids = base[pg_id_col].to_numpy()
        gathered, absent = self._gather(gids)

        merged = base.copy()
        for col in METADATA_COLS:
            merged[col] = gathered[col]

        n_unmapped = int(absent.sum())
        if n_unmapped:
            unmatched = sorted({int(g) for g, miss in zip(gids, absent) if miss})
            logger.warning(
                "%d/%d rows have no lookup match (will fail validation): %s",
                n_unmapped, len(merged), unmatched[:20],
            )
        return merged

    # Convenience alias for new call sites that don't need the legacy name.
    enrich = enrich_dataframe_with_pg_info
