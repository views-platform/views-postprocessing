# Cross-Repo Integration Report: datafactory ↔ postprocessing ↔ Appwrite ↔ faoapi

**Date:** 2026-06-12
**Status:** Investigation complete
**Scope:** Four systems — views-datafactory, views-postprocessing, the Appwrite prediction store, views-faoapi — plus the connective tissue in views-pipeline-core and views-models.
**Method:** Three parallel code sweeps (one per system pair) plus direct verification of data artifacts (parquet schemas, row counts, provenance digests, ledger timestamps). Every factual claim carries a `file:line` citation or a re-runnable command output.

---

## 1. Executive summary

1. **The chain today**: predictions flow through two parallel paths (historical via the datafactory zarr, forecast via the Appwrite `prod_forecasts` bucket) that converge in the postprocessor, where a 3,171-line runtime spatial mapper attaches 9 geographic metadata columns. The enriched output goes to the Appwrite `unfao_bucket`, from which views-faoapi serves it over HTTP to FAO — **without renaming a single column**. The postprocessor's column names ARE the FAO-facing schema.
2. **The datafactory's area-majority work (issue #115) removes the last data prerequisite for ADR-011.** As of June 11, all 7 GAUL parquets (3 codes + 3 names + iso3) are area-majority, 259,200 rows each, mutually consistent. A precomputed lookup table can now be built from them.
3. **views-faoapi requires ZERO changes** if the lookup table reproduces the 9 columns exactly. The schema contract is enforced at three independent points (triple-locked); reproducing it byte-for-byte makes the entire mapper replacement invisible downstream.
4. **The forecast path is the decisive architectural constraint**: forecast data never touches the datafactory, so no "request GAUL columns from the factory" design can work. Only a GID-keyed lookup table serves both paths.
5. **Open questions**: whether the deployed zarr at the remote server has been re-exported since June 8 (deployment fact, not verifiable locally); whether the 5 unassignable ocean cells ever appear in prediction inputs; when/how to notify FAO of the ~5.4% border-cell attribution changes.

---

## 2. How the four systems work together NOW

### 2.1 The full chain

```
PATH 1 — HISTORICAL
═══════════════════
views-datafactory assembled grid  (grid.zarr served at http://204.168.219.108/grid.zarr)
  │   75 features incl. gaul0_code/gaul1_code/gaul2_code (channels 72-74)
  │
  ├─ views-models postprocessors/un_fao/configs/config_queryset.py:31-40
  │    descriptor: {source: "views-datafactory", region: "africa_me_legacy",
  │                 loa: "priogrid_month", features: {ged_*_best → lr_ged_*}}
  │
  ├─ views-pipeline-core dataloaders.py:1117-1224  _fetch_data_from_datafactory()
  │    → datafactory_query.load_dataset(region, start, end, features, "dataframe", zarr_url)
  │    → rename per FEATURE_RENAME (1197-99), add row/col (1201-06),
  │      fillna(0.0) (1208), ensure_float64 (1210)
  │
  └─ postprocessor unfao.py:44-59  _read_historical_data()
       DataFrame: MultiIndex (month_id, priogrid_gid), cols lr_ged_sb/ns/os

PATH 2 — FORECAST
═════════════════
views-models ensemble run (--prediction_store)
  │   pipeline-core model.py:196-203 initializes DatastoreModule
  │   prediction/io.py:111-144 / savers.py:120-154 upload
  │
  ├─ DatastoreModule.upload_data (datastore.py:275-372)
  │    metadata: {loa: "pgm", category: "forecast", targets: [...], file_hash, ...}
  │    → Appwrite prod_forecasts bucket + metadata doc in file_metadata DB
  │
  └─ postprocessor unfao.py:61-134  _read_forecast_data()
       download_latest_file(filters={category: "forecast"})   (unfao.py:126)
       "latest" = newest $createdAt (datastore.py:475-511, sort at 420-424)
       ⚠ no loa / name / run-id filter — risk C-25

CONVERGENCE — ENRICHMENT
════════════════════════
unfao.py:140-163  _append_metadata(dataset)
  → mapper.enrich_dataframe_with_pg_info(...)   (mapping.py:2489-2705)
     runtime spatial join: PRIO-GRID cell → Natural Earth country (area-majority)
                            → GAUL L1 within country → GAUL L2 within country
     loads 774 MB LFS shapefiles at import (mapping.py:3171 set_default_mapper)
  → selects the 9 metadata columns (filter_cols, unfao.py:141-153)

unfao.py:188-221  _validate()
  → hard gate: all 9 columns present AND zero nulls, both dataframes,
    else ValueError (pipeline crashes — fail-loud)

unfao.py:223-273  _save()
  → parquet → DatastoreModule.upload_data → Appwrite unfao_bucket
    historical: category="historical" (unfao.py:258-263)
    forecast:   category="forecast",  targets=[pred_ln_*_best, pred_ln_*_prob] (268-273)

DELIVERY — views-faoapi
═══════════════════════
FAOApiManager._get_latest_dataframe (api.py:422-612)
  3-tier cache (memory 4h TTL → disk pickle → remote)
  → download_latest_file(filters={category})   (api.py:488)
  → FAO_PGMDataset(df)   (handlers.py:1143-1227)
       validates EXACT 9 metadata column names (1146-1163)
       validates MultiIndex (month_id, priogrid_id) (1180-1195)
       detects predictions by pred_* prefix (357-366, 1173-78)
  → HTTP endpoints: /data/{cat}/latest, /{pg|country|gaul0|gaul1|gaul2}/data/{cat}/subset,
    /{level}/analysis/{cat}/hdi-map   (api.py:637-923)
  → NO column renaming anywhere; flatten single-element arrays only (api.py:120-180)
  → FAO receives the postprocessor's column names verbatim
```

