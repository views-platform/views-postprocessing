# ADR-011 Implementation Assessment

## Current State: What We Know and Don't Know

### What we know (verified in this session)

**The algorithm is correct.** The falsification campaign (Layer 2, Claims 2.1-2.4) verified against synthetic data:
- Interior cells get the right country with overlap_ratio = 1.0
- Border cells get the country with the largest area share
- The sequential allocation invariant holds (admin1/admin2 within the assigned country)
- The enrichment output matches the manager's 9 expected columns

**The FAO contract is area-majority.** Release Note 02 confirms in writing: "Each PRIO-GRID cell is assigned to a single country using an area-majority rule." This is locked.

**The datafactory uses a different algorithm.** The views-datafactory's `gaul_admin.py` uses centroid-based point-in-polygon, not area-majority. For ~95% of cells this gives the same answer. For border cells it can disagree. The datafactory already stores its results as Parquet files (`data/raw/gaul_admin/*.parquet`, 86,091 cells, 7 variables).

**The postprocessor's config_queryset.py now sources from the datafactory** (recently changed from VIEWSER). It requests 3 features: `ged_sb_best`, `ged_ns_best`, `ged_os_best`. It does NOT request any GAUL columns — the mapper adds them at runtime.

### What we DON'T know (not verified)

**We have never seen the full pipeline run.** The pipeline requires:
- `views-pipeline-core` installed (not in this environment)
- Git LFS installed (not available — shapefiles are stubs)
- Appwrite credentials and endpoints configured (not available)
- ViewsER or datafactory data source accessible (not tested)

We can read the code, trace the logic, and test with synthetic data. But we have NOT:
- Watched `_read()` download real data from ViewsER or Appwrite
- Watched `_transform()` enrich a real DataFrame with real shapefiles
- Watched `_validate()` pass or fail on real enriched data
- Watched `_save()` upload to the real Appwrite bucket
- Confirmed that the data FAO receives is actually produced by this code

**We don't know the Appwrite-to-FAO data path.** Release Note 02 says FAO accesses data via "a live API endpoint." The postprocessor uploads to Appwrite. Something between Appwrite and the API endpoint may transform the data (rename columns, convert ISO A3 to M49). We don't know if that layer exists or what it does (D-06).

**We don't know if the current output is correct for real data.** The algorithm is correct on synthetic rectangles. Real GAUL shapefiles have complex coastlines, enclaves, disputed territories, and admin boundaries that don't align with the grid. We haven't seen the mapper produce results for real GIDs like 148345 (Tanzania) or 162456 (Nigeria).

**We don't know the exact column names the downstream consumer sees.** The postprocessor produces `country_iso_a3`, `admin1_gaul1_code`, `pg_xcoord`. The FAO contract says `ADM1_CODE`, `lat`, UN M49. We don't know if a renaming layer exists between Appwrite and the API (C-24, D-06).

---

## The Core Risk

**If we change the enrichment logic and break the output, we won't know until the FAO reports a problem.** There is no:
- Staging environment to test against
- Diff test comparing old vs new output (requires LFS)
- Integration test running the real pipeline end-to-end (requires views-pipeline-core + Appwrite)
- Acceptance test with known-good reference output to compare against

