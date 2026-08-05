# ADR-011: Replace Runtime Spatial Mapper with Precomputed Lookup Table

<!-- legacy-ok-file: this ADR IS the decision to retire the runtime mapper. `PriogridCountryMapper`, `mapping.py`, `geopandas` and the cache machinery are its subject, named throughout and correctly. Marking the document once says that where a reader sees it; marking fourteen lines would be noise pretending to be rigour. -->

**Status:** Accepted  
**Date:** 2026-06-02  
**Deciders:** Project maintainers (PRIO MD&D Team)  
**Consulted:** FAO-FSFC (via Pre-release Note 02 and Release Note 02 confirmation)  
**Informed:** All contributors, UN FAO operational team  

---

## Context

The `PriogridCountryMapper` in `mapping.py` (3,122 lines) performs runtime spatial intersection to assign each PRIO-GRID cell to a country (Admin 0), Admin 1, and Admin 2 region using an area-majority rule. It loads four shapefiles (774 MB via git-lfs), depends on `geopandas` (~200 MB of compiled C libraries via GDAL/GEOS/PROJ), and employs a dual-mode cache system (joblib disk cache + cachetools in-memory LRU) with multiprocessing and threading support.

This architecture was necessary when the VIEWS pipeline did not provide administrative boundary metadata — the postprocessor had to solve the mapping problem at runtime. The VIEWS datafactory now provides centroid-based GAUL assignments at build time, but the FAO contract requires area-majority assignment, not centroid-based.

A comprehensive audit of this codebase identified 21 open risk register concerns, of which approximately 15 are internal to the runtime mapper: cache duplication (C-05, C-06), thread safety (C-16), stale cache (C-14), god class (C-11), import side effects (C-02, C-10), undeclared dependencies (C-07), planar area distortion (C-08), and multiple error-hiding mechanisms (C-12, C-19, C-20, C-21). Eight rounds of falsification audits and two expert code reviews confirmed these concerns are real and deeply intertwined.

The core question was whether the area-majority algorithm is a deliberate FAO requirement or a historical accident. This has been definitively answered.

---

## Decision

Replace the 3,122-line runtime spatial mapper (`PriogridCountryMapper` in `mapping.py`) with a **precomputed area-majority lookup table** stored as a Parquet file.

**In scope:**
- One-time precomputation: run the current mapper against all ~65,000 PRIO-GRID cells, producing a static table mapping each GID to its area-majority country, Admin 1, and Admin 2 assignments
- Store the result as a Parquet file (estimated ~2-5 MB) either bundled in this package or hosted in the datafactory
- Replace the runtime mapper with a simple Parquet-join enricher: load the lookup table, merge on GID
- Remove the bundled shapefiles (774 MB git-lfs), the `geopandas` dependency, and all cache machinery
- Update the `UNFAOPostProcessorManager` to use the new enricher instead of `PriogridCountryMapper`

**Out of scope:**
- Changing the assignment algorithm: the area-majority rule is contractually locked and must be preserved exactly
- Changing the GAUL shapefile versions: the precomputation uses the same GAUL 2024 L1/L2 shapefiles currently bundled
- Modifying the datafactory's centroid-based assignments: those serve a different purpose for the assembled grid

---

## Rationale

### The area-majority rule is a confirmed FAO requirement

Pre-release Note 02 (Decision Point A.1) formally proposed both options to FAO-FSFC:
- **Option A (recommended):** Area-majority — assign the cell to the country containing the largest share of its area
- **Option B:** Centroid-based — assign the cell to the country containing its centroid

Release Note 02 (`summary.tex`) records:

> "FAO-FSFC has provided written confirmation agreeing to all recommended options presented in Decision Points A.1-A.3 of the Pre-release Note. The aggregation rules listed below are therefore considered reviewed, confirmed, and locked under this release."

> "Each PRIO-GRID cell is assigned to a single country using an area-majority rule, whereby the cell is allocated to the country containing the largest share of its area."

The area-majority rule is not negotiable. But it does not need to be computed at runtime.

Release Note 02 (`topic_a.tex`) further specifies:
- **Sequential allocation invariant:** "Aggregation does not result in cross-border allocation at subnational levels. All Admin 1 and Admin 2 assignments are constrained to the country determined at the Admin 0 stage."
- **Small Admin 2 units:** informational flagging only — "does not imply automatic reallocation, suppression, or modification of values."
- **Explicitly out of scope:** centroid-based assignment, direct multi-level allocation, automatic adjustment of Admin 2 units, quantitative thresholds for minimum mapping units.

