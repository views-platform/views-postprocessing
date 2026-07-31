"""Lookup-based geographic enrichment (ADR-011).

Drop-in replacement for the runtime spatial mapper's
``enrich_dataframe_with_pg_info``. Instead of loading 774 MB of shapefiles and
computing spatial intersections at run time, it merges a precomputed lookup
table (built by ``scripts/build_gaul_lookup.py`` from the views-datafactory's
area-majority GAUL parquets) onto the input DataFrame by PRIO-GRID cell id.

No geopandas, no shapefiles, no spatial computation. The lookup contains only
fully-complete cells; an unknown or incomplete cell id left-merges to NaN, so
the manager's ``_validate()`` null gate still crashes the delivery (fail-loud)
rather than shipping a hole. This is intentional and matches the old mapper's
behaviour (it returned ``None`` for such cells).

Produces exactly the 9-column contract enforced at
the delivery's artifact builders and at
views-faoapi ``handlers.py`` (``FAO_PGMDataset._METADATA_COLS``).
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from views_postprocessing.contract import gaul_lookup
from views_postprocessing.contract.gaul_schema import METADATA_COLS

logger = logging.getLogger(__name__)

# The artifact's identity lives in `gaul_lookup` (#152, C-68) — this alias keeps the
# enricher's own default working without re-deriving the path.
_DEFAULT_LOOKUP = gaul_lookup.LOOKUP_PATH


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
        self._lookup = pd.read_parquet(self._lookup_path)
        # Index is priogrid_gid; columns are the 9 metadata columns.
        missing = [c for c in METADATA_COLS if c not in self._lookup.columns]
        if missing:
            err_msg = f"Lookup table is missing contract columns: {missing}"
            logger.error(err_msg)
            raise ValueError(err_msg)
        self.lookup_version = self._read_version(self._lookup_path)
        logger.info(
            "Loaded GAUL lookup: %d cells from %s (version=%s)",
            len(self._lookup), self._lookup_path, self.lookup_version,
        )

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

        merged = base.merge(
            self._lookup, left_on=pg_id_col, right_index=True, how="left",
        )

        n_total = len(merged)
        n_unmapped = int(merged["country_iso_a3"].isna().sum())
        if n_unmapped:
            logger.warning(
                "%d/%d rows have no lookup match (will fail validation): %s",
                n_unmapped, n_total,
                sorted(merged.loc[merged["country_iso_a3"].isna(), pg_id_col]
                       .unique().tolist())[:20],
            )
        return merged

    # Convenience alias for new call sites that don't need the legacy name.
    enrich = enrich_dataframe_with_pg_info