The 88 tests we wrote verify the algorithm against synthetic data. They verify the boundary contract (mapper output matches manager's filter_cols). They verify regression protection for our fixes. But they do NOT verify that the complete pipeline produces correct output for real data.

**We are confident the algorithm is right. We are not confident we can change the plumbing without breaking something we can't see.**

---

## What Would Need to Be True Before We Can Safely Change This

### Option 1: See it run first
Before touching the enrichment logic:
1. Get access to a machine with Git LFS and the real shapefiles
2. Run the current mapper against real PRIO-GRID cells, save the output as a reference
3. Run the full pipeline (`_read` → `_transform` → `_validate` → `_save`) against real data
4. Capture the output parquet and compare against what's currently in Appwrite
5. Now we have a known-good baseline to diff against

### Option 2: Build the replacement alongside, not instead of
Don't remove the mapper yet. Build the new enricher as an alternative path:
1. Write the lookup enricher that loads a Parquet file and merges
2. Write the precomputation script (to be run by someone with LFS)
3. Add a config flag: `use_lookup_table = True/False`
4. When `True`, use the enricher. When `False`, use the current mapper.
5. Someone with the full infrastructure runs BOTH paths, compares output, and verifies they're identical
6. Only then: remove the mapper and set `use_lookup_table = True` as the default

### Option 3: Add GAUL columns to the data request and skip enrichment
The simplest path that avoids touching the enrichment logic entirely:
1. Add `gaul0_code`, `gaul1_code`, `gaul2_code`, `iso3_code`, `gaul0_name`, `gaul1_name` to `config_queryset.py`'s `FACTORY_FEATURES`
2. The historical data arrives pre-enriched (centroid-based from the datafactory)
3. The postprocessor's `_append_metadata` still runs the mapper for coordinates (`pg_xcoord`, `pg_ycoord`) and for the FAO-specific area-based assignment
4. OR: accept centroid-based for historical data, keep area-based for forecasts only
5. This is a PARTIAL solution — it doesn't eliminate the mapper, but it reduces the workload (fewer GIDs need enrichment if the factory provides most columns)

### Option 4: Do nothing until we have the infrastructure
Park ADR-011 implementation. The decision (precomputed table is the right approach) is documented and correct. The code works today — it's ugly and carries 22 risk register concerns, but it works. Wait until:
- Git LFS is available in the development environment
- views-pipeline-core can be installed in the test environment
- Someone can run the full pipeline and capture reference output
- Then implement with a safety net

---

## Possible Future Solutions

### A: Precompute area-based lookup table in this repo

**What:** Run the current mapper once against all ~65K PRIO-GRID cells, save as Parquet. Replace the runtime mapper with a Parquet-merge enricher.

**Pros:**
- Self-contained — no changes to other repos
- Eliminates 3,100 lines of runtime code, geopandas dependency, 774 MB shapefiles
- Resolves ~12 of 22 risk register concerns
- The algorithm is preserved (area-majority, sequential allocation)
- The Parquet file is auditable (every assignment visible)

**Cons:**
- Requires LFS to precompute (can't do in this session)
- Need a diff test against current mapper output to verify correctness
- The precomputation must be rerun when GAUL shapefiles update (annually)
- Still need mapping.py for the precomputation script
- If we get the precomputation wrong, every cell assignment is wrong permanently

**Risk:** Medium. The algorithm is verified correct. The risk is in the plumbing (column names, index alignment, merge logic).

### B: Add area-based harvester to the datafactory

**What:** Add an area-based spatial join to `gaul_admin.py` in views-datafactory, alongside the existing centroid-based one. Store as `gaul0_code_area.parquet`, etc. The postprocessor requests these columns via `config_queryset.py`.

**Pros:**
- Single source of truth for all GAUL assignments
- Factory handles shapefile management and caching
- Postprocessor becomes a pure pipeline manager (read, validate, save) — no spatial logic
- Aligns with ADR-025's design philosophy
- Eliminates mapping.py entirely from the postprocessor

**Cons:**
- Requires changes to views-datafactory (separate repo, separate ownership)
- The area-based algorithm needs geopandas in the factory (currently avoided)
- OR: port the algorithm to pyshp + shapely (non-trivial)
- Cross-repo coordination needed
- The factory's harvester pattern assumes (gid, value) Parquet — multiple admin fields need multiple files

**Risk:** Low (algorithm verified, factory patterns well-established). Effort: Medium-High.

### C: Use centroid-based from factory, accept border cell difference

**What:** Add GAUL columns to `config_queryset.py`. The historical data arrives with centroid-based assignments. Accept that ~5% of border cells may differ from area-majority.

**Pros:**
- Zero new code in any repo
- Works today — just add columns to the config
- Eliminates mapping.py dependency for historical data
- The difference is small (~5% of cells, most with minimal overlap difference)

**Cons:**
- Violates the FAO area-majority contract (Release Note 02)
- Border cells may get different country assignments than what the API currently serves
- The FAO confirmed area-majority specifically — switching to centroid is a contract change
- Would need FAO approval to change the algorithm

**Risk:** Low technically. High contractually (FAO may reject).

### D: Hybrid — factory for historical, mapper for forecasts

**What:** Use factory GAUL columns for historical data (centroid-based, arrives pre-enriched). Keep the mapper for forecast data only (area-based, as FAO requires). 

**Pros:**
- Reduces mapper workload (only enriches forecast data, not historical)
- Historical data enrichment becomes instant (columns already in the DataFrame)
- Forecast data still gets FAO-compliant area-based assignment

**Cons:**
- Two different enrichment paths for historical vs forecast → complexity
- Historical and forecast data may have different GAUL assignments for the same border cells
- Confusing to maintain and debug

**Risk:** Medium. The inconsistency between historical and forecast enrichment is a new Cluster B-type risk.

---

## What I'd Recommend

**Option 2 (build alongside, not instead of)** is the safest path that makes progress:

1. Build the enricher module and precomputation script — this is pure additive work, changes nothing
2. Someone with LFS runs the precomputation to generate the lookup table
3. Someone with the full infrastructure runs a comparison: current mapper vs lookup enricher on real data
4. Only when the diff test passes: switch the pipeline to use the enricher
5. Only when running in production for one cycle: consider removing mapping.py

This respects your instinct: **don't change what you don't understand, and don't break what you can't verify.**

The alternative is **Option 4 (do nothing)** — which is also legitimate. The code works, the risks are documented, and ADR-011 is there for when the infrastructure supports safe implementation.