### 2.2 The schema contract (triple-locked)

The same 9 column names are independently hard-coded at three enforcement points:

| Enforcement point | Location | Failure mode if violated |
|---|---|---|
| Postprocessor selection | `unfao.py:141-153` (filter_cols) | KeyError at `_append_metadata` |
| Postprocessor validation | `unfao.py:189-197` (_necessary_metadata_cols) | ValueError, pipeline crash |
| faoapi dataset validation | `views-faoapi handlers.py:1146-1163` (_METADATA_COLS) | HTTP 500 on first request |

The 9 columns:

```
pg_xcoord, pg_ycoord,
country_iso_a3,
admin1_gaul1_code, admin1_gaul1_name,
admin1_gaul0_code, admin1_gaul0_name,
admin2_gaul2_code, admin2_gaul2_name
```

Additionally locked in faoapi:

- **Aggregation level map** (`handlers.py:1206-09`): `country→country_iso_a3`, `gaul0→admin1_gaul0_code`, `gaul1→admin1_gaul1_code`, `gaul2→admin2_gaul2_code`. Renaming any of these breaks the `/country/...`, `/gaul0/...` etc. endpoints.
- **Prediction prefix** (`handlers.py:357-366`): columns must start with `pred_` to be recognized as targets.
- **Index contract** (`handlers.py:1180-1195`): 2-level MultiIndex named `(month_id, priogrid_id)`; `priogrid_gid` is auto-renamed to `priogrid_id` (handlers.py:92-98) — the only rename in the whole chain.

**Consequence:** any schema change (e.g., the D-06 question of adopting FAO contract names like `ADM1_CODE`/M49) requires a coordinated change in views-postprocessing AND views-faoapi, plus FAO notification. The lookup-table migration must NOT bundle renames.

### 2.3 What the datafactory holds today (verified 2026-06-12)

| Artifact | State | Verified |
|---|---|---|
| `data/raw/gaul_admin/gaul0_code.parquet` | 259,200 rows, int32, area-majority | regenerated Jun 11 00:20 |
| `gaul1_code.parquet`, `gaul2_code.parquet` | same | Jun 11 00:20 |
| `gaul0_name.parquet`, `gaul1_name.parquet`, `gaul2_name.parquet` | 259,200 rows, string, area-majority | Jun 11 00:20 |
| `iso3_code.parquet` | 259,200 rows, string, area-majority | Jun 11 00:20 |
| Assembled `grid.npy` / `grid.zarr` | 75 features; gaul codes at channels 72-74, area-majority (assembled Jun 8 from Jun 5 code files), fill = -1 | provenance.json, assemble_grid.py:548-583 |
| `africa_me_legacy_pgids.json` | 13,110 cells | bundled with datafactory_query (regions.py:141-152) |

**Consistency check (africa_me_legacy, 13,110 cells):**
- 13,105 cells fully consistent: valid code + non-empty name + non-empty iso3.
- 5 cells unassigned (pure ocean): gids 62356 (-46.75, 37.75), 94776 (-24.25, 47.75), 99027 (-21.25, 13.25), 107733 (-15.25, 46.25), 107742 (-15.25, 50.75). These carry `code = -1`, `name = ""`.
- Zero cells with a code but missing name (the 598-cell gap that existed before June 11 is closed).

**What CANNOT ride the zarr:** names and iso3_code are strings; the grid is float32. Assembly explicitly skips non-numeric admin fields (`assemble_grid.py:558`). The string parquets exist only as raw files outside the assembly pipeline.

### 2.4 The Appwrite prediction store

Two buckets, one shared metadata database (`file_metadata`):

