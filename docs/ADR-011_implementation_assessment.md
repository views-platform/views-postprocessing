# ADR-011 Implementation Assessment

**Last updated:** 2026-06-12
> **This is a dated snapshot (2026-06-12), not a description of the code today.** It is
> kept as a record of what was known when ADR-011 was assessed. Several things it
> describes as current have since been removed — notably the `.env` credential borrow
> (killed by þing-01 #134; the environment is now declared and validated fail-loud in
> each partner's `appwrite_env.py`) and `self.ensemble_path_manager`, which stopped
> existing on 2026-08-05 when store construction moved off the manager class (register
> C-40). Read §8 in particular as history.

**Status:** Data prerequisites MET — see §10. Implementation unblocked on the data side; verification infrastructure (Appwrite, pipeline-core E2E) still required before switching the pipeline.

---

## 1. Current State: What We Know and Don't Know

### 1.1 What we know (verified in this session)

**The algorithm is correct.** The falsification campaign (Layer 2, Claims 2.1-2.4) verified against synthetic data:
- Interior cells get the right country with overlap_ratio = 1.0
- Border cells get the country with the largest area share
- The sequential allocation invariant holds (admin1/admin2 within the assigned country)
- The enrichment output matches the manager's 9 expected columns

**The FAO contract is area-majority.** Release Note 02 confirms in writing: "Each PRIO-GRID cell is assigned to a single country using an area-majority rule." This is locked. The sequential allocation rule is also locked: "All Admin 1 and Admin 2 assignments are constrained to the country determined at the Admin 0 stage."

**The datafactory uses a different algorithm.** The views-datafactory's `gaul_admin.py` uses centroid-based point-in-polygon (STRtree spatial index, pyshp + shapely, no geopandas). For ~95% of cells this gives the same answer as area-majority. For border cells it can disagree. The datafactory already stores its results as Parquet files (`data/raw/gaul_admin/*.parquet`, 86,091 cells covering all land cells, 7 variables: gaul0_code, gaul1_code, gaul2_code, iso3_code, gaul0_name, gaul1_name, gaul2_name).

**The postprocessor's config_queryset.py now sources from the datafactory** (migrated from VIEWSER — see Section 3 below). It requests 3 features: `ged_sb_best`, `ged_ns_best`, `ged_os_best`. It does NOT request any GAUL columns — the mapper adds geographic metadata at runtime, independently of the data source.

**The views-faoapi exists and is the Appwrite-to-FAO bridge.** An investigation report (2026-06-03) identified a separate repository, `views-faoapi`, that contains a `FAOApiManager` which downloads data from the Appwrite `unfao_bucket`, parses it, caches it, and serves it via HTTP to FAO consumers. This is the "live API endpoint hosted on a dedicated production domain" mentioned in Release Note 02. This means:
- The postprocessor uploads to Appwrite with its column names (`country_iso_a3`, `admin1_gaul1_code`, `pg_xcoord`)
- The FAOApiManager reads from Appwrite and serves to FAO with the FAO contract names (`ADM1_CODE`, `lat`, UN M49)
- The column renaming almost certainly happens in views-faoapi, not in this repo

**The forecast data stream is completely separate from the historical data stream.** The investigation report confirms:
- Historical data: views-datafactory (zarr on Hetzner) → ViewsDataLoader → postprocessor
- Forecast data: Appwrite prod_forecasts bucket → direct download → postprocessor
- Both streams get enriched by the SAME mapper — geographic metadata is added independently of the data source
- This means ANY replacement for the mapper must work for BOTH streams

**The viewser-to-datafactory migration is complete for this postprocessor.** The config_queryset.py was migrated in commit `2518335` from a VIEWSER Queryset object to a datafactory dict descriptor. The postprocessor only needs 3 raw UCDP features with no server-side transforms, making it an ideal migration candidate. Six other models have also been migrated.

### 1.2 What we DON'T know (not verified)

**We have never seen the full pipeline run.** The pipeline requires:
- `views-pipeline-core` installed (not in this environment)
- Git LFS installed (not available — shapefiles are stubs, ~774 MB)
- Appwrite credentials and endpoints configured (not available)
- Views-datafactory zarr store accessible (requires ~/.netrc for Hetzner HTTP)
- An ensemble (currently `orange_ensemble`, likely to become `golden_hour`) producing forecast data in the prod_forecasts bucket

We can read the code, trace the logic, and test with synthetic data. But we have NOT:
- Watched `_read()` download real data from the datafactory zarr store or Appwrite
- Watched `_transform()` enrich a real DataFrame with real shapefiles
- Watched `_validate()` pass or fail on real enriched data
- Watched `_save()` upload to the real Appwrite unfao_bucket
- Confirmed that the data FAO receives is actually produced by this code path

**We haven't read the views-faoapi code.** We know it exists and that it bridges Appwrite to the FAO HTTP API. We don't know:
- Whether it renames columns (resolving D-06/C-24)
- Whether it adds M49 codes or transforms ISO A3
- Whether it filters, aggregates, or restructures the data
- What schema the HTTP response actually has

**We don't know if the current output is correct for real data.** The algorithm is correct on synthetic rectangles. Real GAUL shapefiles have complex coastlines, enclaves, disputed territories, and admin boundaries that don't align with the grid. We haven't seen the mapper produce results for real GIDs.

**The orange_ensemble reference is a ghost.** `unfao.py:67` constructs `EnsemblePathManager(ensemble_name_or_path="orange_ensemble", validate=False)`. The `validate=False` suppresses the error that `orange_ensemble` doesn't exist as a directory in the repo. The ensemble name is used to locate `.env` credentials for Appwrite and as metadata on uploaded files. If credential resolution changes, the forecast download breaks silently. Tracked in views-models GitHub issue #77, expected to be replaced with `golden_hour` or a new ensemble.

**The nokgi semantic difference.** The viewser-era data used `ged_sb_best_sum_nokgi` — the `nokgi` suffix means "no known geographic imprecision," a server-side filter that excludes UCDP events with imprecise geolocation. The datafactory uses `ged_sb_best` — raw best estimates including ALL events regardless of geolocation precision. The practical difference is documented as ~0.05% in the datafactory's parity tests, but the semantic difference is real: the FAO is now receiving slightly different underlying data than before the migration, and this change was not explicitly communicated or approved.

---

## 2. The Complete Data Flow

### 2.1 Historical data path

```
Views-Datafactory (zarr on Hetzner, http://204.168.219.108/grid.zarr)
    │
    │  config_queryset.py specifies:
    │    source: "views-datafactory"
    │    features: ged_sb_best → lr_ged_sb, ged_ns_best → lr_ged_ns, ged_os_best → lr_ged_os
    │    region: "africa_me_legacy" (13,110 cells)
    │
    ▼
ViewsDataLoader._fetch_data_from_datafactory()  (views-pipeline-core)
    │  calls load_dataset(region, start, end, features, output_format="dataframe", data_dir=zarr_url)
    │  renames columns via FEATURE_RENAME dict
    │  derives row/col from priogrid_gid
    │  fillna(0.0), sort_index, ensure_float64
    │  caches as data/raw/forecasting_datafactory_df.parquet
    │
    ▼
UNFAOPostProcessorManager._read_historical_data()
    │  self._initialize_data_loader()
    │  self._data_loader.get_data(partition="forecasting")
    │  reads cached parquet → self._historical_dataframe
    │  wraps in PGMDataset
    │
    │  DataFrame at this point has:
    │    Index: (month_id, priogrid_gid)
    │    Columns: lr_ged_sb, lr_ged_ns, lr_ged_os, row, col
    │    NO geographic metadata yet
    │
    ▼
UNFAOPostProcessorManager._transform()
    │  calls _append_metadata(self._historical_dataset)
    │    │
    │    ▼
    │  PriogridCountryMapper.enrich_dataframe_with_pg_info()
    │    │  loads 4 shapefiles (Natural Earth 10m, PRIO-GRID, GAUL L1, GAUL L2)
    │    │  for each unique GID: compute area-majority country, admin1, admin2
    │    │  returns DataFrame with ~24 columns (9 needed + 15 extras)
    │    │
    │    ▼
    │  _append_metadata selects 9 columns via filter_cols:
    │    pg_xcoord, pg_ycoord, country_iso_a3,
    │    admin1_gaul1_code, admin1_gaul1_name, admin1_gaul0_code, admin1_gaul0_name,
    │    admin2_gaul2_code, admin2_gaul2_name
    │  re-indexes and joins back onto the dataset
    │
    ▼
UNFAOPostProcessorManager._validate()
    │  checks all 9 metadata columns: present AND non-null
    │  log-before-raise on failure
    │
    ▼
UNFAOPostProcessorManager._save()
    │  creates AppwriteConfig for unfao_bucket from os.getenv()
    │  saves timestamped parquet locally
    │  uploads to Appwrite unfao_bucket with metadata:
    │    name, loa="pgm", type="model", targets, category="historical"
    │    description="Enriched with geographic metadata on {timestamp}..."
    │
    ▼
Appwrite (unfao_bucket)
    │
    ▼
FAOApiManager (views-faoapi)
    │  downloads from unfao_bucket
    │  parses, caches, transforms (column renaming likely happens HERE)
    │  serves via HTTP to FAO consumers
    │
    ▼
UN FAO (end consumer)
```

### 2.2 Forecast data path

```
Ensemble model (currently "orange_ensemble", to become "golden_hour")
    │  produces predictions: pred_ln_sb_best, pred_ln_ns_best, pred_ln_os_best,
    │                        pred_ln_sb_prob, pred_ln_ns_prob, pred_ln_os_prob
    │  uploads to Appwrite prod_forecasts bucket
    │
    ▼
UNFAOPostProcessorManager._read_forecast_data()
    │  loads .env from ensemble path (load_dotenv — mutates os.environ)
    │  creates AppwriteConfig for prod_forecasts bucket
    │  downloads latest file with category="forecast"
    │  parses parquet bytes: pd.read_parquet(io.BytesIO(file_bytes))
    │  wraps in PGMDataset
    │
    │  DataFrame at this point has:
    │    Index: (month_id, priogrid_gid)
    │    Columns: pred_ln_sb_best, pred_ln_ns_best, pred_ln_os_best,
    │             pred_ln_sb_prob, pred_ln_ns_prob, pred_ln_os_prob
    │    NO geographic metadata yet
    │
    ▼
Same enrichment path as historical:
    _transform() → _append_metadata() → mapper → 9 columns added
    _validate() → null check
    _save() → upload to Appwrite unfao_bucket with category="forecast"
    │
    ▼
Same downstream path: Appwrite → FAOApiManager → FAO
```

### 2.3 Key observations about the data flow

1. **Geographic metadata is added at runtime by the mapper, independently of both data sources.** Neither the datafactory nor Appwrite provides GAUL columns to the postprocessor. The mapper loads its own shapefiles and computes assignments from scratch for every pipeline run.

2. **The forecast stream is completely independent of the viewser/datafactory question.** Forecast data comes from Appwrite, not from the datafactory. Even if we add GAUL columns to the historical data request (Option C), the forecast data still needs enrichment from the mapper or its replacement.

3. **The postprocessor uploads TWO files per run** — one historical (category="historical") and one forecast (category="forecast") — both to the same unfao_bucket. The FAOApiManager presumably reads both.

4. **The column renaming for the FAO contract likely happens in views-faoapi**, not in this repo. The postprocessor outputs `country_iso_a3`, `admin1_gaul1_code`, `pg_xcoord`. The FAO contract specifies `ADM1_CODE`, `lat`, UN M49. The views-faoapi is the only code between Appwrite and the FAO HTTP consumer.

---

## 3. The Viewser-to-Datafactory Migration

### 3.1 What happened

The UN FAO postprocessor was migrated from viewser to views-datafactory. The git history of `views-models/postprocessors/un_fao/configs/config_queryset.py` shows three stages:

1. **Initial (commit 1351460):** VIEWSER Queryset, 1 column (`ged_sb_best_count_nokgi`)
2. **Expanded (commit 2871b1e):** VIEWSER Queryset, 3 columns (`ged_sb_best_sum_nokgi`, `ged_ns_best_sum_nokgi`, `ged_os_best_sum_nokgi`), only `replace_na()` transforms
3. **Migrated (commit 2518335):** Datafactory dict descriptor, 3 columns (`ged_sb_best`, `ged_ns_best`, `ged_os_best`)

The migration was straightforward because the postprocessor only needs 3 raw UCDP features with no server-side transforms (no ln, lag, spatial.lag, decay). The only transform it used was `replace_na()`, which the datafactory loader replaces with `fillna(0.0)`.

### 3.2 The dispatch mechanism

The `ViewsDataLoader` in views-pipeline-core routes data fetching based on what `config_queryset.generate()` returns:
- If it returns a dict with `"source": "views-datafactory"` → `_fetch_data_from_datafactory()` → calls `load_dataset()` from datafactory_query
- If it returns an object with `.publish()` → `_fetch_data_from_viewser()` → calls viewser API

No flag, no env var, no central registry. The config file's return type IS the configuration. Switching a model from viewser to datafactory is a single-file change. Cache files encode the source to prevent cross-contamination: `forecasting_viewser_df.parquet` vs `forecasting_datafactory_df.parquet`.

### 3.3 The nokgi semantic difference

This is the most subtle consequence of the migration. Viewser's columns were `ged_sb_best_sum_nokgi` — the `nokgi` suffix means "no known geographic imprecision." This is a server-side filter in viewser/ingester3 that excludes UCDP events whose geolocation is imprecise (events that can't be confidently assigned to a specific PRIO-GRID cell).

