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
``unfao.py`` (``_append_metadata`` filter_cols / ``_validate``) and at
views-faoapi ``handlers.py`` (``FAO_PGMDataset._METADATA_COLS``).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from views_postprocessing.unfao.gaul_schema import METADATA_COLS

logger = logging.getLogger(__name__)

_DEFAULT_LOOKUP = Path(__file__).resolve().parent.parent / "data" / "gaul_lookup.parquet"


class GaulLookupEnricher:
    """Merge precomputed GAUL metadata onto an input DataFrame by cell id."""

    def __init__(self, lookup_path: str | Path | None = None) -> None:
        self._lookup_path = Path(lookup_path) if lookup_path else _DEFAULT_LOOKUP
        if not self._lookup_path.exists():
            raise FileNotFoundError(
                f"GAUL lookup table not found at {self._lookup_path}. "
                f"Build it with scripts/build_gaul_lookup.py."
            )
        self._lookup = pd.read_parquet(self._lookup_path)
        # Index is priogrid_gid; columns are the 9 metadata columns.
        missing = [c for c in METADATA_COLS if c not in self._lookup.columns]
        if missing:
            raise ValueError(
                f"Lookup table is missing contract columns: {missing}"
            )
        self.lookup_version = self._read_version(self._lookup_path)
        logger.info(
            "Loaded GAUL lookup: %d cells from %s (version=%s)",
            len(self._lookup), self._lookup_path, self.lookup_version,
        )

    @staticmethod
    def _read_version(path: Path) -> str:
        """A short, stampable version id from the lookup's embedded provenance.

        Format: ``<region>@<short source digest>`` (e.g. ``land_gaul@f74d3b2b``)
        so a delivery can be traced to the exact lookup build. Falls back to
        ``"unknown"`` if the parquet carries no provenance metadata.
        """
        meta = pq.read_metadata(path).metadata or {}
        meta = {k.decode(): v.decode() for k, v in meta.items()}
        region = meta.get("region", "?")
        digest = "?"
        try:
            prov = json.loads(meta.get("source_provenance", "{}"))
            digest = (prov.get("land_gaul_region", {})
                      .get("content_digest", "?"))[:8]
        except (ValueError, AttributeError):
            pass
        return "unknown" if region == "?" and digest == "?" else f"{region}@{digest}"

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
            raise ValueError(f"Column '{pg_id_col}' not found in DataFrame")

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