| Bucket | Writers | Readers | Categories |
|---|---|---|---|
| `prod_forecasts` | views-models ensembles (via pipeline-core `upload_data`, datastore.py:275-372) | postprocessor `_read_forecast_data` (unfao.py:126) | `forecast` |
| `unfao_bucket` | postprocessor `_save` (unfao.py:258-273) | views-faoapi (api.py:488) | `historical`, `forecast` |

Mechanics that matter:

- **"Latest" = newest `$createdAt`** (datastore.py:475-511). The postprocessor's only filter is `category: "forecast"` — no loa, model name, or run-id filter. If any other pgm-level product were ever uploaded with `category: "forecast"`, the postprocessor would silently consume it (registered as C-25 during this investigation).
- **No retention**: files accumulate indefinitely. Upload dedup is SHA-256 hash-based (file.py:2098-2110) but never removes old versions.
- **24 h local cache** with TTL + remote `$updatedAt` validation (file.py:2451-2569). faoapi adds its own 4 h in-memory + disk pickle cache layers (api.py:451-482); staleness there is advisory — stale data is served with a WARNING log, never blocked (api.py:458-465).

---

## 3. How they COULD work together

### Option 1 — GID-keyed lookup table built FROM the datafactory parquets (recommended)

Build once, offline:

1. Join the 7 area-majority parquets by `gid`.
2. Compute `pg_xcoord = -180 + ((gid-1) % 720) * 0.5 + 0.25` and `pg_ycoord = -90 + ((gid-1) // 720) * 0.5 + 0.25` (same formula pipeline-core already uses for row/col, dataloaders.py:1201-06).
3. Rename to the 9 contract columns (`gaul0_code → admin1_gaul0_code`, `iso3_code → country_iso_a3`, etc.).
4. Commit as a single parquet in views-postprocessing (~1-2 MB for africa_me_legacy; ~15 MB global).

Runtime enrichment becomes a merge-by-gid. Properties:

- **Serves BOTH paths.** Forecast data (from Appwrite) and historical data (from the factory) both carry `priogrid_gid`; the lookup doesn't care where the frame came from. This is the property no factory-delivery design can have.
- **Removes**: 774 MB LFS shapefiles, geopandas (~200 MB compiled deps), the import-time `set_default_mapper()` side effect (mapping.py:3171), and the entire mapper splash zone (register clusters A–D, the bulk of 22 open concerns).
- **faoapi-invisible** if the 9 columns are reproduced exactly (acceptance criterion, §4.1).
- **One semantic change to flag**: `country_iso_a3` source switches from Natural Earth to GAUL. Today the postprocessor mixes boundary datasets (NE for country, GAUL for admin1/2 — internally inconsistent at disputed borders); the lookup makes the row internally consistent and FAO-aligned. Needs a sign-off note to FAO (§4.3).

### Option 2 — Request GAUL columns via config_queryset.py (rejected, three independent blockers)

1. **Strings can't ride the zarr** — names and iso3 are not in the float32 grid and never can be (assemble_grid.py:558).
2. **fillna(0.0) corruption** — dataloaders.py:1208 unconditionally fills NaN with 0.0; any missing GAUL value would silently become code 0 instead of failing.
3. **Forecast path bypass** — forecast data never touches the factory; this design leaves the mapper in place for half the pipeline.

### Option 3 — Keep the runtime mapper (status quo, rejected by ADR-011)

Carries all open register concerns; duplicates a spatial computation the datafactory now owns (ADR-039 there); 774 MB LFS and geopandas remain hard dependencies of a repo whose actual runtime job is a merge and an upload.

### The 5 ocean cells — design decision needed at implementation time

Under the current mapper these cells (if ever present in input) get null country → `_validate()` crashes → fail-loud. The lookup must preserve that semantics: **unknown or unassigned gids must produce nulls, not sentinels**, so the existing validation gate still catches them. Concretely: either exclude `code = -1` rows from the lookup (merge produces NaN → validation fails loudly) or keep them with explicit nulls. Do NOT map `-1`/`""` through as values — `-1` is non-null and would sail through validation while being semantically wrong all the way to FAO.

Whether these 5 cells ever appear in prediction inputs is unverified (requires inspecting an actual forecast parquet from Appwrite). If they never appear, the point is moot but the fail-loud design should stand anyway.

---

## 4. Implications for the Appwrite store and views-faoapi

### 4.1 faoapi: zero changes, one acceptance criterion

The migration is downstream-invisible **iff** the postprocessor's output parquet keeps: the 9 metadata columns (exact names), `pred_*` prediction columns, and the `(month_id, priogrid_gid|priogrid_id)` MultiIndex. This should be the acceptance test for ADR-011: diff the output schema (names, dtypes, index) of the old mapper vs the new enricher on the same input — values may differ (that's the point), schema may not.

### 4.2 Appwrite: no structural changes, two standing observations

