# Class Intent Contract: GaulLookupEnricher

**Status:** Draft
**Owner:** PRIO MD&D Team
**Last reviewed:** 2026-06-18
**Related ADRs:** ADR-011 (replace runtime mapper with precomputed lookup)

---

## 1. Purpose

> Attach the 9 geographic metadata columns to a prediction frame by merging a
> precomputed GAUL lookup table on the PRIO-GRID cell id.

It is the lookup-based replacement for `PriogridCountryMapper`'s runtime spatial
enrichment: the spatial computation has already happened upstream (the
views-datafactory area-majority join), so this class does only a table join.

---

## 2. Non-Goals (Explicit Exclusions)

- This class does **not** perform spatial computation — no geometry, no
  shapefiles, no geopandas, no area-majority calculation.
- This class does **not** build the lookup table (that is
  `scripts/build_gaul_lookup.py`, run offline).
- This class does **not** fill, impute, or invent metadata for unmatched cells.
- This class does **not** validate the result. Null/coverage enforcement lives on the
  delivery path — `contract/historical.assert_metadata_complete` at artifact build and
  `delivery/coverage.py` for the region contract. It is **not** the manager's
  `_validate()`, which stopped null-gating in #149 and now asserts only that the read
  resolved. (Corrected 2026-08-02; PR #200 retired the same claim in the manager's CIC
  and this one was left standing.)
- This class does **not** read from the datafactory, viewser, or Appwrite.

---

## 3. Responsibilities and Guarantees