Release Note 01 (`topic_c.tex`) confirms annual GAUL updates: "FAO will release updated GAUL boundaries annually. Only boundaries that change will be updated." The precomputed lookup table must be regenerable when new GAUL shapefiles arrive.

### Runtime computation is unnecessary for a static mapping

The PRIO-GRID is a fixed global grid (~65,000 cells). The GAUL boundaries change infrequently (the current version is GAUL 2024). The area-majority assignment for each cell is deterministic given the shapefiles. Computing it at runtime — loading 774 MB of shapefiles, building spatial indices, performing geometric intersections — is equivalent to computing `2 + 2` every time instead of storing `4`.

A one-time precomputation produces a ~65K-row lookup table that can be joined to any DataFrame in milliseconds. The result is byte-identical to what the runtime mapper produces, but without the 3,122 lines of code, the geopandas dependency, the cache machinery, or the 15 associated risk register concerns.

### The precomputed table eliminates the majority of registered risks

Of 21 open risk register concerns, approximately 15 are internal to the runtime mapper. Replacing it with a lookup table eliminates:
- **Cluster A** (cache architecture): C-05, C-06, C-14, C-16 — no cache needed
- **Cluster C** (import side effect): C-02, C-10 — no module-level shapefile loading
- **Cluster B** (mapper-internal error hiding): C-12 (geometry errors), C-20 (zero-area), and most of C-19 — no runtime spatial operations
- **Standalone:** C-07 (undeclared deps), C-08 (planar distortion), C-11 (god class), C-17 (column naming chain)

The remaining concerns (C-03, C-13, C-15, C-19 partial, C-21, C-22, C-23) are in `unfao.py` or operational — they survive regardless of the mapper's implementation.

---

## Considered Alternatives

### Alternative A: Keep the runtime mapper, refactor incrementally

- **Pros:** No one-time precomputation needed. Preserves the ability to handle shapefile updates without regeneration.
- **Cons:** Requires resolving Clusters A, B, C, D — estimated weeks of refactoring work across 3,100 lines. The refactored mapper would still load geopandas, still bundle 774 MB of shapefiles, and still perform runtime spatial operations that produce a deterministic result.
- **Reason for rejection:** The mapping is deterministic and the shapefiles change infrequently. Runtime computation of a static result is unnecessary complexity.

### Alternative B: Use the datafactory's centroid-based assignments

- **Pros:** No new code needed — just add GAUL columns to the UNFAO queryset config. Eliminates mapping.py entirely.
- **Cons:** Centroid-based assignment disagrees with area-majority on border cells (~5% of grid). FAO has explicitly confirmed area-majority as the required rule.
- **Reason for rejection:** Contractually incompatible. FAO-FSFC confirmed Option A (area-majority) in writing. Centroid-based was explicitly presented as Option B and not selected.

### Alternative C: Precompute and host in the datafactory

- **Pros:** Single source of truth for all GAUL assignments. The factory already handles data assembly.
- **Cons:** Requires changes to `views-datafactory` (separate repo, separate ownership). Introduces a cross-repo dependency for the postprocessor.
- **Reason for deferral:** Not rejected, but deferred. The initial implementation should bundle the lookup table in this package for simplicity. Migration to the factory can happen later if both teams agree.

---

## Consequences

### Positive
- Eliminates ~15 of 21 open risk register concerns in one structural change
- Removes 774 MB of git-lfs shapefile data from the repository
- Removes the `geopandas` dependency (~200 MB of compiled C libraries)
- Reduces `mapping.py` from 3,122 lines to ~50 lines (Parquet load + merge)
- Eliminates all cache machinery (joblib, cachetools, threading, multiprocessing)
- Eliminates the module-level import side effect (no shapefile loading at import time)
- Enrichment becomes a simple DataFrame merge — milliseconds instead of minutes
- The lookup table is auditable: a 65K-row Parquet file where every assignment can be inspected

### Negative
- Requires a one-time precomputation job using the current mapper (estimated: 1-2 hours of runtime)
- When shapefiles are updated (e.g., GAUL 2025), the lookup table must be regenerated
- The precomputation job itself depends on geopandas — but only as a one-time offline tool, not a runtime dependency
- During the transition, the old and new enrichment paths must produce identical results (verified by a diff test)