The datafactory's columns are `ged_sb_best` — raw best estimates from consolidated UCDP data, including ALL events regardless of geolocation precision. The practical magnitude is ~0.05% (documented in `views-datafactory/tests/test_consumer_parity.py`).

**Impact for this repo:** The FAO is now receiving data that includes geolocation-imprecise events that were previously filtered out. The difference is small but the semantic change is real, and it was not explicitly communicated to or approved by FAO. This is not tracked in our risk register. The closest entries in the views-pipeline-core register are C-52 (drift detection silently lost) and D-10 (descriptor simplicity vs correctness features embedded in viewser).

### 3.4 What the datafactory already provides

The assembled zarr store contains 68 features. The GAUL admin features available in the zarr:
- `gaul0_code` — GAUL country code (int, centroid-based assignment, -1 for ocean)
- `gaul1_code` — GAUL admin level 1 code (int)
- `gaul2_code` — GAUL admin level 2 code (int)

The raw GAUL Parquet files at `data/raw/gaul_admin/` additionally contain:
- `iso3_code` — ISO Alpha-3 country code (string)
- `gaul0_name` — Country name (string)
- `gaul1_name` — Admin level 1 name (string)
- `gaul2_name` — Admin level 2 name (string)

Coverage: 86,091 cells (all land cells globally). The Africa+ME legacy region has 13,110 pgids, of which 12,507 have GAUL codes (603 unmapped — coastal/boundary edge cases, assigned gaul0_code = -1).

