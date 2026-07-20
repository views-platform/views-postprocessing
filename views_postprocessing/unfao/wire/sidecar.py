"""The §5 GAUL geography sidecar builder (ADR-013).

One sidecar per run: a 10-column parquet — ``priogrid_id`` (int64) as the FIRST
COLUMN, then the 9 contract columns in ``gaul_schema.METADATA_COLS`` order (the
SSOT; never restated here). Pinned by §5.1: ``*_code`` columns **always float64**
(missing codes become NaN values, matching the canonical fixture bytes), string
columns plain (dictionary encodings are flattened; missing stays null), rows
ascending by ``priogrid_id``.

The lookup is a **parameter** (DIP): production passes the ADR-011
``data/gaul_lookup.parquet`` table; tests inject a synthetic one. The builder is
restricted to the declared forecast gid set, and a declared gid absent from the
lookup FAILS LOUD — geography for a forecast cell must never silently vanish
(§5.2 parity direction).

pyarrow-only — the delivery's pandas-free path stays pandas-free.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from views_postprocessing.unfao.gaul_schema import CODE_COLS, COORD_COLS, METADATA_COLS
from views_postprocessing.unfao.wire.naming import sidecar_name


class SidecarError(ValueError):
    """The sidecar cannot be built as declared."""


def build_sidecar(lookup: pa.Table, gids) -> pa.Table:
    """The §5.1 table for exactly the declared ``gids``, schema pinned.

    ``lookup`` carries ``priogrid_gid`` plus the 9 contract columns (the ADR-011
    lookup's shape). Output renames the key to the wire's ``priogrid_id``.
    """
    missing = [c for c in ("priogrid_gid", *METADATA_COLS) if c not in lookup.column_names]
    if missing:
        raise SidecarError(f"lookup lacks required columns: {missing}.")

    wanted = np.asarray(sorted(int(g) for g in set(gids)), dtype=np.int64)
    lookup_gids = lookup.column("priogrid_gid").to_numpy(zero_copy_only=False)
    absent = np.setdiff1d(wanted, lookup_gids)
    if absent.size:
        raise SidecarError(
            f"{absent.size} forecast cell(s) absent from the GAUL lookup — geography "
            f"must never silently vanish (§5.2). First missing gids: {absent[:5].tolist()}."
        )

    mask = pa.array(np.isin(lookup_gids, wanted))
    selected = lookup.filter(mask).sort_by("priogrid_gid")  # ascending rows (§5.1)

    columns: dict[str, pa.Array] = {
        "priogrid_id": selected.column("priogrid_gid").cast(pa.int64()).combine_chunks()
    }
    for col in METADATA_COLS:
        array = selected.column(col)
        if col in CODE_COLS:
            # Always float64 (§5.1 dtype ruling); missing codes are NaN VALUES,
            # matching the canonical fixture bytes (not arrow nulls).
            array = pc.fill_null(array.cast(pa.float64()), float("nan"))
        elif col in COORD_COLS:
            array = array.cast(pa.float64())
        else:
            array = array.cast(pa.string())  # flatten dictionary encodings; nulls stay
        columns[col] = array.combine_chunks()
    return pa.table(columns)


def write_sidecar(lookup: pa.Table, gids, *, run_id: str, directory: Path) -> tuple[str, str]:
    """Write the run's sidecar; return ``(file_name, sha256_of_bytes)`` for §4.2."""
    name = sidecar_name(run_id)
    path = Path(directory) / name
    pq.write_table(build_sidecar(lookup, gids), path)
    return name, hashlib.sha256(path.read_bytes()).hexdigest()