These trade-offs are accepted intentionally.

---

## Prerequisite: Understand the Data Path and Column Naming Before Choosing the Lookup Table Schema

### The problem in plain terms

When we build the precomputed lookup table, we have to choose what columns it contains and what they're called. This sounds trivial but it isn't, because **two different documents in this project use different names for the same things**, and we don't fully understand which names reach the FAO.

### What the postprocessor currently produces

The `_append_metadata` method in `unfao.py` (lines 146-158) enriches prediction data with these columns:

| Column in postprocessor output | What it contains |
|---|---|
| `country_iso_a3` | Country code using ISO Alpha-3 (e.g., `NGA`, `TCD`, `KEN`) |
| `admin1_gaul1_code` | GAUL Level 1 numeric code |
| `admin1_gaul1_name` | GAUL Level 1 name (province/state) |
| `admin1_gaul0_code` | GAUL Level 0 numeric code (parent country) |
| `admin1_gaul0_name` | GAUL Level 0 name (parent country name) |
| `admin2_gaul2_code` | GAUL Level 2 numeric code |
| `admin2_gaul2_name` | GAUL Level 2 name (district/county) |
| `pg_xcoord` | Cell centroid longitude |
| `pg_ycoord` | Cell centroid latitude |

These names come from the mapper's internal conventions. They were never formally agreed with anyone — they're whatever the original developer chose.

### What the FAO contract specifies

Release Note 01, Topic C (confirmed and locked by FAO-FSFC) specifies a different set of conventions for the API that delivers data to FAO:

| FAO contract field | What it contains | Postprocessor equivalent |
|---|---|---|
| UN M49 code | Country code using UN M49 numeric system (e.g., `566`, `148`, `404`) | `country_iso_a3` uses ISO Alpha-3 instead — **different coding system** |
| `ADM1_CODE` | GAUL Level 1 numeric code | `admin1_gaul1_code` — **same data, different column name** |
| `ADM1_NAME` | GAUL Level 1 name | `admin1_gaul1_name` — **same data, different column name** |
| `ADM2_CODE` | GAUL Level 2 numeric code | `admin2_gaul2_code` — **same data, different column name** |
| `ADM2_NAME` | GAUL Level 2 name | `admin2_gaul2_name` — **same data, different column name** |
| `lat` | Latitude | `pg_ycoord` — **same data, different column name** |
| `lon` | Longitude | `pg_xcoord` — **same data, different column name** |

The country identifier is the biggest difference: ISO Alpha-3 (`NGA`) vs UN M49 (`566`) are completely different coding systems, not just different column names.

### Why this matters for the precomputed table

The precomputed lookup table will have columns. Those columns will be the new source of truth for all enrichment. We need to decide:

- Should the table use the **current postprocessor names** (`country_iso_a3`, `admin1_gaul1_code`, `pg_xcoord`)? This preserves backward compatibility but perpetuates names that don't match the FAO contract.
- Should the table use the **FAO contract names** (`ADM1_CODE`, `lat`, plus a UN M49 column)? This aligns with the locked contract but breaks every downstream consumer that expects the current names.
- Should the table contain **both** (e.g., both `country_iso_a3` AND a `country_m49` column)? Safest but adds complexity.

### What we don't know yet

There is a gap in our understanding of the data path. We know two things:

1. **The postprocessor** uploads enriched Parquet files to an Appwrite bucket (this repo, `_save()` method).
2. **FAO accesses data** through "a live API endpoint hosted on a dedicated production domain" (Release Note 02, conclusion).

What we don't know is: **what happens between the Appwrite upload and the API endpoint?**

Three possibilities exist (see D-06 in the risk register):

- **Possibility A:** A separate API service reads from Appwrite, renames columns (`admin1_gaul1_code` → `ADM1_CODE`, `country_iso_a3` → M49 lookup, `pg_xcoord` → `lon`), and serves the FAO contract schema. If this is the case, the postprocessor's names don't matter to FAO — they're internal — and the lookup table should keep the current names for backward compatibility.

- **Possibility B:** No renaming layer exists. The postprocessor's Parquet files are served directly (or near-directly) to FAO. If this is the case, the current names violate the locked contract, and the lookup table is the moment to fix it.

