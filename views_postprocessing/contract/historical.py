"""The FAO historical (actuals) artifact, built pandas-free (#126).

One concept: turn the historical ``views_frames.FeatureFrame`` plus the injected
ADR-011 GAUL lookup into the SAME artifact faoapi's deployed reader already
ingests — plain-column parquet with ``month_id, priogrid_id, <targets...>,
<the 9 gaul_schema.METADATA_COLS>``. The wire artifact does not change shape
(ADR-013 §4.1/§8); only its construction leaves pandas. Reader-level parity with
the legacy chain is pinned by ``tests/test_historical_parity.py``'s golden.

Rules carried over from the sidecar builder (§5.1 discipline):
- lookup injected (DIP) — production passes ``data/gaul_lookup.parquet``;
- a cell absent from the lookup FAILS LOUD (geography never silently vanishes);
- string columns plain (never dictionary/categorical), code columns float64;
- deliberately DROPPED: any non-feature payload columns (the legacy chain would
  have shipped datafactory's ``row``/``col`` grid coordinates as bogus
  auto-detected "targets" — pinned in the characterization golden).

The null-gate (every metadata value present) is this module's fail-loud
equivalent of the legacy ``_validate`` historical leg; ``unmapped_cell_count``
feeds the same provenance field it always did (C-15).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from views_postprocessing.contract.gaul_schema import CODE_COLS, COORD_COLS, METADATA_COLS


class HistoricalArtifactError(ValueError):
    """The historical artifact cannot be built as declared."""


def build_historical_table(frame, lookup: pa.Table) -> pa.Table:
    """FeatureFrame + GAUL lookup → the reader-compatible historical table.

    ``frame.values`` is ``(N, F, S)``; actuals are single-valued (S=1) — a
    multi-sample historical is a declaration error, refused loud.
    """
    if frame.sample_count != 1:
        raise HistoricalArtifactError(
            f"historical actuals must be single-valued; got sample_count={frame.sample_count}."
        )
    missing_cols = [c for c in ("priogrid_gid", *METADATA_COLS) if c not in lookup.column_names]
    if missing_cols:
        raise HistoricalArtifactError(f"lookup lacks required columns: {missing_cols}.")

    unit = np.asarray(frame.index.unit, dtype=np.int64)
    time = np.asarray(frame.index.time, dtype=np.int64)

    lookup_gids = lookup.column("priogrid_gid").to_numpy(zero_copy_only=False)
    order = np.argsort(lookup_gids)
    sorted_gids = lookup_gids[order]
    pos = np.searchsorted(sorted_gids, unit)
    pos_valid = (pos < len(sorted_gids))
    if not pos_valid.all() or not (sorted_gids[np.clip(pos, 0, len(sorted_gids) - 1)] == unit).all():
        absent = np.unique(unit[~pos_valid | (sorted_gids[np.clip(pos, 0, len(sorted_gids) - 1)] != unit)])
        raise HistoricalArtifactError(
            f"{absent.size} historical cell(s) absent from the GAUL lookup — geography "
            f"must never silently vanish. First missing gids: {absent[:5].tolist()}."
        )
    row_indices = pa.array(order[pos])

    columns: dict = {
        "month_id": pa.array(time, pa.int64()),
        "priogrid_id": pa.array(unit, pa.int64()),
    }
    for i, name in enumerate(frame.feature_names):
        columns[name] = pa.array(frame.values[:, i, 0])
    for col in METADATA_COLS:
        array = lookup.column(col).combine_chunks().take(row_indices)
        if col in CODE_COLS:
            array = pc.fill_null(array.cast(pa.float64()), float("nan"))
        elif col in COORD_COLS:
            array = array.cast(pa.float64())
        else:
            array = array.cast(pa.string())  # plain, never dictionary (§5.1 discipline)
        columns[col] = array
    return pa.table(columns)


def assert_metadata_complete(table: pa.Table) -> None:
    """Fail loud on any missing metadata value (the legacy null-gate, kept)."""
    for col in METADATA_COLS:
        nulls = table.column(col).null_count
        if nulls:
            raise HistoricalArtifactError(
                f"historical artifact has {nulls} null value(s) in required metadata "
                f"column {col!r} ({nulls}/{table.num_rows} rows)."
            )


def unmapped_cell_count(table: pa.Table) -> int:
    """Distinct cells with a null in ANY metadata column (the C-15 provenance count)."""
    mask = None
    for col in METADATA_COLS:
        col_null = pc.is_null(table.column(col))
        mask = col_null if mask is None else pc.or_(mask, col_null)
    if not pc.any(mask).as_py():
        return 0
    gids = pc.filter(table.column("priogrid_id"), mask)
    return len(pc.unique(gids))


def write_historical_artifact(table: pa.Table, path: Path) -> tuple[str, str]:
    """Serialize; return ``(file_name, sha256_of_bytes)``."""
    path = Path(path)
    pq.write_table(table, path)
    return path.name, hashlib.sha256(path.read_bytes()).hexdigest()