- Loads exactly one lookup Parquet at construction and verifies it carries the key
  plus the 9 contract columns; missing columns raise at construction, and so does an
  **empty** lookup — every cell would gather to null and the delivery would then
  complain about missing metadata rather than about a missing lookup (S4 / #89).
- Returns the input frame augmented with exactly the 9 columns of
  `gaul_schema.METADATA_COLS`: codes numeric, coordinates float, **names and iso as
  `object`**.
  *Changed in S4 (#89).* They were `category`, inherited from the pandas merge that
  read the artifact's dictionary encoding. The gather that replaced it assigns plain
  values. Measured on a 200-row output: category 1,795,191 bytes, object 60,061 —
  a categorical carries the artifact's full 64,742-entry dictionary whatever the
  output size. The builder still writes the artifact with dictionary-encoded names
  (`# names/iso categorical (C-32 memory)`); that governs the file, not this output.
- A cell id present in the lookup is enriched with that cell's metadata.
- A cell id **absent** from the lookup yields **null** metadata for that row —
  never a sentinel, never a fabricated value (fail-loud downstream).
- Row count, row order **and index** of the input are preserved. Pinned by
  `tests/test_enrichment.py::TestFramePropertiesPreserved` across six shapes —
  ordered, reversed, duplicated, single, empty, and a non-default index.
  (An earlier draft of this line claimed *eight* shapes "including unknown gids",
  counting a throwaway development script rather than the committed suite, and naming
  a shape that class does not exercise. Unknown gids are covered, for null-value
  correctness, by `TestFailLoud` — a different guarantee.)
  On **empty** input this is now *more* true than before: the pandas merge replaced the
  input's `RangeIndex` with an object-dtype `Index`, where the gather leaves it
  untouched. The only behavioural difference found, and it is in the direction the
  guarantee above already claimed.

---

## 4. Inputs and Assumptions

- A lookup Parquet exists at the configured path (default: the committed
  `views_postprocessing/data/gaul_lookup.parquet`), indexed by `priogrid_gid`,
  containing only fully-complete cells (no nulls, no `-1`, no empty strings).
- The input DataFrame has a column named by `pg_id_col` holding PRIO-GRID cell
  ids; a missing `pg_id_col` raises `ValueError`.
- The lookup is the single source of geographic truth — the caller does not
  expect this class to reconcile it against any other source.

---

## 5. Outputs and Side Effects

- Output: the input frame (or, with `only_metadata=True`, just `pg_id_col` +
  `time_id_col`) with the 9 metadata columns attached by **keyed gather**.
  *Changed in S4 (#89):* this was a pandas left-merge on the lookup's index. The
  lookup is now read with pyarrow, sorted once, and addressed by `np.searchsorted`.
  Attaching metadata to a frame is a keyed gather, not frame algebra, and it never
  needed a merge — which is also what frees the builder to stop writing pandas index
  metadata (S5 / #90).
- Public attribute: `lookup_version` — a short, stampable id read from the
  lookup's **declared** `lookup_version` metadata key at construction
  (`<region>@<8-char source digest>`). Delegates to
  `contract.gaul_lookup.version`. The manager stamps it on each delivery so a
  delivery is traceable to the exact lookup build.
  **It does not degrade.** An artifact carrying no declared key raises
  `gaul_lookup.LookupVersionError` (logged at ERROR first, per ADR-008) rather
  than returning a placeholder. Until S5 (#186) this returned the string
  `"unknown"` whenever views-datafactory's ingestion-ledger shape moved under
  it — silently, in the one field register C-15 exists to answer *after* a
  suspect delivery. See register **C-60**.
- Side effects: logs the lookup size + version at construction (INFO); logs a
  WARNING with the count and sample of unmatched cell ids when any occur; logs
  ignored mapper-only kwargs at DEBUG. No file writes, no network.

---

## 6. Failure Modes and Loudness

- **Raises** at construction if the lookup file is missing or lacks a contract
  column.
- **Raises** `ValueError` if `pg_id_col` is not in the input.
- **Does not raise** on unmatched cells — it surfaces them as nulls and logs a
  WARNING naming the unknown cells, and separately counting rows that carried no
  usable cell id at all. This is deliberate: enforcement is a single point on the
  delivery path (`historical.assert_metadata_complete`), so a coverage hole fails
  loudly there, not in two places. Passing a sentinel for unmatched cells would be a **bug** (it would
  bypass that gate). Aligns with ADR-003 (fail loud on semantic ambiguity).

---

## 7. Boundaries and Interactions

- Allowed to depend on: numpy, pyarrow, `gaul_schema`, and a local Parquet file.
  **pandas is interface-only** — callers hand this class DataFrames and get one back,
  but nothing here constructs, reads or joins one, and its import is under
  `if TYPE_CHECKING` (S4 / #89). `tests/test_doc_accuracy.py` asserts by AST that the
  package has **zero** runtime pandas importers.
- Must **not** depend on: geopandas/shapely, the runtime mapper, the
  datafactory, viewser, Appwrite, or any network resource.
- Treats the lookup table as an opaque, trusted artifact produced by the build
  script; it does not re-validate the table's spatial correctness.

---

## 8. Examples of Correct Usage

```python
enricher = GaulLookupEnricher()
out = enricher.enrich_dataframe_with_pg_info(
    df.reset_index(), pg_id_col="priogrid_gid", time_id_col="month_id",
    only_metadata=True,
)
# out has the 9 metadata columns; unmatched cells are null.
```

Signature-compatible with the runtime mapper it replaced (same method name and key
kwargs), which is why the mapper-only kwargs are still accepted and ignored.
**The manager does not call this class** — it has no `enrich` reference at all, and
reads the lookup directly via `gaul_lookup.load()` (register C-66). This example is a
build/verification-path usage. Whether the class should survive that is register
**C-75**.

---

## 9. Examples of Incorrect Usage

- Filling unmatched cells with `-1`/`""`/`"unknown"` to "avoid validation
  errors" — defeats the fail-loud contract and ships wrong data to FAO.
- Using it to enrich against a lookup built for a different region without
  expecting nulls for out-of-region cells.
- Calling it expecting spatial recomputation when the lookup is stale — regenerate
  the lookup with the build script instead.

---

## 10. Test Alignment

`tests/test_enrichment.py`:
- **Green:** the 9 columns present; values match the lookup; row count preserved;
  codes numeric / coords float.
- **Beige:** lookup integrity (cell count, no nulls, no `-1`, dtypes); coordinate
  formula (independent oracle).
- **Red:** unknown cell id and excluded ocean cells yield null; missing
  `pg_id_col` raises.

---

## 11. Evolution Notes

- Stable: the 9-column contract and the fail-loud-on-unmatched behavior (changing
  either is a coordinated change across this repo and views-faoapi).
- Expected to change: the lookup's cell-set/region and its source GAUL version,
  via re-running the build script. Such regenerations must not change the schema.

---

## End of Contract

This document defines the **intended meaning** of `GaulLookupEnricher`.

Changes to behavior that violate this intent are bugs.
Changes to intent must update this contract.