**Critical:** These are ALL centroid-based, not area-based. The postprocessor's mapper uses area-based. For border cells (~5%), the assignments can differ.

---

## 4. The Core Risk

**If we change the enrichment logic and break the output, we won't know until the FAO reports a problem.** There is no:
- Staging environment to test against
- Diff test comparing old vs new output (requires LFS for real shapefiles)
- Integration test running the real pipeline end-to-end (requires views-pipeline-core + Appwrite + datafactory access)
- Acceptance test with known-good reference output to compare against
- Visibility into what views-faoapi does to the data before serving it to FAO

The 88 tests we wrote verify the algorithm against synthetic data. They verify the boundary contract (mapper output matches manager's filter_cols). They verify regression protection for our fixes. But they do NOT verify that the complete pipeline produces correct output for real data through the full chain (datafactory → postprocessor → Appwrite → views-faoapi → FAO).

**We are confident the algorithm is right. We are not confident we can change the plumbing without breaking something we can't see.**

**Additionally:** The forecast data path depends on `orange_ensemble` which doesn't exist in the views-models repo (masked by `validate=False`). Any change to credential resolution could silently break forecast downloads. This is tracked in views-models issue #77.

---

## 5. What Would Need to Be True Before We Can Safely Change This

### Option 1: See it run first
Before touching the enrichment logic:
1. Get access to a machine with Git LFS and the real shapefiles
2. Run the current mapper against real PRIO-GRID cells, save the output as a reference
3. Run the full pipeline (`_read` → `_transform` → `_validate` → `_save`) against real data
4. Capture the output parquet and compare against what's currently in the Appwrite unfao_bucket
5. ~~Read the views-faoapi code to understand the Appwrite→API column transformation~~ ✅ **DONE (2026-06-03):** No renaming exists. Postprocessor columns pass through to FAO unmodified. See Section 7.
6. Now we have a known-good baseline to diff against

### Option 2: Build the replacement alongside, not instead of
Don't remove the mapper yet. Build the new enricher as an alternative path:
1. Write the lookup enricher that loads a Parquet file and merges
2. Write the precomputation script (to be run by someone with LFS)
3. Add a config flag: `use_lookup_table = True/False`
4. When `True`, use the enricher. When `False`, use the current mapper
5. Someone with the full infrastructure runs BOTH paths, compares output, and verifies they're identical for both historical AND forecast data
6. Only then: switch the default to `True`
7. Only after running in production for one cycle: consider removing mapping.py

### Option 3: Add GAUL columns to the data request (historical only, partial solution)
Add GAUL columns to `config_queryset.py`'s feature list so historical data arrives pre-enriched:
1. Add `gaul0_code`, `gaul1_code`, `gaul2_code`, `iso3_code`, `gaul0_name`, `gaul1_name` to `FACTORY_FEATURES`
2. The historical DataFrame arrives with centroid-based GAUL columns from the factory
3. **BUT:** The forecast DataFrame still arrives from Appwrite without ANY GAUL columns — the mapper (or its replacement) is still needed for forecast enrichment
4. **AND:** The centroid-based assignments differ from area-based for border cells, violating the FAO contract
5. This is a PARTIAL solution at best — it does not eliminate the mapper

### Option 4: Do nothing until we have the infrastructure
Park ADR-011 implementation. The decision (precomputed table is the right approach) is documented and correct. The code works today — it's ugly and carries 22 risk register concerns, but it works. Wait until:
- Git LFS is available in the development environment
- views-pipeline-core can be installed in the test environment
- Someone can run the full pipeline and capture reference output
- ~~views-faoapi has been reviewed (resolving D-06)~~ ✅ **DONE (2026-06-03)**
- The orange_ensemble reference is resolved (views-models #77)
- Then implement with a safety net

---

## 6. Possible Future Solutions

### A: Precompute area-based lookup table in this repo

**What:** Run the current mapper once against all ~65K PRIO-GRID cells, save as Parquet. Replace the runtime mapper with a Parquet-merge enricher. The enricher works for BOTH historical and forecast data (merge by GID regardless of data source).

**Pros:**
- Self-contained — no changes to other repos
- Eliminates 3,100 lines of runtime code, geopandas dependency, 774 MB shapefile bundle
- Resolves ~12 of 22 risk register concerns
- The algorithm is preserved (area-majority, sequential allocation)
- The Parquet file is auditable (every assignment visible)
- Works for both data streams (historical from factory, forecast from Appwrite)

**Cons:**
- Requires LFS to precompute (can't do in this session)
- Need a diff test against current mapper output to verify correctness
- The precomputation must be rerun when GAUL shapefiles update (FAO releases annually, partial updates)
- Still need mapping.py for the precomputation script
- If we get the precomputation wrong, every cell assignment is wrong permanently (and cached in the lookup table)

**Risk:** Medium. The algorithm is verified correct on synthetic data. The risk is in the plumbing (column names, index alignment, merge logic) and the impossibility of verifying against real data in this environment.

### B: Add area-based harvester to the datafactory

**What:** Add an area-based spatial join to `gaul_admin.py` in views-datafactory, alongside the existing centroid-based one. Store as additional Parquet files (`gaul0_code_area.parquet`, etc.). The postprocessor requests these columns via `config_queryset.py`.

**Pros:**
- Single source of truth for all GAUL assignments (centroid AND area-based)
- Factory handles shapefile management, caching, and provenance tracking
- Postprocessor becomes a pure pipeline manager (read, validate, save) — no spatial logic
- Aligns with the datafactory's ADR-025 design philosophy (identity is a static property)
- Eliminates mapping.py entirely from the postprocessor

**Cons:**
- Requires changes to views-datafactory (separate repo, separate ownership)
- The area-based algorithm needs geopandas in the factory (currently avoided — the factory uses pyshp + shapely only)
- OR: port the area-based algorithm to pyshp + shapely (non-trivial — the overlap calculation relies on geopandas GeoDataFrame operations)
- Cross-repo coordination needed
- The factory's harvester pattern stores one Parquet per variable (gid, value) — mapping 9 output columns requires 9 files
- **Does NOT solve the forecast stream** — forecast data from Appwrite still has no GAUL columns, so the postprocessor still needs SOME enrichment mechanism even if historical data comes pre-enriched
- UNLESS: the forecast data is also pre-enriched before upload to Appwrite (requires changes to the ensemble pipeline)

**Risk:** Low (algorithm verified, factory patterns well-established). Effort: High (cross-repo, potential dependency change, forecast stream unsolved).

### C: Use centroid-based from factory, accept border cell difference

**What:** Add GAUL columns to `config_queryset.py`. The historical data arrives with centroid-based assignments from the factory.

**Pros:**
- Zero new code in any repo (just config change)
- Works today — just add columns to the feature list
- Eliminates mapping.py dependency for historical data
- The difference is small (~5% of cells, most with minimal overlap difference)

**Cons:**
- Violates the FAO area-majority contract (Release Note 02)
- Border cells get centroid-based assignments, not area-majority
- The FAO confirmed area-majority specifically after reviewing both options — switching to centroid is a contract change requiring re-approval
- **Does NOT solve the forecast stream** — forecast data still needs enrichment
- The mapper is still needed for forecast data, so the dependency isn't eliminated

**Risk:** Low technically. High contractually (FAO explicitly chose area-majority over centroid).

### D: Hybrid — factory for historical, mapper for forecasts

**What:** Use factory GAUL columns for historical data (centroid-based, arrives pre-enriched). Keep the mapper for forecast data only (area-based, as FAO requires).

**Pros:**
- Reduces mapper workload (only enriches forecast data, ~36 months, not historical ~500+ months)
- Historical data enrichment becomes instant (columns already in the DataFrame)
- Forecast data still gets FAO-compliant area-based assignment

**Cons:**
- Two different enrichment paths → complexity and confusion
- Historical and forecast data have DIFFERENT GAUL assignments for the same border cells (centroid vs area-based) — the same GID can show one country in historical data and a different country in forecast data
- This inconsistency would be visible to FAO and is arguably worse than either algorithm alone
- Confusing to maintain, debug, and explain to partners

**Risk:** High. The inconsistency between historical and forecast enrichment is a new problem that doesn't exist today. The current system at least uses the same algorithm for both streams.

---

## 7. The D-06 / C-24 Schema Question — RESOLVED

### 7.1 D-06 Answer: views-faoapi does NOT rename columns

**We have now read the views-faoapi code.** The answer to D-06 is definitive:

**views-faoapi passes the postprocessor's column names through to the FAO consumer WITHOUT any renaming, mapping, or transformation.**

Evidence from `/home/simon/Documents/scripts/views_platform/views-faoapi/`:

1. **`handlers.py:1146-1156`** — The `FAO_PGMDataset` class defines `_METADATA_COLS` with the EXACT column names from the postprocessor: `pg_xcoord`, `pg_ycoord`, `country_iso_a3`, `admin1_gaul1_code`, etc. These are validated on load — if the postprocessor's column names change, views-faoapi throws a ValueError.

2. **`api.py:182-191`** — The `dataframe_to_dict()` function converts the DataFrame to JSON records via `df.to_dict(orient="records")`. No renaming occurs. The column names in the HTTP response are whatever the DataFrame has.

3. **`api.py:700-702`** — The `/data/historical/latest` endpoint returns:
   ```python
   {
       "success": True,
       "data": {
           "dataframe": dataframe_to_dict(df),  # raw records, no renaming
           "columns": df.columns.tolist(),       # raw column names
           "category": "historical"
       }
   }
   ```
   The same pattern at lines 731-733 (forecast) and 786-788 (subset). Every endpoint passes columns through unmodified.

4. **No `.rename()` on data columns exists anywhere in the codebase.** We searched for rename, mapping, M49, ADM1_CODE, lat/lon — nothing.

### 7.2 The gap between the feedback document and the implementation

The repo contains a feedback document from October 2025 (`notebooks/27102025_01_review.md`) that was sent to FAO requesting feedback on the API schema. This document shows an EXAMPLE payload with `lat`, `lon`, `isoab`, `name` — but these column names were **aspirational proposals, not the implemented schema.**

The October 2025 feedback document asked FAO to confirm column names. The responses were formalized in Release Note 01 (Topic C), which locked: UN M49, `ADM1_CODE`/`ADM2_CODE`, `lat`/`lon`. But the code was implemented using the postprocessor's internal column names (`country_iso_a3`, `admin1_gaul1_code`, `pg_xcoord`) and the renaming to FAO contract names **was never implemented.**

Timeline:
1. **October 2025:** Feedback document sent to FAO with proposed schema (`lat`, `lon`, `isoab`)
2. **Release Note 01 (confirmed):** FAO signs off on UN M49, `ADM1_CODE`, `lat`/`lon`
3. **Release Note 02 (confirmed):** FAO confirms area-majority allocation rule
4. **Implementation:** views-faoapi built using postprocessor's column names, not the confirmed FAO contract names
5. **Current state:** FAO receives `country_iso_a3`, `pg_xcoord`, `admin1_gaul1_code` — NOT what the contract specifies

### 7.3 What this means

**The FAO is currently receiving data with column names that do not match the locked contract from Release Note 01.** Specifically:

| What FAO contract says | What FAO actually receives | Gap |
|---|---|---|
| UN M49 country code | `country_iso_a3` (ISO Alpha-3, e.g., "KEN") | Different coding system entirely |
| `ADM1_CODE` | `admin1_gaul1_code` | Different column name |
| `ADM1_NAME` | `admin1_gaul1_name` | Different column name |
| `ADM2_CODE` | `admin2_gaul2_code` | Different column name |
| `ADM2_NAME` | `admin2_gaul2_name` | Different column name |
| `lat` | `pg_ycoord` | Different column name |
| `lon` | `pg_xcoord` | Different column name |

This is either:
- **Accepted by FAO** — they adapted their systems to the actual column names regardless of what the contract says (possible, since the API has been running)
- **Not noticed by FAO** — they haven't done detailed schema validation against the contract (possible for early/prototype stages)
- **Tracked separately** — there may be a backlog item to add the renaming layer that simply hasn't been prioritized

### 7.4 Impact on this repo and ADR-011

**The postprocessor's column names ARE what reaches FAO.** There is no intermediate transformation. This means:

1. **C-24 (schema divergence) is a REAL gap, not an artifact of missing knowledge.** The postprocessor's column names don't match the FAO contract, and nothing downstream fixes it.

2. **D-06 is resolved: Possibility B was correct.** "No renaming layer exists — the postprocessor's Parquet files are served directly to FAO." The postprocessor's output schema IS the FAO-facing schema.

3. **For ADR-011:** The precomputed lookup table's column names matter directly. Whatever names the table uses will reach FAO. The current names (`country_iso_a3`, `admin1_gaul1_code`, etc.) are what FAO has been receiving and presumably adapted to.

4. **The safest choice for ADR-011 is to preserve the current column names.** Changing them now would break whatever FAO has built against the current schema. If column renaming is desired (to match the Release Note 01 contract), it should be done in views-faoapi as a separate, coordinated change — NOT in the postprocessor during an enrichment refactor.

5. **The column renaming is NOT this repo's responsibility.** It belongs in views-faoapi (the API layer) or as a coordinated cross-repo change. This repo should produce the same columns it always has.

---

## 8. Open Issues Affecting This Repo (From the Investigation Report)

### 8.1 The orange_ensemble ghost (views-models #77)

`unfao.py:67` references `orange_ensemble` with `validate=False`. The ensemble doesn't exist in the repo. The name is used for:
- Locating `.env` credentials for Appwrite (via `self.ensemble_path_manager.dotenv`)
- Setting metadata on uploaded forecast files (`name=self.ensemble_path_manager.model_name`)

If credential resolution changes (e.g., the `.env` file moves, or the ensemble name changes to `golden_hour`), the forecast download path breaks silently. This is NOT in our risk register — it's tracked in views-models #77 but affects this repo's code.

### 8.2 The nokgi semantic difference

The migration from viewser to datafactory changed the underlying data from `ged_sb_best_sum_nokgi` (filtered for geolocation precision) to `ged_sb_best` (all events). The ~0.05% difference in values was not explicitly communicated to or approved by FAO. This is a subtle but real semantic change that should be documented in the risk register.

### 8.3 Cross-repo risk register entries

The views-pipeline-core risk register contains entries relevant to this repo:
- **C-52:** Drift detection silently lost for datafactory sources (viewser had `fetch_with_drift_detection()`, datafactory returns `None` for alerts)
- **C-59:** Cache filename convention hardcoded across 5 locations in 3 repos
- **C-60:** Phase 1 workaround saves datafactory data as `_viewser_df.parquet`
- **C-61:** No cache provenance verification with `use_saved=True`
- **D-10:** Disagreement on descriptor simplicity vs correctness features embedded in viewser

These are not duplicated in our register (they're about views-pipeline-core, not this repo), but they affect the data that reaches our postprocessor.

---

## 9. Recommendation

**Option 2 (build alongside, not instead of)** is the safest path that makes progress:

1. **D-06 is now resolved** — views-faoapi does NOT rename columns. The postprocessor's column names reach FAO directly. Keep the current names in any replacement.
2. **Build the enricher module and precomputation script** — pure additive work, changes nothing in the running pipeline.
3. **Someone with LFS runs the precomputation** to generate the lookup table from real shapefiles.
4. **Someone with the full infrastructure runs a comparison** — current mapper vs lookup enricher on real data, for BOTH historical and forecast streams.
5. **Only when the diff test passes:** switch the pipeline to use the enricher.
6. **Only after running in production for one cycle:** consider removing mapping.py.

The alternative is **Option 4 (do nothing)** — which is also legitimate. The code works, the risks are documented, and ADR-011 is there for when the infrastructure supports safe implementation.

**What NOT to do:**
- Don't change the enrichment logic without being able to verify the output against real data
- Don't change column names in the postprocessor — FAO has presumably adapted to the current names, and renaming belongs in views-faoapi if it happens at all
- Don't eliminate the mapper for historical data without solving the forecast data stream too (forecasts come from Appwrite, not the datafactory, and always need enrichment)

**Remaining unblocked actions:**
1. The column naming question is settled — keep current names
2. The architecture decision (precomputed table) is confirmed — area-majority, sequential allocation, Parquet lookup
3. What blocks progress is infrastructure: LFS for precomputation, views-pipeline-core for E2E testing, Appwrite for verification

---

## 10. June 2026 Status Update — Datafactory Prerequisites MET

**Added:** 2026-06-12. Full detail in `docs/cross_repo_integration_report.md`.

### 10.1 What changed upstream

The views-datafactory completed the area-majority work (issue #115 → PR #127, ADR-039 accepted, shipped v1.2.28/29):

| Artifact | State (verified 2026-06-12) |
|---|---|
| `gaul0/1/2_code.parquet` | 259,200 rows each, int32, **area-majority** (regenerated Jun 11) |
| `gaul0/1/2_name.parquet` | 259,200 rows each, string, **area-majority** (regenerated Jun 11 — the earlier 86,091-row centroid gap is closed) |
| `iso3_code.parquet` | 259,200 rows, string, **area-majority** (Jun 11) |
| Assembled grid/zarr | gaul codes at channels 72-74, area-majority, fill = -1 (assembled Jun 8) |

Consistency for africa_me_legacy (13,110 cells): 13,105 fully consistent (code + name + iso3); 5 pure-ocean cells unassigned (gids 62356, 94776, 99027, 107733, 107742).

### 10.2 What this resolves

- **The "regeneration requires LFS + 774 MB shapefiles" blocker is gone.** The lookup table no longer needs this repo's mapper or shapefiles to be built — it is a join of the 7 factory parquets plus a coordinate formula (`xcoord = -180 + ((gid-1) % 720) * 0.5 + 0.25`, `ycoord = -90 + ((gid-1) // 720) * 0.5 + 0.25`).
- **The area-majority requirement is satisfied at the source.** The factory's single L2-based join yields all three admin levels from the same winning polygon; empirically 0 cells diverge from a direct L0 computation (sequential-allocation invariant preserved).
- **D-05 (platform mapping divergence) is resolved upstream** — the datafactory now ships area-majority, the same algorithm family FAO's contract requires.

### 10.3 Revised implementation path (supersedes §6 options)

Build the lookup FROM the datafactory parquets (Option 1 in the integration report):

1. Offline script joins the 7 parquets by gid, computes pg_xcoord/pg_ycoord, renames to the 9 contract columns (`gaul0_code → admin1_gaul0_code`, `iso3_code → country_iso_a3`, …).
2. Commit the resulting parquet (~1-2 MB africa_me / ~15 MB global) to this repo.
3. New enricher = merge-by-gid; replaces `mapper.enrich_dataframe_with_pg_info()` in `_append_metadata()`.
4. Serves BOTH historical and forecast paths (decisive — forecast data bypasses the factory entirely).
5. **Fail-loud preservation:** unassigned gids (factory code = -1) must surface as nulls so `_validate()` still crashes the pipeline rather than shipping wrong attributions. Do not pass -1/"" through as values.
6. **Acceptance criterion:** output schema (column names, dtypes, index) identical to current mapper output. faoapi then requires zero changes.

### 10.4 What still blocks the switch (unchanged)

- Verification infrastructure: Appwrite access + views-pipeline-core for an E2E run and an old-vs-new diff on real data.
- FAO communication: attribution values change for ~711 border cells (5.4%) and 149 recovered coastal cells — contractually correct (area-majority per Release Note 02) but a visible data-version change.
- Open: deployed-zarr sync status at the remote server; whether the 5 ocean cells ever appear in prediction inputs.

### 10.5 Semantic change to flag

`country_iso_a3` switches source from Natural Earth to GAUL. Current pipeline mixes boundary datasets (NE country + GAUL admin); the lookup makes each row internally consistent from a single GAUL polygon. This is an improvement but technically a change in what the ISO column means at disputed borders.
