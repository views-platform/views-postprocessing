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

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
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


def _load_source(datafactory: Path) -> pa.Table:
    """Join the 7 GAUL parquets on gid into one wide table (source names).

    Arrow throughout since #90 — the sources are parquet, the output is parquet, and
    pandas was only ever the thing in the middle. The join is an inner join on ``gid``:
    a cell missing from any one source has no complete row to contribute, and the
    completeness filter in ``build`` would drop it anyway.
    """
    gaul_dir = datafactory / "data" / "raw" / "gaul_admin"
    table = None
    for src_col in SOURCE_RENAME:
        one = pq.read_table(gaul_dir / f"{src_col}.parquet").select(["gid", "value"])
        one = one.rename_columns(["gid", src_col])
        table = one if table is None else table.join(one, keys="gid", join_type="inner")
    return table


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


def build(datafactory: Path, region: str, out: Path) -> pa.Table:
    """Build the lookup and write it. Arrow end to end (#90).

    **What must not change, and is asserted by the fidelity suite:** the nine declared
    columns in ``METADATA_COLS`` order with ``priogrid_gid`` last, the four name columns
    dictionary-encoded, codes ``int64``, coordinates ``float64``, rows sorted by cell id,
    and the declared metadata keys. The delivered artifact is read as arrow by its only
    consumer (``contract.gaul_lookup.load``), so those are the observable contract.

    **One deliberate difference from the pandas build:** the written file no longer
    carries a ``pandas`` schema-metadata blob. It described an index that arrow does not
    have, nothing in this repository reads the lookup with pandas, and reproducing it
    would have meant keeping knowledge of pandas' metadata format in the one script this
    change exists to remove pandas from.
    """
    src = _load_source(datafactory)

    # Optionally restrict to a region's cell set.
    region_gids = _region_gids(datafactory, region)
    if region_gids is not None:
        wanted = pa.array(sorted(region_gids), type=src.column("gid").type)
        src = src.filter(pc.is_in(src.column("gid"), value_set=wanted))

    # Rename to the contract names, keeping `gid` alongside.
    table = src.rename_columns(
        ["gid"] + [SOURCE_RENAME[c] for c in src.column_names if c != "gid"]
    ) if src.column_names[0] == "gid" else src.rename_columns(
        [SOURCE_RENAME.get(c, c) for c in src.column_names]
    )

    # Keep only fully-complete cells. Incomplete cells must NOT enter the lookup: an
    # unknown/incomplete gid then gathers to null downstream and the delivery's null
    # gate fails loud instead of shipping a hole or a -1 sentinel. Never carry -1 / "".
    # Typed explicitly: on an empty table `pa.array([True] * 0)` infers NULL type, and
    # `pc.and_` then raises ArrowNotImplementedError before the zero-row guard below can
    # say anything useful. Found by the guard's own mutation test.
    complete = pa.array([True] * table.num_rows, type=pa.bool_())
    for c in CODE_COLS:
        col = table.column(c)
        complete = pc.and_(complete, pc.and_(pc.is_valid(col), pc.not_equal(col, -1)))
    for c in NAME_COLS:
        col = table.column(c).cast(pa.string())
        complete = pc.and_(
            complete,
            pc.and_(pc.is_valid(col), pc.greater(pc.utf8_length(col), 0)),
        )
    dropped = int(pc.sum(pc.invert(complete)).as_py() or 0)
    table = table.filter(complete)

    # Coordinates from the gid (no geometry needed). Vectorised over the id array
    # rather than a Python loop per row — the formula is the declared one either way.
    gids = table.column("gid").to_numpy(zero_copy_only=False).astype(np.int64)
    table = table.append_column(
        "pg_xcoord", pa.array([xcoord(int(g)) for g in gids], type=pa.float64())
    ).append_column(
        "pg_ycoord", pa.array([ycoord(int(g)) for g in gids], type=pa.float64())
    )

    # dtypes: codes int64, coords float64, names dictionary-encoded. The dictionary
    # encoding is the artifact's shipped type — it was `category` under pandas and the
    # committed file carries dictionary<values=string, indices=int32>.
    cast = {c: pa.int64() for c in CODE_COLS}
    cast.update({c: pa.float64() for c in COORD_COLS})
    columns, names = [], []
    for c in METADATA_COLS:
        col = table.column(c)
        if c in NAME_COLS:
            col = pc.dictionary_encode(col.cast(pa.string()))
        else:
            col = col.cast(cast[c])
        columns.append(col)
        names.append(c)
    columns.append(table.column("gid").cast(pa.int64()))
    names.append("priogrid_gid")
    table = pa.Table.from_arrays(columns, names=names)
    table = table.sort_by([("priogrid_gid", "ascending")])

    # Hard invariants — the lookup must be clean by construction.
    #
    # These are explicit raises, NOT `assert`: `python -O` strips assert statements
    # entirely, and a stripped run would write an unvalidated lookup that looks
    # identical on disk (register C-61). The -1 check in particular has no downstream
    # backstop — -1 is non-null, so every gate in the delivery chain would pass it
    # straight through to FAO, which is exactly the resolved C-35 defect recurring.
    key = table.column("priogrid_gid")
    if len(pc.unique(key)) != table.num_rows:
        counts = key.value_counts()
        dupes = [
            counts.field("values")[i].as_py()
            for i in range(len(counts))
            if counts.field("counts")[i].as_py() > 1
        ]
        raise LookupBuildError(
            f"{len(dupes)} duplicate gid(s) in the lookup key: {dupes[:10]}. "
            "A duplicated key multiplies rows through a keyed gather with every value "
            "non-null, so no downstream gate can see it (C-59)."
        )
    n_null = sum(table.column(c).null_count for c in table.column_names)
    if n_null:
        raise LookupBuildError(
            f"lookup contains {n_null} null value(s); only fully-complete cells may "
            "enter it, so that an ABSENT cell (never a partial one) is what fails "
            "downstream."
        )
    for c in CODE_COLS:
        n_sentinel = int(pc.sum(pc.equal(table.column(c), -1)).as_py() or 0)
        if n_sentinel:
            raise LookupBuildError(
                f"{c} contains {n_sentinel} -1 sentinel(s). -1 is non-null, so it would "
                "reach FAO through every gate as a country/admin code (cf. C-35)."
            )
    # Register C-76: a build that filtered every cell out is not a result. Downstream
    # this fails late and confusingly — `build_historical_table` raises about missing
    # geography rather than about an empty lookup, and by then the artifact is
    # committed. Two lines here, at the moment a human is present.
    if table.num_rows == 0:
        raise LookupBuildError(
            f"the build produced ZERO cells for region {region!r}. Either the region "
            "filtered every cell out, or the join found no overlap between the seven "
            "source parquets. An empty lookup is writable and looks like a result; it "
            "is not one."
        )

    out.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        b"adr": b"ADR-011",
        b"region": region.encode(),
        b"n_cells": str(table.num_rows).encode(),
        b"n_dropped_incomplete": str(dropped).encode(),
    }
    prov = _provenance(datafactory, datasets=(AREA_MAJORITY_DATASET, stamp_dataset(region)))
    # The DECLARED stamp: one flat key, composed here, read verbatim by the consumer
    # (C-60). Key order in parquet metadata carries no meaning; this is a dict.
    meta[b"lookup_version"] = _lookup_version(region, prov).encode()
    meta[b"source_provenance"] = json.dumps(prov).encode()
    table = table.replace_schema_metadata(meta)
    pq.write_table(table, out)

    print(f"region={region}  cells={table.num_rows:,}  dropped_incomplete={dropped:,}")
    print(f"wrote {out} ({out.stat().st_size/1e6:.2f} MB)")
    return table


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
