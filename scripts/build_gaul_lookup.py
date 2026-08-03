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

from views_postprocessing.contract.gaul_schema import (
    CODE_COLS,
    COORD_COLS,
    METADATA_COLS,
    NAME_COLS,
    SOURCE_RENAME,
    xcoord,
    ycoord,
)


class LookupBuildError(ValueError):
    """The lookup cannot be built as declared — never write a half-valid artifact."""


def _resolve_datafactory() -> Path:
    """Locate the views-datafactory checkout without a machine-specific path.

    Order: $VIEWS_DATAFACTORY, then the sibling repo next to this one
    (views_platform/views-datafactory). Overridable with --datafactory.

    **Deliberately duplicated with** ``tests/conftest.sibling_repo`` (S7 / #188,
    register C-46). Not an oversight and not laziness:

    - a script must not import from ``tests/`` — that is the dependency direction
      backwards, and it would make the build depend on the test tree;
    - the contracts differ. This returns a ``Path`` **even when the checkout is
      absent**, so ``main`` can raise its own message naming both the flag and the
      variable. The test helper returns ``None``, because a missing sibling is a
      normal skip, not an error.

    Two copies that are understood beat one abstraction that is guessed. What is
    guarded instead is the thing that actually matters — that they **agree** —
    pinned by ``tests/test_gaul_lookup_fidelity.py``. If they ever resolve to
    different checkouts, a rebuilt artifact would be verified against a producer it
    was not built from.
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


#: The ledger dataset naming the whole GAUL area-majority join, used to stamp an
#: unregionalised (``--region all``) build.
AREA_MAJORITY_DATASET = "gaul_admin_area_majority"

#: Length of the digest carried in a stamp. Declared so producer and consumer agree.
DIGEST_CHARS = 8


def stamp_dataset(region: str) -> str:
    """DECLARED: which ledger dataset's digest stamps this region's build.

    One rule, no fallback. ``--region all`` is stamped by the area-majority join that
    produced every value; a regional build is stamped by that region's own definition
    entry, because the region determines which rows exist and a change to it changes
    the artifact.

    **Why not "whichever entry happens to be present" (register C-60, review of #186).**
    The first draft read ``land_gaul_region or gaul_admin_area_majority``. Since
    ``_provenance`` does not take a region, ``land_gaul_region`` is present for *every*
    build — so ``--region all`` would have been stamped ``all@f74d3b2b``, the land_gaul
    region definition's digest, on a global artifact. Authoritative-looking and wrong,
    silently: the exact defect class C-60 exists to close, reintroduced one level up.
    A region with no ledger entry is now refused, not substituted.
    """
    return AREA_MAJORITY_DATASET if region == "all" else f"{region}_region"


def _lookup_version(region: str, provenance: dict) -> str:
    """Compose the DECLARED build stamp: ``<region>@<source digest>``.

    This is the value written as a flat ``lookup_version`` key and read back verbatim
    by ``contract.gaul_lookup.version`` — register **C-60**. Composing it here is the
    point: the builder is the only thing holding both the region and the producer's
    ledger, so the consumer stops needing to know views-datafactory's schema in order
    to answer "which lookup produced this delivery?".

    **Refuses an untraceable build.** ``_provenance`` is best-effort by design — a
    missing or reshaped ledger yields ``{}``. Previously that produced the string
    ``"unknown"`` at *delivery* time, silently, in the one field C-15 exists to answer
    after a suspect delivery. Failing here moves the error to the moment a human is
    present to fix it: the build.
    """
    dataset = stamp_dataset(region)
    digest = str((provenance.get(dataset) or {}).get("content_digest", ""))
    if len(digest) < DIGEST_CHARS:
        raise LookupBuildError(
            f"cannot compose a lookup_version for region {region!r}: the datafactory "
            f"ingestion ledger has no usable content_digest for {dataset!r} "
            f"(provenance/gaul_admin/ingestion_ledger.jsonl; need at least "
            f"{DIGEST_CHARS} characters, got {len(digest)}). An artifact without a "
            "declared version cannot be traced back to the build that made it, which "
            "is what register C-15 needs after a suspect delivery. Rebuild against a "
            "datafactory checkout whose ledger declares that dataset — this build is "
            "NOT stamped from some other region's entry."
        )
    return f"{region}@{digest[:DIGEST_CHARS]}"


def _provenance(datafactory: Path, *, datasets: tuple[str, ...]) -> dict:
    """Pull the named ledger entries for traceability (best-effort).

    Kept richer than the stamp — it carries timestamps and the upstream GAUL digest,
    which are worth having. What changed in C-60 is that the STAMP is no longer
    derived from it by the consumer; see ``_lookup_version``.

    **The ledger is append-only and the LAST entry per dataset wins.** The real file
    carries 14 ``gaul_admin_area_majority`` entries and 2 ``land_gaul_region`` ones;
    this loop overwrites, so the most recent ingestion is what stamps the build. That
    was harmless while provenance was decorative. Since C-60 the stamp *raises* on its
    absence, so the selection rule is load-bearing and is stated here rather than left
    to be inferred from the loop. (Recency-over-a-broad-match is the shape register
    **C-73** was opened for on the forecast path; here it is intended, and now said.)
    """
    ledger = (datafactory / "provenance" / "gaul_admin"
              / "ingestion_ledger.jsonl")
    out = {}
    if ledger.exists():
        for line in ledger.read_text().splitlines():
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("dataset") in datasets:
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
    #
    # These are explicit raises, NOT `assert`: `python -O` strips assert statements
    # entirely, and a stripped run would write an unvalidated lookup that looks
    # identical on disk (register C-61). The -1 check in particular has no downstream
    # backstop — -1 is non-null, so every gate in the delivery chain would pass it
    # straight through to FAO, which is exactly the resolved C-35 defect recurring.
    if not df.index.is_unique:
        dupes = df.index[df.index.duplicated()].unique().tolist()
        raise LookupBuildError(
            f"{len(dupes)} duplicate gid(s) in the lookup index: {dupes[:10]}. "
            "A duplicated key multiplies rows through the enricher's left-merge with "
            "every value non-null, so no downstream gate can see it (C-59)."
        )
    n_null = int(df.isna().sum().sum())
    if n_null:
        raise LookupBuildError(
            f"lookup contains {n_null} null value(s); only fully-complete cells may "
            "enter it, so that an ABSENT cell (never a partial one) is what fails "
            "downstream."
        )
    for c in CODE_COLS:
        n_sentinel = int((df[c] == -1).sum())
        if n_sentinel:
            raise LookupBuildError(
                f"{c} contains {n_sentinel} -1 sentinel(s). -1 is non-null, so it would "
                "reach FAO through every gate as a country/admin code (cf. C-35)."
            )

    out.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(df, preserve_index=True)
    meta = dict(table.schema.metadata or {})
    meta[b"adr"] = b"ADR-011"
    meta[b"region"] = region.encode()
    meta[b"n_cells"] = str(len(df)).encode()
    meta[b"n_dropped_incomplete"] = str(dropped).encode()
    prov = _provenance(datafactory, datasets=(AREA_MAJORITY_DATASET, stamp_dataset(region)))
    # The DECLARED stamp: one flat key, composed here, read verbatim by the consumer
    # (C-60). Key order in parquet metadata carries no meaning; this is a dict.
    meta[b"lookup_version"] = _lookup_version(region, prov).encode()
    meta[b"source_provenance"] = json.dumps(prov).encode()
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