- **Possibility C:** The Appwrite upload and the API are separate delivery paths for different purposes. The postprocessor delivers raw data to Appwrite for FAO's own processing (they may not care about column names). The API delivers a formatted version (with contract-compliant names) from a different source. If this is the case, the lookup table's names are irrelevant to the API contract.

### What to do

**Investigate before deciding.** Trace the data path from Appwrite upload to what FAO actually sees. Specifically:

1. Does the VIEWS API service (the "live endpoint" mentioned in RN02) read from the Appwrite bucket that this postprocessor uploads to?
2. If yes, does it rename columns before serving?
3. If no, where does the API get its data?

Until this is understood, the precomputed lookup table should use the **current postprocessor column names** (preserving backward compatibility) and optionally include additional columns (e.g., `country_m49`) that would be needed if the table eventually serves the API directly. Do NOT rename existing columns without understanding what breaks downstream.

This investigation is tracked as D-06 in the risk register and C-24 (schema divergence concern).

---

## Implementation Notes

### Step 1: Precompute the lookup table

Run the current `PriogridCountryMapper` against all ~65,000 PRIO-GRID cells. For each cell, store:
- `priogrid_gid` (int)
- `pg_xcoord`, `pg_ycoord` (float — cell centroid)
- `country_iso_a3` (str — area-majority country)
- `admin1_gaul1_code`, `admin1_gaul1_name` (int, str)
- `admin1_gaul0_code`, `admin1_gaul0_name` (int, str — parent country from GAUL)
- `admin2_gaul2_code`, `admin2_gaul2_name` (int, str)

Save as `views_postprocessing/data/priogrid_gaul_lookup.parquet`.

This requires a machine with Git LFS installed to access the actual shapefiles.

### Step 2: Replace the mapper with a lookup enricher

Replace `PriogridCountryMapper` with a function that:
1. Loads the Parquet lookup table (once, at init)
2. Merges it onto the input DataFrame by `priogrid_gid`

### Step 3: Update the manager

Change `_append_metadata` to use the lookup enricher instead of `get_default_mapper().enrich_dataframe_with_pg_info()`.

### Step 4: Remove the old mapper

Delete `mapping.py`, the `shapefiles/` directory, and the git-lfs configuration for shapefiles.

### Step 5: Update dependencies

Remove `geopandas`, `joblib`, `shapely` from the dependency tree (they may still come via `views-pipeline-core` but are no longer directly needed).

### Guardrails

- Before removing the old mapper, run a diff test: enrich a representative DataFrame with both the old mapper and the new lookup, verify byte-identical results for all cells
- The precomputation script should be preserved (in a `scripts/` directory or separate repo) so the lookup table can be regenerated when shapefiles are updated

---

## Validation & Monitoring

- **Diff test:** Old mapper output vs new lookup output must be identical for all ~65K cells
- **Schema test:** The enriched DataFrame must have exactly the same columns with the same dtypes as the current output
- **Regression signal:** If any GAUL code in the lookup table doesn't appear in the GAUL shapefiles, the table is stale
- **Reconsidering trigger:** If FAO requests real-time remapping (e.g., disputed territory updates mid-cycle), the precomputed approach may need augmentation with a small runtime override mechanism

---

## Open Questions

- Should the lookup table be bundled in this package or hosted externally (e.g., in the datafactory or an Appwrite bucket)?
- When GAUL shapefiles are updated (FAO releases annually, partial updates only — RN01 Topic C), who is responsible for regenerating the lookup table? Should this be automated as part of the shapefile update workflow? Can partial regeneration (only affected cells) be supported?
- Should the precomputation script also produce a centroid-based table for comparison, to document exactly which cells differ between the two methods?

---

## References

- Pre-release Note 02, Decision Points A.1-A.3: formal proposal of area-majority vs centroid-based assignment
- Release Note 02, `summary.tex`: FAO-FSFC written confirmation of area-majority rule
- Release Note 02, `topic_a.tex`: detailed specification of the sequential majority allocation rule
- Risk Register: Cluster E (C-23, D-05), Clusters A, B, C, D
- ADR-001: Ontology of views-postprocessing (defines Geographic Data Assets and Spatial Mapping Engine categories — this ADR transitions the latter from runtime computation to static data)
