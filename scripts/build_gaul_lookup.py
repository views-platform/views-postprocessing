"""Build the precomputed GAUL lookup table (ADR-011, Stage 1).

Replaces the runtime spatial mapper's geographic enrichment with a precomputed
table. Joins the views-datafactory's 7 area-majority GAUL parquets by PRIO-GRID
cell id, renames to the postprocessor's 9-column contract, computes the cell
coordinates from the gid, keeps only fully-complete cells, and writes a single
Parquet keyed by priogrid_gid.

The spatial computation already happened upstream (the datafactory's
area-majority join, ADR-039 there). This script does NO geometry — only a
table join and a coordinate formula. No geopandas.

Source of truth: views-datafactory raw parquets (v1.3.0, area-majority).
Contract: the 9 columns hard-validated at views_postprocessing/unfao/managers/
unfao.py:141-153 + 189-197 and views-faoapi handlers.py:1146-1156.

Usage:
    python scripts/build_gaul_lookup.py \
        [--datafactory /path/to/views-datafactory] \
        [--region land_gaul] \
        [--out views_postprocessing/data/gaul_lookup.parquet]
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from views_postprocessing.unfao.gaul_schema import (
    CODE_COLS,
    COORD_COLS,
    METADATA_COLS,
    NAME_COLS,
    SOURCE_RENAME,
    xcoord,
    ycoord,
)


def _resolve_datafactory() -> Path:
    """Locate the views-datafactory checkout without a machine-specific path.

    Order: $VIEWS_DATAFACTORY, then the sibling repo next to this one
    (views_platform/views-datafactory). Overridable with --datafactory.
    """
    env = os.environ.get("VIEWS_DATAFACTORY")
    if env:
        return Path(env)
    sibling = Path(__file__).resolve().parents[2] / "views-datafactory"
    return sibling


def _load_source(datafactory: Path) -> pd.DataFrame:
    """Join the 7 GAUL parquets on gid into one wide frame (source names)."""
    gaul_dir = datafactory / "data" / "raw" / "gaul_admin"
    frames = {}
    for src_col in SOURCE_RENAME:
        t = pq.read_table(gaul_dir / f"{src_col}.parquet")
        s = pd.Series(
            t.column("value").to_pylist(),
            index=t.column("gid").to_pylist(),
            name=src_col,
        )
        frames[src_col] = s
    df = pd.DataFrame(frames)
    df.index.name = "gid"
    return df


def _region_gids(datafactory: Path, region: str) -> set[int] | None:
    """Load a bundled region pgid set; None means 'all complete cells'."""
    if region in ("all", "global_complete"):
        return None
    path = datafactory / "src" / "datafactory_query" / f"{region}_pgids.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Region file not found: {path}. Use a bundled region name "
            f"(e.g. land_gaul, africa_me_legacy) or 'all'."
        )
    return set(json.loads(path.read_text()))


def _provenance(datafactory: Path) -> dict:
    """Pull the land_gaul ledger entry for traceability (best-effort)."""
    ledger = (datafactory / "provenance" / "gaul_admin"
              / "ingestion_ledger.jsonl")
    out = {}
    if ledger.exists():
        for line in ledger.read_text().splitlines():
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("dataset") in ("land_gaul_region",
                                    "gaul_admin_area_majority"):
                out[e["dataset"]] = {
                    k: e[k] for k in
                    ("content_digest", "source_gaul_digest", "timestamp")
                    if k in e
                }
    return out


def build(datafactory: Path, region: str, out: Path) -> pd.DataFrame:
    src = _load_source(datafactory)

    # Optionally restrict to a region's cell set.
    region_gids = _region_gids(datafactory, region)
    if region_gids is not None:
        src = src.loc[src.index.intersection(sorted(region_gids))]

    # Rename to the contract names.
    df = src.rename(columns=SOURCE_RENAME)

    # Keep only fully-complete cells. Incomplete cells must NOT enter the
    # lookup: an unknown/incomplete gid then merges to null downstream and the
    # manager's _validate() gate crashes (fail-loud) instead of shipping a hole
    # or a -1 sentinel. Never carry -1 / "" as a value.
    complete = pd.Series(True, index=df.index)
    for c in CODE_COLS:
        complete &= df[c].notna() & (df[c] != -1)
    for c in NAME_COLS:
        complete &= df[c].notna() & (df[c].astype(str).str.len() > 0)
    dropped = int((~complete).sum())
    df = df[complete].copy()

    # Coordinates from the gid (no geometry needed).
    gids = df.index.to_numpy()
    df["pg_xcoord"] = [xcoord(int(g)) for g in gids]
    df["pg_ycoord"] = [ycoord(int(g)) for g in gids]

    # dtypes: codes numeric, coords float64, names/iso categorical (C-32 memory).
    for c in CODE_COLS:
        df[c] = df[c].astype("int64")
    for c in COORD_COLS:
        df[c] = df[c].astype("float64")
    for c in NAME_COLS:
        df[c] = df[c].astype("category")

    df = df[METADATA_COLS]
    df.index = df.index.astype("int64")
    df.index.name = "priogrid_gid"
    df = df.sort_index()

    # Hard invariants — the lookup must be clean by construction.
    assert df.isna().sum().sum() == 0, "lookup contains nulls"
    for c in CODE_COLS:
        assert (df[c] != -1).all(), f"{c} contains -1 sentinel"

    out.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(df, preserve_index=True)
    meta = dict(table.schema.metadata or {})
    meta[b"adr"] = b"ADR-011"
    meta[b"region"] = region.encode()
    meta[b"n_cells"] = str(len(df)).encode()
    meta[b"n_dropped_incomplete"] = str(dropped).encode()
    meta[b"source_provenance"] = json.dumps(
        _provenance(datafactory)).encode()
    table = table.replace_schema_metadata(meta)
    pq.write_table(table, out)

    print(f"region={region}  cells={len(df):,}  dropped_incomplete={dropped:,}")
    print(f"wrote {out} ({out.stat().st_size/1e6:.2f} MB)")
    return df


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--datafactory", type=Path, default=None)
    ap.add_argument("--region", default="land_gaul")
    ap.add_argument(
        "--out", type=Path,
        default=Path("views_postprocessing/data/gaul_lookup.parquet"),
    )
    args = ap.parse_args()
    datafactory = args.datafactory or _resolve_datafactory()
    if not (datafactory / "data" / "raw" / "gaul_admin").exists():
        raise SystemExit(
            f"views-datafactory not found at {datafactory}. Set $VIEWS_DATAFACTORY "
            f"or pass --datafactory /path/to/views-datafactory."
        )
    build(datafactory, args.region, args.out)


if __name__ == "__main__":
    main()