- The `category`-only "latest file" selection (C-25) becomes no more and no less fragile — but it is now a documented load-bearing link in the FAO chain.
- Unbounded retention means old centroid-era enriched files remain downloadable from `unfao_bucket` forever. After the migration, a stale cache or an explicit old-file download serves pre-area-majority attributions. Consider whether `unfao_bucket` needs a cleanup or versioning note.

### 4.3 FAO-facing data changes (must be communicated)

Switching enrichment source changes the VALUES FAO receives for border and coastal cells:

| Change | Magnitude (africa_me_legacy) | Direction |
|---|---|---|
| Country attribution changes | ~711 cells (5.4%) | centroid → area-majority (contractually correct per FAO Release Note 02) |
| Coastal cells recovered | 149 cells (carrying ~409,743 historical fatalities) | previously lost/null, now attributed |
| Internally consistent rows | all | country + admin1 + admin2 from one GAUL polygon instead of NE+GAUL mix |

This is the contractually *correct* behavior — FAO's own specification requires area-majority — but it is a data-version change FAO will see in the numbers. Recommend a release note accompanying the first post-migration upload.

### 4.4 Dtype note for implementation

The factory codes are int32. After a left-merge onto prediction frames, pandas will promote columns with any NaN to float64. The current mapper output passes faoapi's checks today, and faoapi checks only presence, not dtype (handlers.py:1160-63) — but the integration tests in this repo assert numeric dtype (test_integration.py:79-92). Match the current mapper's output dtypes in the enricher to keep both green.

---

## 5. Open questions

> **Plan of record (2026-06-12):** the delivery is now tracked as a cross-repo issue set — umbrella [views-postprocessing#20](https://github.com/views-platform/views-postprocessing/issues/20) (Plan C: baseline → lookup build → shadow diff → swap → go global), with [views-datafactory#159](https://github.com/views-platform/views-datafactory/issues/159) (`land_gaul` region, resolves the 82-cell question) and [views-models#127](https://github.com/views-platform/views-models/issues/127) (the go-global config flip).

| # | Question | Owner / resolution path |
|---|---|---|
| Q1 | Has the deployed zarr at 204.168.219.108 been re-exported/synced since the June 8 local assembly? (Local artifacts verified; remote not verifiable from here.) | User — check server or export ledger |
| Q2 | Do the 5 ocean-cell gids ever appear in prediction inputs? | Inspect a real forecast parquet when Appwrite access is available |
| Q3 | When/how to notify FAO of the attribution changes (§4.3)? | User / VIEWS-FAO channel |
| Q4 | Should the lookup be africa_me_legacy-only (~1-2 MB) or global (~15 MB)? Global is region-future-proof and still trivially small. | Decide at ADR-011 implementation |
| Q5 | unfao_bucket retention: do old centroid-era files need cleanup or a version marker? | User / platform decision |

---

## 6. Source map

| Claim area | File | Lines |
|---|---|---|
| Postprocessor descriptor | views-models `postprocessors/un_fao/configs/config_queryset.py` | 13-40 |
| Datafactory fetch + transforms | views-pipeline-core `modules/dataloaders/dataloaders.py` | 1117-1224 |
| Zarr URL default | views-datafactory `src/datafactory_query/defaults.py` | 24-45 |
| Consumer bridge | views-datafactory `src/datafactory_query/dataset.py` | 298-444 |
| DataFrame conversion | views-datafactory `src/datafactory_adapters/grid_to_dataframe.py` | 84-130 |
| Admin channel assembly | views-datafactory `scripts/assemble_grid.py` | 548-583, 714-717 |
| Area-majority generator | views-datafactory `scripts/generate_area_majority_gaul.py` | 283-294, 297-360 |
| Ensemble upload | views-pipeline-core `managers/model/model.py` 196-203; `managers/prediction/io.py` 111-144; `managers/prediction/savers.py` 120-154 | |
| Datastore upload/download | views-pipeline-core `modules/datastore/datastore.py` | 275-372, 475-568 |
| Appwrite file module | views-pipeline-core `modules/appwrite/file.py` | 2040-2273 (upload), 2451-2569 (download/cache) |
| Postprocessor manager | views-postprocessing `views_postprocessing/unfao/managers/unfao.py` | 44-273 |
| Runtime mapper enrichment | views-postprocessing `views_postprocessing/unfao/mapping/mapping.py` | 2489-2789, 3171 |
| faoapi manager | views-faoapi `src/views_faoapi/managers/api.py` | 422-612 (download), 637-923 (endpoints) |
| faoapi dataset contract | views-faoapi `src/views_faoapi/data/handlers.py` | 1143-1227, 357-366, 1206-09 |

Data artifacts verified by direct read (2026-06-12): all 7 GAUL parquet schemas/row counts, africa_me consistency counts, assembly provenance digests, ingestion ledger timestamps (Jun 5 codes, Jun 10/11 full regeneration).
