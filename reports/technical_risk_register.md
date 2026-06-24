# Technical Risk Register

| Register Info     | Details                              |
|-------------------|--------------------------------------|
| Project           | views-postprocessing                 |
| Owner             | Dylan Pinheiro / PRIO MD&D Team      |
| Last Updated      | 2026-06-24                           |
| Total Concerns    | 41                                   |
| Open Concerns     | 24                                   |
| Resolved Concerns | 17                                   |

---

## Tier Definitions

| Tier | Severity | Description |
|------|----------|-------------|
| 1 | Critical | Silent data corruption or model output correctness risk. Requires immediate attention. |
| 2 | High | Structural fragility that will cause failures under realistic change scenarios. |
| 3 | Medium | Maintainability or coupling issues that increase cost of change. |
| 4 | Low | Code quality concerns that do not affect correctness or reliability. |

---

## Causal Clusters

### Cluster A: Cache architecture never unified
**Root cause:** Disk and memory caching implemented by duplicating logic in every method rather than abstracting the cache interface.
**Entries:** C-05, C-06, C-14, C-16, D-01, D-02
**Highest tier:** 1 (C-16)
**Fix strategy:** Extract `CacheStrategy` interface with disk/memory implementations. Thread-lock in memory impl. Shapefile hash in disk cache keys.
**Resolution scope:** Full
**✅ RESOLVED 2026-06-24:** ADR-011 is executed and the runtime mapper (`mapping.py`) was deleted (C-39, PR #42). The cache machinery this cluster describes no longer exists — C-05, C-06, C-14, C-16, D-01, D-02 are all resolved.

### Cluster B: Silent error hiding architecture
**Root cause:** The codebase suppresses problem signals at three levels — global warning filter, DEBUG-level exception logging with `continue`, and raises without preceding logs. The impact propagates through a delivery chain with no correction mechanism.
**Entries:** C-12, C-19, C-20, C-21, C-22, D-03 (resolved), D-04 (resolved), C-18 (resolved)
**Highest tier:** 2 (C-12, C-21)
**Fix strategy (5/9 done):** ✅ Replace global warning suppression with targeted filter. ◻ Promote geometry errors from DEBUG to WARNING. ✅ Add `make_valid()` preprocessing. ◻ Narrow exception scope. ✅ Zero-area guard clause (all 7 sites). ◻ `logger.error` before all raises (3 of ~23 done). ✅ Surface batch failures to caller (both methods). ◻ Enrichment provenance in upload (timestamp added, no shapefile version). ◻ Post-delivery correction procedure (C-22).
**Resolution scope:** Full (code mechanisms) + Partial (operational impact — C-22 requires process documentation). **Note:** If D-05 resolves toward mapper elimination, remaining code fixes become moot.

### Cluster C: Module-level import side effect
**Root cause:** `set_default_mapper()` couples class definition with instantiation and shapefile loading at import time.
**Entries:** C-02, C-10
**Highest tier:** 2 (C-02)
**Fix strategy:** Lazy initialization or removal of module-level call. Add `mapper` constructor parameter to manager.
**Resolution scope:** Full
**✅ RESOLVED 2026-06-24:** ADR-011 is executed and the runtime mapper (`mapping.py`) was deleted (C-39, PR #42). The module-level `set_default_mapper()` side effect this cluster describes no longer exists — C-02 and C-10 are both resolved.

### Cluster D: Mapper-manager boundary contract
**Root cause:** No explicit contract declares what columns the mapper produces and the manager consumes.
**Entries:** C-04, C-17
**Highest tier:** 2 (C-04)
**Fix strategy:** Define `ENRICHMENT_SCHEMA` constant. Harmonize forward/reverse thresholds. Add end-to-end integration test.
**Resolution scope:** Full
**✅ RESOLVED 2026-06-24:** ADR-011 is executed and the runtime mapper (`mapping.py`) was deleted (C-39, PR #42). The mapper/manager column boundary is now a precomputed Parquet schema (`gaul_schema.py` + `GaulLookupEnricher`); there is no runtime forward/reverse divergence — C-04 and C-17 are both resolved.

### Cluster F: CIC-code drift (documentation describes aspirational, not actual behavior)
**Root cause:** CICs were written as design contracts and never validated against the code. Multiple guarantees are false.
**Entries:** Campaign findings 1.1, 1.2 — affecting CIC PriogridCountryMapper §3/§5/§6 and CIC UNFAOPostProcessorManager §3/§6
**Highest tier:** Not a code risk — documentation accuracy risk
**Fix strategy:** Update CICs to describe actual code behavior. Specifically: (1) cache guarantee needs C-05 caveat, (2) return types need full key listing, (3) §6 log level should say DEBUG not WARNING, (4) ADR-008 compliance claim needs qualifying, (5) env var boundary validation claim needs qualifying. Pure documentation, no code changes.
**Resolution scope:** Full
**✅ PARTIALLY RESOLVED 2026-06-24:** the `PriogridCountryMapper` CIC was deleted with the mapper (C-39, PR #42), so its drift findings (1.1, 1.2) are moot. The `UNFAOPostProcessorManager` CIC remains and is kept current (it now describes `GaulLookupEnricher`).

### Cluster E: Replace runtime mapper with precomputed lookup table
**Root cause:** The area-majority algorithm is a confirmed FAO requirement (D-05 resolved), but it doesn't need 3,100 lines of geopandas runtime code — a one-time precomputation produces a ~65K-row Parquet lookup table that replaces the entire mapper with a dictionary join.
**Entries:** C-23, D-05 (resolved), D-08, C-30, C-31, C-32, and transitively: Clusters A (cache), C (import side effect), plus C-07, C-08, C-11
**Highest tier:** 2 (C-23)
**Fix strategy (revised 2026-06-12):** (1) Build the lookup by joining views-datafactory's 7 area-majority GAUL parquets (regenerated June 11, 259,200 rows each) plus the GID→lat/lon formula — the original "run the current mapper with LFS" precomputation is obsolete. (2) Replace `mapping.py` with a simple Parquet-join enricher. (3) Remove 774 MB shapefile bundle, geopandas dependency, and all cache machinery. See `docs/cross_repo_integration_report.md` and ADR-011 assessment §10.
**Resolution scope:** Full — resolves Clusters A and C entirely. Eliminates C-07, C-08, C-11. Reduces Cluster B to manager-side concerns only (C-19 unfao.py raises, C-21 batch tracking, C-22 correction process).
**✅ EXECUTED 2026-06-24:** the lookup enricher shipped (`GaulLookupEnricher`, ADR-011) and the runtime mapper + shapefiles + geopandas were deleted (C-39, PR #42). The remaining open entries here are the datafactory-side area-math (C-08/C-31, tracked in views-datafactory) and the manager-side Cluster B residue (C-19/C-22) — not mapper code.

---

## Open Concerns

### C-03: Test coverage gaps in manager validation and the enrich→validate path

| Field | Value |
|-------|-------|
| ID | C-03 |
| Tier | 3 |
| Source | `repo-assimilation` (2026-06-02), `test-review` (2026-06-02) |
| Trigger | When modifying the manager's `_validate()` or the enricher, verify that the test suite covers the changed behavior — end-to-end coverage across the enrich→validate path is still absent |
| Location | `tests/test_validation.py`, `views_postprocessing/unfao/managers/unfao.py` |

Initial state was zero test coverage. A 73-test suite was written (2026-06-02) covering the (now-deleted) mapper's core guarantees and the validation logic (missing columns, null rejection, error messages). Remaining gaps after the mapper removal: (1) the validation tests replicate `_validate()` logic in a standalone function because `views-pipeline-core` is unavailable in test environments — if the real `_validate()` diverges, tests pass while production fails; (2) no end-to-end test enriches through `GaulLookupEnricher` then validates through the manager.

Tier recalibrated from 2 to 3 during review-rr (2026-06-02): the gap is maintainability (test-code divergence, missing integration path), not structural fragility.

**Update 2026-06-24:** narrowed with the mapper deletion (C-39, PR #42). The mapper-coverage dimension is gone with the mapper (`tests/test_mapping.py` deleted; the determinism/cache/shapefile/`ThreadPoolExecutor` gaps no longer exist). Two manager-side gaps remain: the standalone `_validate()` replica and the missing enrich→validate end-to-end test.

---

### C-07: Undeclared direct runtime dependencies in pyproject.toml

| Field | Value |
|-------|-------|
| ID | C-07 |
| Tier | 3 |
| Source | `repo-assimilation` (2026-06-02) |
| Trigger | When `views-pipeline-core` updates its dependency tree (e.g., drops `geopandas` or `joblib`), verify that this package's imports still resolve |
| Location | `pyproject.toml:11-13`, `views_postprocessing/unfao/mapping/mapping.py:1-20` |

`mapping.py` directly imports `geopandas`, `shapely`, `numpy`, `pandas`, `joblib`, and `multiprocessing`. `unfao.py` directly imports `pandas`, `polars`, and `python-dotenv`. Only `views-pipeline-core` and `cachetools` are declared in `pyproject.toml`. The undeclared dependencies presumably arrive transitively via `views-pipeline-core`, but this coupling is implicit and fragile. If the upstream package refactors its dependency tree, this package will break with `ImportError` at install time.

---

### C-08: Planar area calculation on geographic (degree-based) coordinates

| Field | Value |
|-------|-------|
| ID | C-08 |
| Tier | 3 |
| Source | `repo-assimilation` (2026-06-02) |
| Trigger | When processing PRIO-GRID cells above 55°N or below 55°S (e.g., Russia-Ukraine border, Nordic countries), verify that country/admin assignment is correct for cells straddling boundaries |
| Location | `views_postprocessing/unfao/mapping/mapping.py:649-650,920,1192,1428` |

All overlap ratio calculations use `.area` on EPSG:4326 geometries, which produces values in square degrees. At the equator, 1° longitude ≈ 1° latitude in distance. At 60°N, 1° longitude ≈ 0.5° latitude in distance, distorting area by up to 2x. For border cells at high latitudes, this distortion could theoretically cause incorrect assignment to the wrong country/admin region. In practice, most VIEWS conflict prediction zones are equatorial/mid-latitude, limiting the impact. No projection to equal-area CRS is performed before area calculations.

**Update 2026-06-12 (expert-code-review):** The "equatorial/mid-latitude, limiting the impact" rationale dies with the planned global coverage — Russia, Scandinavia, and Canada (55°N+) enter scope when the region switches to `"land"`. Mitigating consideration: within a single 0.5° cell, all candidate polygon intersections sit at the same latitude band, so the cos(lat) distortion multiplies all candidates roughly equally and largely cancels in the *ranking* — this applies to both this repo's mapper and the datafactory's area-majority script. Required action before global delivery: one falsification probe on ~20 border cells above 55°N comparing degree-based assignment against an equal-area-projected computation. See C-31 (mapper unverified at global scale).

---

### C-09: Publish workflow validates version against wrong PyPI package

| Field | Value |
|-------|-------|
| ID | C-09 |
| Tier | 4 |
| Source | `repo-assimilation` (2026-06-02) |
| Trigger | When publishing a new release of `views-postprocessing`, the version check may incorrectly pass or fail because it compares against `views-pipeline-core` on PyPI |
| Location | `.github/workflows/publish_package.yml:33` |

The "Validate Version" step fetches the latest version from `https://pypi.org/pypi/views-pipeline-core/json` instead of `https://pypi.org/pypi/views-postprocessing/json`. This compares the local `views-postprocessing` version against `views-pipeline-core`'s PyPI version, which is a different package entirely. The check may incorrectly block a valid release or allow a version that collides with an existing `views-postprocessing` release.

---

### C-13: No timeout on Appwrite operations — pipeline can hang indefinitely

| Field | Value |
|-------|-------|
| ID | C-13 |
| Tier | 2 |
| Source | `expert-review` (2026-06-02) |
| Trigger | When configuring Appwrite connection parameters in `_read_forecast_data` or `_save`, verify that timeout parameters are set on the underlying HTTP client — currently no timeout exists and a hung endpoint blocks the pipeline indefinitely |
| Location | `views_postprocessing/unfao/managers/unfao.py:131,262,272` |

`prediction_store_manager.download_latest_file()` (line 131) and `dsm.upload_data()` (lines 262, 272) make network calls to Appwrite with no configured timeout. If the endpoint hangs (DNS resolution stalls, connection accepted but response never arrives, TLS handshake blocks), the pipeline blocks indefinitely. There is no watchdog timer, no circuit breaker, and no automated alert for a run that never completes. The only detection is manual observation that a scheduled run didn't finish.

---

### C-15: Upload metadata lacks enrichment provenance and carries test description

| Field | Value |
|-------|-------|
| ID | C-15 |
| Tier | 3 |
| Source | `expert-review` (2026-06-02), `falsification-audit` (2026-06-02) |
| Trigger | When UN FAO needs to audit the quality or provenance of received data, verify that upload metadata includes shapefile version, enrichment timestamp, and error count — currently none of these are present |
| Location | `views_postprocessing/unfao/managers/unfao.py:262-267,272-277` |

Both `dsm.upload_data()` calls in `_save()` carry metadata: `name`, `loa`, `type`, `targets`, `description`, `category`. The `description` field was updated from a hardcoded test string to an enrichment timestamp (`"Enriched with geographic metadata on {timestamp}"`). However, broader enrichment provenance is still missing: no shapefile version/hash, no enrichment error count, no unmapped cell count. The consumer cannot verify which shapefile version produced their data or whether any errors occurred during enrichment.

Tier recalibrated from 4 to 3 during falsification audit (2026-06-02): the missing provenance affects the partner's ability to audit data quality.

See also C-14 (stale cache without version tracking), C-22 (no post-delivery correction process).

---

### C-19: Systematic ADR-008 non-compliance — 23 of 24 raises lack preceding log

| Field | Value |
|-------|-------|
| ID | C-19 |
| Tier | 3 |
| Source | `falsification-audit` (2026-06-02) |
| Trigger | When a structural failure occurs in `PriogridCountryMapper` and the operator searches logs for context, verify that the exception was preceded by a `logger.error` — currently 20 of 24 raises in mapping.py and 3 in unfao.py have no preceding log |
| Location | `views_postprocessing/unfao/mapping/mapping.py` (20 raises), `views_postprocessing/unfao/managers/unfao.py:70,80,230` |

ADR-008 requires structural failures to be both logged persistently AND raised explicitly. Three validation methods in mapping.py and the C-01 fix in unfao.py were fixed with log-before-raise. 20 raises in mapping.py and 3 in unfao.py remain unfixed.

Part of Cluster B (expanded scope).

**Update 2026-06-24:** the mapper portion (20 of the 23 raises, in `mapping.py`) is gone with the deleted runtime mapper (C-39); the **3 raises in `unfao.py`** remain (tracked by issue #13). Narrowed to the manager.

---

### C-22: No post-delivery correction process for wrong assignments

| Field | Value |
|-------|-------|
| ID | C-22 |
| Tier | 3 |
| Source | `falsification-audit` (2026-06-02) |
| Trigger | When a Cluster B error is discovered after data has been uploaded to the UN FAO Appwrite bucket, verify that a correction/recall procedure exists — currently none is documented or implemented |
| Location | `views_postprocessing/unfao/managers/unfao.py:259-277`, `reports/technical_risk_register.md` (Cluster B) |

The delivery chain has four stages beyond the code: Appwrite bucket → UN FAO download → FAO systems → operational decisions. When an error is discovered post-delivery, correction requires clearing cache, re-running, re-uploading, notifying FAO, and FAO retracting old data. Steps 3-5 have no documented procedure.

Part of Cluster B (operational impact dimension). See also C-14, C-15.

---

### C-23: Algorithmic divergence — area-based vs centroid-based GAUL mapping across VIEWS platform

| Field | Value |
|-------|-------|
| ID | C-23 |
| Tier | 2 |
| Source | `manual` (2026-06-02) — external assessment |
| Trigger | When datafactory's assembled grid is used alongside postprocessor enrichment for the same GIDs, verify that gaul0/gaul1/gaul2 assignments agree — currently they use different algorithms (centroid vs area-based) that disagree on border cells |
| Location | `views_postprocessing/unfao/mapping/mapping.py` (area-based), external `views-datafactory/datafactory/gaul_admin.py` (centroid-based) |

The VIEWS platform has two independent PRIO-GRID-to-GAUL mapping implementations using different algorithms. For the ~95% of cells entirely within one region, both agree. For border cells, they disagree — and nothing reconciles them. It is unclear whether area-based is a deliberate FAO requirement or historical accident.

**Update 2026-06-12 — divergence resolved upstream.** views-datafactory shipped area-majority GAUL assignment (issue #115 → PR #127, v1.2.28/29); all 7 GAUL parquets regenerated June 11 as area-majority. Both implementations now use the same algorithm family. Residual difference: this repo's mapper sources `country_iso_a3` from Natural Earth while the factory uses GAUL boundaries — disputed-border cells can still differ on ISO code. This residual disappears when ADR-011's lookup (built from factory parquets) replaces the mapper. See `docs/cross_repo_integration_report.md`.

Part of Cluster E. See also D-05 (the gating decision), C-11 (god class — moot if mapper eliminated).

---

### C-24: Postprocessor output schema diverges from FAO-confirmed API contract

| Field | Value |
|-------|-------|
| ID | C-24 |
| Tier | 2 |
| Source | `falsification-audit` (2026-06-02) |
| Trigger | When verifying that postprocessor output matches the FAO API contract (Release Note 01, Topic C), check whether field names and coding systems align — currently 3 of 4 data categories use different conventions |
| Location | `views_postprocessing/unfao/managers/unfao.py:146-158` (filter_cols), FAO Release Note 01 `topic_c.tex` |

The FAO API contract (Release Note 01, Topic C, confirmed and locked) specifies: UN M49 country codes, `ADM1_CODE`/`ADM1_NAME`/`ADM2_CODE`/`ADM2_NAME` for admin fields, and `lat`/`lon` for coordinates. The postprocessor's `filter_cols` uses: `country_iso_a3` (ISO Alpha-3), `admin1_gaul1_code`/`admin1_gaul1_name`/`admin2_gaul2_code`/`admin2_gaul2_name`, and `pg_xcoord`/`pg_ycoord`. Three of four data categories (country ID, admin fields, coordinates) use different naming conventions from the locked contract.

**D-06 resolved (2026-06-03):** Investigation of views-faoapi confirms NO renaming layer exists. The `FAOApiManager` passes postprocessor column names through to the HTTP response unmodified. FAO receives `country_iso_a3`, `admin1_gaul1_code`, `pg_xcoord` — not the contract-specified names. The column renaming from Release Note 01 Topic C was never implemented in any repo.

**This is NOT this repo's responsibility to fix.** The schema mismatch is between the API layer (views-faoapi) and the FAO contract. The postprocessor should keep its current column names — changing them now would break views-faoapi's `FAO_PGMDataset._METADATA_COLS` validation. The renaming belongs in views-faoapi as a response-formatting step, coordinated with FAO.

See also C-17 (implicit column naming between mapper and manager), D-06 (resolved: no renaming layer exists).

---

### C-25: Forecast input selected by category-only filter — newest file wins regardless of producer

| Field | Value |
|-------|-------|
| ID | C-25 |
| Tier | 2 |
| Source | `cross-repo-investigation` (2026-06-12) |
| Trigger | When any new producer uploads to the prod_forecasts bucket with `category: "forecast"`, verify the postprocessor still picks up the intended ensemble's file — selection is newest-`$createdAt`-wins with no loa, model-name, or run-id filter |
| Location | `views_postprocessing/unfao/managers/unfao.py:126`; views-pipeline-core `modules/datastore/datastore.py:475-511` |

`_read_forecast_data()` calls `download_latest_file(filters={"category": "forecast"})`. "Latest" is resolved by sorting metadata documents on `$createdAt` descending and taking the first (datastore.py:475-511). There is no filter on `loa`, `name`, `targets`, or any run identifier. Today only the production ensemble uploads with this category, so the newest file is the right file by circumstance, not by contract. If a second model, a test run, or a backfill ever uploads to the same bucket with `category: "forecast"`, the postprocessor silently enriches and ships the wrong predictions to FAO. The same single-filter pattern exists downstream: views-faoapi selects from the unfao_bucket by category only (views-faoapi `api.py:488`), so a stray upload there reaches FAO directly. Compounding factor: Appwrite has no retention — every historical upload remains a candidate forever; correctness depends entirely on upload discipline.

This concern became visible during the cross-repo investigation (`docs/cross_repo_integration_report.md` §2.4, §4.2); it was previously implicit in the C-13 narrative (timeouts) but is a distinct failure mode: C-13 is "the call hangs," C-25 is "the call succeeds with the wrong file."

See also C-13 (no timeout on the same calls), C-15 (upload metadata lacks provenance to detect this downstream).

---

### C-26: Unconditional fillna(0.0) fabricates "no conflict" from missing upstream data

| Field | Value |
|-------|-------|
| ID | C-26 |
| Tier | 1 — silent data fabrication with no error signal: absence of evidence becomes evidence of absence in FAO-delivered values |
| Source | `expert-code-review` (2026-06-12) |
| Trigger | When the datafactory zarr has missing months or cells inside the requested range (failed harvest, partial assembly), verify the postprocessor fails rather than zero-fills — currently every NaN becomes 0.0 with no count logged |
| Location | views-pipeline-core `modules/dataloaders/dataloaders.py:1208`; consumed at `views_postprocessing/unfao/managers/unfao.py:48-56` |

`_fetch_data_from_datafactory()` applies `df.fillna(0.0)` unconditionally to all features. For `lr_ged_sb/ns/os`, a datafactory assembly gap (unharvested month, failed source) flows to FAO as "zero fatalities" rather than failing. The postprocessor's `_validate()` checks only the 9 metadata columns for nulls (`unfao.py:188-221`), never the feature columns — so the fabricated zeros pass every gate. There is no fill-count logging, so the corruption is unquantified and undetectable after the fact. The zarr exposes `last_valid_month_id` in its attributes, which would permit bounded filling (fill only outside the declared valid range, fail on fills inside it), but it is not consulted.

Location is in views-pipeline-core, but the impact lands on this repo's FAO delivery; registered here because the consuming call and the delivery responsibility are here.

See also C-25 (same data path, wrong-file variant), C-15 (upload provenance would aid post-hoc detection).

---

### C-27: Loader construction failures swallowed — surface as remote AttributeError

| Field | Value |
|-------|-------|
| ID | C-27 |
| Tier | 2 — structural fragility: any dependency or config breakage is converted into a misleading crash far from its cause |
| Source | `expert-code-review` (2026-06-12) |
| Trigger | When a dependency bump, import error, or config change breaks `ViewsDataLoader` construction, verify the real exception is visible — currently it is caught bare, logged as "No Queryset detected" with `exc_info=False`, and replaced with `self._data_loader = None` |
| Location | views-pipeline-core `managers/model/model.py:883-902`; crash site `views_postprocessing/unfao/managers/unfao.py:48` |

`_initialize_data_loader()` catches bare `Exception`, discards the traceback, and nulls the loader. The failure then surfaces as `AttributeError: 'NoneType' object has no attribute 'get_data'` in `_read_historical_data` — the operator debugs the postprocessor while the cause (import error, malformed config, path issue) was erased at construction time. Cost is time-to-diagnosis during exactly the runs where time matters.

---

### C-28: No timeout on the datafactory zarr fetch — historical path can hang indefinitely

| Field | Value |
|-------|-------|
| ID | C-28 |
| Tier | 2 — same hazard class as C-13, on the other input path; a stalled chunk read blocks delivery with no deadline or alert |
| Source | `expert-code-review` (2026-06-12) |
| Trigger | When the datafactory HTTP server accepts connections but stalls mid-chunk (network degradation to the zarr host), verify the pipeline run terminates — no deadline exists anywhere on the fetch path |
| Location | views-pipeline-core `modules/dataloaders/dataloaders.py:1180-1188`; views-datafactory `src/datafactory_query/dataset.py:106-217` |

`load_dataset()` opens a remote zarr over plain HTTP. xarray chunk reads have no timeout; a stall blocks the scheduled run forever, and the only detection is manually noticing a run never finished. Risk grows with the planned global region (~5× data volume → longer fetch window). Partial overlap with C-13 (no timeout on Appwrite operations) — same problem type, different dependency and repo; registered separately because the fix sites are disjoint.

See also C-13.

---

### C-29: Manager reads fetch result via disk side-channel instead of return value

| Field | Value |
|-------|-------|
| ID | C-29 |
| Tier | 2 — under a realistic pipeline-core caching refactor, the postprocessor silently reads a stale previous parquet and enriches outdated data |
| Source | `expert-code-review` (2026-06-12) |
| Trigger | When views-pipeline-core changes caching behavior (format, filename template, skip-write optimization), verify `_read_historical_data` still reads what `get_data()` just produced — the return value is discarded and the dataframe re-read from `cached_data_path` |
| Location | `views_postprocessing/unfao/managers/unfao.py:48-56`; views-pipeline-core `modules/dataloaders/dataloaders.py:1490-1494` |

`get_data()` returns `(df, alerts)`; the manager discards it and re-reads from `self._data_loader.cached_data_path`, a property set as a side effect of the fetch. Two sources of truth for "the data just fetched," coupled by an undocumented convention. If pipeline-core ever skips the disk write for `use_saved=False` (a legitimate optimization from its perspective), the manager reads a stale previous file silently — or crashes if none exists. The convention has already drifted once: the loader docstring (dataloaders.py:1466-1471) still documents `{partition}_viewser_df` naming while the code now formats `{partition}_{source}_df` (line 1490). Fix is one line: consume the return value. Related to views-pipeline-core register entries C-59/C-60 (cache filename convention).

---

### C-30: 82 GAUL-uncovered land cells crash or corrupt global delivery

| Field | Value |
|-------|-------|
| ID | C-30 |
| Tier | 1 — with `-1`/`""` passed through, validation passes and FAO receives rows attributed to country "-1" (silent); with nulls, the delivery run crashes (loud, but on delivery day) |
| Source | `expert-code-review` (2026-06-12), verified by direct data inspection |
| Trigger | When the region switches from `africa_me_legacy` to `land` for global historical delivery, verify the 82 unassigned cells are explicitly excluded before `_validate()` — they have no GAUL assignment in any source |
| Location | `views_postprocessing/unfao/managers/unfao.py:188-221`; views-datafactory `data/raw/gaul_admin/gaul0_code.parquet` (value = -1) |

Verified 2026-06-12: of the datafactory's 64,818 `land`-region cells, 64,736 have complete area-majority metadata; exactly 82 are unassigned across all 7 GAUL fields — all remote sub-Antarctic islands FAO's GAUL 2024 boundaries do not cover (Macquarie, Auckland Islands, Prince Edward; sample gids 51078, 51798, 53979, 62356, 94776, 99027). The mitigation must be a named exclusion-list constant with the 82 gids, count-asserted (`== 82`) in both the enricher and a test, logged at WARNING, and disclosed to FAO — not a generic `code != -1` filter, which would silently absorb future coverage regressions. Generalizes the previously documented "5 ocean cells" of africa_me_legacy (those 5 are among the 82).

See also D-10 (handling decision), C-34 (coverage contract).

---

### C-31: Runtime mapper unverified and unverifiable at global scale

| Field | Value |
|-------|-------|
| ID | C-31 |
| Tier | 2 — choosing this path for global delivery converts unknown runtime, unknown memory, and unknown Natural-Earth coverage into delivery-day discoveries |
| Source | `expert-code-review` (2026-06-12) |
| Trigger | Before any global (`land` region) run that enriches via `mapping.py`, verify runtime, peak memory, and Natural-Earth assignment coverage for all 64,818 cells — none has ever been measured, and none can be measured in the development environment (shapefiles are LFS stubs) |
| Location | `views_postprocessing/unfao/mapping/mapping.py:2727` (per-gid boolean mask over all 259,200 grid rows — O(N) per lookup), `mapping.py:649-650,920,1192,1428` (degree-based area math, C-08, newly in scope above 55°N) |

The mapper is production-proven at 13,110 cells and never executed at 64,818. Per-cell linear scans put plausible global runtime in the hours; any cell Natural Earth fails to assign produces a null that crashes `_validate()` **at the end of those hours**. The equivalent completeness number for the lookup path is known exactly (C-30: 64,736/82); for the mapper path it is unknowable before a production-machine run. This asymmetry — enumerable versus discoverable failures — is the core argument in D-08.

See also C-08 (high-latitude math, escalated), C-11 (god class), D-08.

---

### C-32: Unbudgeted memory at global enrichment volume

| Field | Value |
|-------|-------|
| ID | C-32 |
| Tier | 2 — realistic MemoryError mid-`_transform` on the planned global run; fails after the fetch succeeded, late in the pipeline |
| Source | `expert-code-review` (2026-06-12) |
| Trigger | Before the first global historical run, verify peak memory of joining 9 metadata columns onto ~28M rows (64,818 cells × ~432 months) — four string columns as pandas object dtype cost roughly 8–20 GB at this scale |
| Location | `views_postprocessing/unfao/managers/unfao.py:154-163` (the metadata join); any replacement enricher |

Object-dtype strings (`admin1_gaul0_name`, `admin1_gaul1_name`, `admin2_gaul2_name`, `country_iso_a3`) broadcast to 28M rows dominate memory. Mitigation is cheap and should be built into any new enricher from day one: pandas categorical dtype for the string columns (~10× reduction; the underlying uniques number in the low thousands). A full-volume dry run (fetch → enrich → validate → local parquet, no upload) before delivery day is the verification.

---

### C-33: Store identity hardcoded throughout the manager — blocks the planned multi-store rollout

| Field | Value |
|-------|-------|
| ID | C-33 |
| Tier | 2 — two to three additional Appwrite stores are planned imminently; the current design forces copy-pasting a 273-line manager per store |
| Source | `expert-code-review` (2026-06-12) |
| Trigger | When the second Appwrite prediction store is configured, verify store identity comes from configuration — currently env var names (`APPWRITE_UNFAO_*`, `APPWRITE_PROD_FORECASTS_*`) are inline in two hand-built `AppwriteConfig` blocks, the forecast targets list is hardcoded, and category strings are literals |
| Location | `views_postprocessing/unfao/managers/unfao.py:109-122, 234-247, 272`; dead alternative config blocks at `unfao.py:80-107` |

Mitigation: a small `DeliveryProfile` (bucket/collection/database ids, category, targets) passed to the manager — one manager class, N store configs. Scheduled **after** the FAO global delivery ships (D-09); the only immediate action is deleting the commented-out config blocks at lines 80-107, which are a mis-uncomment hazard during deadline work.

See also C-24 (schema contract per store), D-09.

---

### C-34: Spatial coverage has no contract — no assertion of expected cell count anywhere

| Field | Value |
|-------|-------|
| ID | C-34 |
| Tier | 2 — a wrong or upstream-changed region definition delivers partial coverage to FAO with no error signal |
| Source | `expert-code-review` (2026-06-12) |
| Trigger | When the region string in views-models `config_queryset.py` or the datafactory's bundled `land_pgids.json` / `africa_me_legacy_pgids.json` changes, verify this repo notices — today nothing asserts how many cells the pipeline expects to process |
| Location | views-models `postprocessors/un_fao/configs/config_queryset.py:20`; views-datafactory `src/datafactory_query/regions.py:126-152`; no counterpart check in `views_postprocessing/` |

The coverage decision lives in one repo (views-models), the cell-set definition in a second (views-datafactory), and the consequences in a third (this repo). Mitigation: a coverage test asserting enrichment completeness for the configured region (for `land`: 64,736 complete + exactly the 82 known exclusions), plus cell-count logging in `_read` and `_validate`.

See also C-30, C-26 (both are coverage-integrity failures with no signal).

---

### C-35: Invalid `-99` country code shipped to FAO for Somaliland cells

| Field | Value |
|-------|-------|
| ID | C-35 |
| Tier | 1 — silent invalid data delivered to the partner: a non-ISO sentinel string passes the null-only validation gate and reaches FAO as a country code |
| Source | `enrichment-diff` (2026-06-18) — empirically measured, old mapper vs new lookup on africa_me |
| Trigger | Whenever the current runtime mapper enriches cells in the Somaliland region (and any other Natural Earth `ISO_A3 = "-99"` territory), it emits `country_iso_a3 = "-99"`; `_validate()` checks only for nulls, so the invalid code ships |
| Location | `views_postprocessing/unfao/mapping/mapping.py` (country from Natural Earth `ISO_A3`); `unfao.py:188-221` (`_validate` — null-only, no code-validity check); Natural Earth `ne_10m_admin_0_countries` (`ADMIN="Somaliland", ISO_A3="-99"`) |

The current mapper sources `country_iso_a3` from Natural Earth's `ISO_A3` field. Natural Earth represents Somaliland as a separate de-facto entity but assigns it the sentinel `ISO_A3 = "-99"` (no recognized ISO code). The diff measured **64 africa_me cells** delivered with `country_iso_a3 = "-99"`. Because `"-99"` is a non-null string, the `_validate()` gate (which only rejects nulls) passes it, and it reaches the FAO Appwrite bucket as the country code for those cells. FAO consumers filtering or aggregating by country code receive an invalid value.

**Resolved by ADR-011's lookup.** The new GAUL-sourced lookup has zero `-99` codes anywhere (verified across all 64,742 global cells); Somaliland cells become `SOM` (Somalia), matching GAUL — FAO's own boundary product. So the engine swap (Stage 3) eliminates this defect as a side effect. Until the swap ships, the current production output carries it. Note: other Natural Earth `-99` territories (e.g. N. Cyprus, Kosovo) could surface the same way outside africa_me — the global swap covers them too.

See also C-01 (null-validation re-enabled — but it does not check code *validity*), and the disputed-territories section of `reports/enrichment_diff/report.md`.

---

### C-37: Reconciliation uses a pragmatic per-draw approximation, not principled probabilistic reconciliation

| Field | Value |
|-------|-------|
| ID | C-37 |
| Tier | 3 |
| Source | `manual` (2026-06-24) — phase-2 reconciliation migration |
| Trigger | When reconciliation is wired into a delivery and its uncertainty is consumed (intervals, scores), verify the method is the principled one — the current per-draw scaling can distort the joint predictive distribution |
| Location | `views_postprocessing/reconciliation/proportional.py` |

`reconcile_proportional` is a faithful numpy port of views-reporting's `ForecastReconciler.reconcile_forecast`: **top-down disaggregation using forecast proportions** (FPP3), applied **per posterior draw**. It rescales each marginal draw independently to hit that draw's country total, which implicitly assumes the grid and country samples are index-aligned joint draws. This is a pragmatic approximation, **not** principled joint probabilistic reconciliation (the IJF paper, PII `S0169207023001097` — exact title TBC; cf. FPP3 §reconciliation), under which the reconciled draws would be coherent samples from a single reconciled joint distribution (e.g. MinT-style projection on samples). The migration deliberately preserves the existing method first (parity proven bit-for-bit against the untouched views-reporting oracle, `tests/test_reconciliation_parity.py`); the upgrade is **gated behind** completing the move and wiring (slices 2-3) so behaviour change and relocation never mix. Until then, treat reconciled uncertainty as approximate.

See also the migration plan (reconciliation slices 2-4) and views-reporting issue #72 (the relocation).

**Update 2026-06-24 (expert-code-review, Kleppmann lens):** the per-draw index-pairing is only *valid* if the production cm and pgm forecasts are the **same joint posterior draws**. If they come from independent models (separate posteriors), pairing draw *s* of the grid with draw *s* of the country is arbitrary and the reconciled uncertainty is meaningless — and the parity fixture cannot detect this, because it manufactures aligned draws. **At S7 (#39) wiring, verify the sample-alignment assumption against the real pipeline as a hard precondition** (or escalate the C-37 upgrade). This is a correctness precondition distinct from the "is the method principled" question.

---

### C-38: Reconciliation grouping is O(groups × N) and materializes the whole grid frame — won't scale to global volume

| Field | Value |
|-------|-------|
| ID | C-38 |
| Tier | 2 |
| Source | `expert-code-review` (2026-06-24) |
| Trigger | Before the first global / `land`-region reconciliation run — i.e. before wiring at S7 (#39) — benchmark `ReconciliationModule.reconcile` runtime and peak memory on global-volume frames; nothing above the 39-row fixture has been measured |
| Location | `views_postprocessing/reconciliation/grouping.py:69-79` (per-group `np.nonzero(inverse == gi)`); `views_postprocessing/reconciliation/module.py` (holds the full pgm frame; `np.empty_like` copy) |

`reconcile_pgm_to_cm` groups grid rows with `np.unique` (good) but then loops over unique `(time, country)` groups doing `np.nonzero(inverse == gi)` **per group** — an O(groups × N_pg) full-array scan. At global scale (~86k groups × ~28M pgm rows) that is ~10¹² comparisons plus 86k full-size boolean masks. Separately, the module holds the **entire** pgm frame at once (28M rows × S samples × 4 bytes ≈ 11 GB at S=100, **>100 GB at S=1000**) and `np.empty_like` doubles it — the original views-reporting code processed per-country subsets, never materialized the global frame, and used `ProcessPoolExecutor` for exactly this scale. **Parity is unaffected** (the result is identical); only runtime/memory blow up. Mitigation: replace the per-group `nonzero` with a single `argsort(inverse)` + contiguous slices (O(N log N)); budget/measure peak memory on a global-volume dry run and chunk by time or country if needed — both **before** wiring. Same enumerable-vs-discovered-at-scale pattern as C-31/C-32.

Tier 2: structural fragility under the realistic change of wiring to global, with a clear trigger; not Tier 1 (no silent corruption — parity is exact; this is a runtime/memory failure). See also C-31 (mapper scale), C-32 (enricher memory), C-37 (the algorithm), epic #31 / views-reporting#72.

**Update 2026-06-24 — compute RESOLVED.** The per-group `np.nonzero(inverse == gi)` was replaced with **group-by-sort** (`argsort(inverse)` + contiguous slices from `np.unique` counts, O(N log N), one index array). Parity stays **bit-exact** (`tests/test_reconciliation_grouping.py`, `test_reconciliation_e2e_parity.py` → 0.0) and a scale guard (`tests/test_reconciliation_scale.py`) protects against regression. **Residual (still open):** the module holds the whole pgm frame in memory at once; at global volume the **caller must chunk by time** (reconciliation is independent across months) — the chunk-by-time contract is documented in the CIC (`docs/CICs/ReconciliationModule.md` §5), to be **verified on a global-volume dry-run at S7 (#39)**. This entry stays open until that verification.

---

### C-40: FAO delivery logic fused to pipeline-core via double inheritance + interleaved infrastructure

| Field | Value |
|-------|-------|
| ID | C-40 |
| Tier | 2 |
| Source | `expert-code-review` (2026-06-24) |
| Trigger | When pipeline-core changes `PGMDataset` / the data loader / the postprocessor base (it is mid-migration: their #186/#188/#161), or when wanting to unit-test or numpy-ify the FAO enrich/validate without standing up the whole framework |
| Location | `views_postprocessing/unfao/managers/unfao.py:26` (double inheritance); `:78-98` and `:185-199` (inline env/AppwriteConfig/DatastoreModule); `:112-122` (`_append_metadata`), `:147-172` (`_validate`) |

`UNFAOPostProcessorManager` subclasses **two concrete** pipeline-core base classes (`PostprocessorManager`, `ForecastingModelManager`) and **interleaves infrastructure** (env reading, `AppwriteConfig` construction, `DatastoreModule`, path resolution) with the FAO **business logic** (GAUL enrichment, the 9-column null gate) inside the lifecycle hooks. Consequences: (a) the FAO logic cannot be instantiated or unit-tested without the full framework + Appwrite env + viewser; (b) **pandas cannot leave the delivery path** because the inherited data loader and `PGMDataset` are pandas — gated on pipeline-core's own DataFrame retirement; (c) **SDP exposure** — heavy *inheritance* coupling to a pipeline-core that is itself unstable (mid-migration), so upstream changes break far from their cause (cf. C-27, C-29); (d) it's the repo's only composition-over-inheritance violation. The dependency itself is correct (`unfao.py` genuinely *is* a pipeline-core postprocessor) — the issue is its **blast radius**. Mitigation (does **not** fight the Template-Method framework): keep the subclass as a **thin shell** but extract `enrich` + `validate` + the 9-column contract into a pipeline-core-free core object the manager *calls*, and wrap the Appwrite I/O behind a small delivery-sink adapter (DIP). This makes the FAO logic testable standalone and insulates it from pipeline-core churn.

See also C-07/C-27/C-29 (pipeline-core coupling symptoms), C-39 (the dead-mapper cleanup that precedes any unfao restructuring).

---

## Disagreements

### D-05: Strategic direction — eliminate runtime mapper vs keep area-based algorithm

| Field | Value |
|-------|-------|
| ID | D-05 |
| Source | `manual` (2026-06-02) — external assessment |
| Perspectives | Path A: area-based is a FAO requirement → precompute lookup table. Path B: centroid-based acceptable → eliminate mapping.py entirely. Both eliminate 774 MB shapefiles, geopandas, and 3,100-line mapper. |
| Resolution | **Resolved (2026-06-02): Path A confirmed.** FAO-FSFC provided written confirmation (Release Note 02, `summary.tex`) agreeing to area-majority allocation as the locked aggregation rule: "Each PRIO-GRID cell is assigned to a single country using an area-majority rule." The area-based algorithm is a contractual requirement, not a historical accident. Path B (centroid-based) is off the table. Next step: build a one-time precomputed area-based lookup table (~65K rows, Parquet) and replace the 3,100-line runtime mapper with a dictionary lookup. This still eliminates geopandas, the shapefile bundle, and the runtime spatial operations — but preserves the area-majority assignment rule. |
| Update 2026-06-12 | **Upstream resolution deployed.** views-datafactory shipped area-majority GAUL assignment (issue #115 → PR #127, ADR-039 there, v1.2.28/29). All 7 GAUL parquets (codes + names + iso3) regenerated June 11 as area-majority, 259,200 rows each, mutually consistent (13,105/13,110 africa_me cells fully attributed; 5 pure-ocean cells unassigned). The precomputed lookup table can now be built by joining the factory parquets — no LFS, no shapefiles, no this-repo mapper run needed. The platform-level mapping divergence (centroid in factory vs area-majority here) no longer exists. See `docs/cross_repo_integration_report.md` and ADR-011 assessment §10. |

---

### D-07: Historical data route — keep pipeline-core dispatcher vs call datafactory directly

| Field | Value |
|-------|-------|
| ID | D-07 |
| Source | `expert-code-review` (2026-06-12) |
| Perspectives | Ousterhout/Hickey: the postprocessor uses ~20% of `ViewsDataLoader`'s services (it passes `use_saved=False, validate=False, self_test=False`) while paying 100% of the seven-hop indirection — call `datafactory_query.load_dataset()` directly and own the three renames. Martin/GoF/Feathers: the dispatcher seam absorbed the viewser→datafactory migration with zero consumer changes and will absorb the next one; bypassing it re-couples the postprocessor to the current backend. |
| Location | `views_postprocessing/unfao/managers/unfao.py:44-59`; views-pipeline-core `modules/dataloaders/dataloaders.py:1088-1224` |
| Status | Open. Review recommendation: keep the pipeline-core route, but pass explicit `month_first/month_last` instead of partition semantics, consume `get_data()`'s return value (C-29), and re-enable validation once it supports datafactory sources. Decide alongside ADR-011 since both touch the same manager. |

---

### D-08: Global delivery path — scale up the runtime mapper vs swap to the precomputed lookup first

| Field | Value |
|-------|-------|
| ID | D-08 |
| Source | `expert-code-review` (2026-06-12) |
| Perspectives | Feathers' instinct: the mapper is production-proven and the region change is one config line — don't swap components days before a deadline. Kleppmann/Nygard/Ousterhout: the mapper is *unverifiable at global scale before running it* (C-31: unknown null count, runtime, memory; C-08 newly in scope), while the lookup's complete global failure set is exactly 82 named cells, verified locally (C-30). |
| Location | `views_postprocessing/unfao/managers/unfao.py:154-160`; `mapping.py`; views-datafactory `data/raw/gaul_admin/*.parquet` |
| Status | Open — user decision pending. Review adjudication: **swap to the lookup first, then go global.** The "don't swap before a deadline" rule assumes the old part is known-good for the new job; here it is known-good only for a job 5× smaller and cannot be tested for the new job until the moment it matters. Enumerable risk beats discoverable risk on a deadline. Prerequisite: shadow diff old-vs-new on africa_me (13,110 cells) on the production machine. |

---

### D-09: Multi-store support — parameterize the manager now vs after the FAO global delivery

| Field | Value |
|-------|-------|
| ID | D-09 |
| Source | `expert-code-review` (2026-06-12) |
| Perspectives | GoF: the manager is being touched anyway — extract the `DeliveryProfile` now while context is loaded. Beck/Hickey/Ousterhout: the smallest change that delivers wins; a profile refactor adds review surface to the highest-stakes week, and frameworks built under deadline pressure rot. |
| Location | `views_postprocessing/unfao/managers/unfao.py:109-122, 234-247, 272` |
| Status | Open. Review adjudication: **after delivery** — with two exceptions to do now: delete the dead config blocks (`unfao.py:80-107`, a mis-uncomment hazard) and ensure nothing added this week hardcodes additional store identity. The `DeliveryProfile` itself is a calm 1-day job the following week (C-33). |

---

### D-10: The 82 GAUL-uncovered cells — exclude, crash, or negotiate with FAO

| Field | Value |
|-------|-------|
| ID | D-10 |
| Source | `expert-code-review` (2026-06-12) |
| Perspectives | Fail-loud purism: let validation crash and force the conversation — never silently drop cells. Pragmatic exclusion: drop with a named, count-asserted, logged exclusion list. Diplomatic: ask FAO before shipping anything. |
| Location | `views_postprocessing/unfao/managers/unfao.py:188-221`; the 82 gids enumerated in C-30 |
| Status | **Resolved direction (2026-06-12): fix upstream in views-datafactory.** User decision, superseding the review's exclusion-list adjudication. A new bundled curated region (`land ∩ gaul0_code != -1`, 64,736 cells — e.g. `land_gaul`) is added to `datafactory_query` alongside `land` and `africa_me_legacy`, with generation script, provenance, and a count-pinning test. The postprocessor keeps zero spatial knowledge; its invariant simplifies to "every arriving cell must enrich completely — any null crashes" (the existing `_validate()` gate, unchanged). The `land` region itself is NOT redefined (other consumers depend on its physical-land semantics). Forecast-path residual: unmatched gids null→crash via left merge + validation; pin with one test. FAO disclosure of the 82 excluded sub-Antarctic cells still required in the release note. Closes the postprocessor side of C-30; C-34's coverage test becomes "100% completeness for the configured region." |

---

---

## Resolved Concerns

### C-41: Vestigial Git LFS config breaks routine git operations (no git-lfs installed) — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-41 |
| Resolved | 2026-06-24 |
| Resolution | Retired Git LFS (C-41 fix, this PR): removed the all-shapefile `.gitattributes` LFS rules (matched zero files after C-39) and unwired the local LFS filter config + the four `.git/hooks` LFS hooks. Verified: `git commit`/push now run with no `--no-verify` and no `git-lfs: not found` error. No LFS-tracked files remain in the repo. |

---

### C-10: Manager-to-Mapper coupling via module-level global state — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-10 |
| Resolved | 2026-06-24 |
| Resolution | The `PriogridCountryMapper` runtime mapper was deleted (C-39, PR #42); the module-level `_DEFAULT_MAPPER` global and `get_default_mapper()` coupling this concern describes no longer exist (the manager now uses `GaulLookupEnricher`). |

---

### C-04: Inconsistent forward/reverse mapping breaks expected bijection — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-04 |
| Resolved | 2026-06-24 |
| Resolution | The `PriogridCountryMapper` runtime mapper was deleted (C-39, PR #42); the code this concern describes no longer exists. |

---

### C-02: Module-level side effect blocks package import on shapefile failure — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-02 |
| Resolved | 2026-06-24 |
| Resolution | The `PriogridCountryMapper` runtime mapper was deleted (C-39, PR #42); the code this concern describes no longer exists. |

---

### C-05: Multiple methods crash when disk caching is active — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-05 |
| Resolved | 2026-06-24 |
| Resolution | The `PriogridCountryMapper` runtime mapper was deleted (C-39, PR #42); the code this concern describes no longer exists. |

---

### C-06: Massive code duplication across disk/memory cache branches — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-06 |
| Resolved | 2026-06-24 |
| Resolution | The `PriogridCountryMapper` runtime mapper was deleted (C-39, PR #42); the code this concern describes no longer exists. |

---

### C-11: PriogridCountryMapper is a god class bridging 3 architectural concerns — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-11 |
| Resolved | 2026-06-24 |
| Resolution | The `PriogridCountryMapper` runtime mapper was deleted (C-39, PR #42); the code this concern describes no longer exists. |

---

### C-12: Silent wrong-country assignment when geometry intersection fails — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-12 |
| Resolved | 2026-06-24 |
| Resolution | The `PriogridCountryMapper` runtime mapper was deleted (C-39, PR #42); the code this concern describes no longer exists. |

---

### C-14: Stale disk cache returns outdated mappings after shapefile update — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-14 |
| Resolved | 2026-06-24 |
| Resolution | The `PriogridCountryMapper` runtime mapper was deleted (C-39, PR #42); the code this concern describes no longer exists. |

---

### C-16: Thread-unsafe caches under concurrent enrichment — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-16 |
| Resolved | 2026-06-24 |
| Resolution | The `PriogridCountryMapper` runtime mapper was deleted (C-39, PR #42); the code this concern describes no longer exists. |

---

### C-17: Implicit column naming contract between mapper and manager — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-17 |
| Resolved | 2026-06-24 |
| Resolution | The `PriogridCountryMapper` runtime mapper was deleted (C-39, PR #42); the code this concern describes no longer exists. |

---

### C-20: ZeroDivisionError on degenerate zero-area cells — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-20 |
| Resolved | 2026-06-24 |
| Resolution | The `PriogridCountryMapper` runtime mapper was deleted (C-39, PR #42); the code this concern describes no longer exists. |

---

### C-21: Batch enrichment failures produce incomplete DataFrames (observability-only fix) — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-21 |
| Resolved | 2026-06-24 |
| Resolution | The `PriogridCountryMapper` runtime mapper was deleted (C-39, PR #42); the code this concern describes no longer exists. |

---

### C-39: Dead geopandas runtime mapper + 1.3 GB shapefiles — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-39 |
| Resolved | 2026-06-24 |
| Resolution | Deleted the dead mapper cluster on branch `chore/remove-dead-geopandas-mapper`: `unfao/mapping/` (3,171 lines), the 1.3 GB `shapefiles/` bundle, the mapper tests + `conftest.py`, the two ADR-011 diff scripts, and the CIC — **45 files / ~5,069 deletions**. **geopandas + shapely are now gone from the codebase** (zero references); `cachetools` dropped from pyproject (mapper-only). Verified: deletion broke nothing (keep-tests green). **Dissolves the old-mapper concern cluster** — C-02, C-05, C-06, C-11, C-12, C-14, C-16, C-17, C-19, C-20, C-21 and D-01, D-02 describe code that no longer exists; they are superseded by this deletion and should be relocated to Resolved in a register-curation pass. (C-08's high-latitude-area note also dies on the mapper side; its datafactory dimension stays under C-31.) |

---

### C-01: Silent upload of incomplete geographic metadata to UN FAO — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-01 |
| Resolved | 2026-06-02 |
| Resolution | Re-enabled null validation in `_validate()`. Nulls logged at ERROR and raise `ValueError`. |

---

### C-18: Global warning suppression hides correctness signals — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-18 |
| Resolved | 2026-06-02 |
| Resolution | Removed `warnings.filterwarnings("ignore")` from module scope (line 26). Replaced with targeted `warnings.catch_warnings()` in `_load_priogrid()` scoped to the CRS centroid warning only. All other Python warnings are now active process-wide. D-03 decision applied to code. |

---

### C-36: Permanently-red test suite makes the CI/ship-it gate unable to detect new regressions — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-36 |
| Resolved | 2026-06-22 |
| Resolution | Converted the 43 permanently-failing tests to `xfail(strict=True)` so the suite is green-when-healthy: **119 passed / 43 xfailed / 0 failed**. The 40 falsification probes carry module-level `pytestmark` (plus a per-function mark on `r3_03`); the 3 cross-repo gates in `test_datafactory_deploy_readiness.py` are `xfail(strict)` tracked upstream as **views-datafactory#223** (provenance omits `admin_digest` → stale served grid) and **views-datafactory#224** (development version `1.3.0` collides with released tag). A real regression now surfaces as a `failed` (distinct from the expected xfails), and any probe/gate that *starts passing* flips to a strict failure forcing promotion. Residual (accepted): the pure-`assert False` probes don't test the live condition, so a fixed finding won't auto-flip — inherent to marker-style tests; the deploy gates, being conditional, do auto-flip. |

---

## Resolved Disagreements

### D-01: Cache strategy refactoring — extract now vs. characterize first — RESOLVED

| Field | Value |
|-------|-------|
| ID | D-01 |
| Resolved | 2026-06-24 |
| Resolution | The `PriogridCountryMapper` runtime mapper was deleted (C-39, PR #42); the code this concern describes no longer exists. |

---

### D-02: Thread safety fix — lock caches vs. remove threading — RESOLVED

| Field | Value |
|-------|-------|
| ID | D-02 |
| Resolved | 2026-06-24 |
| Resolution | The `PriogridCountryMapper` runtime mapper was deleted (C-39, PR #42); the code this concern describes no longer exists. |

---

### D-03: Warning suppression — RESOLVED

| Field | Value |
|-------|-------|
| ID | D-03 |
| Resolved | 2026-06-02 |
| Resolution | Beck/Ousterhout consensus applied to code: targeted `warnings.catch_warnings()` for CRS centroid warning only. Global suppression removed. |

---

### D-04: Geometry correction — RESOLVED

| Field | Value |
|-------|-------|
| ID | D-04 |
| Resolved | 2026-06-02 |
| Resolution | Kleppmann/Feathers consensus applied to code: `make_valid()` called in `_load_and_preprocess_naturalearth`, `_load_priogrid`, `_load_admin_data`. |

---

### D-06: C-24 schema divergence — RESOLVED

| Field | Value |
|-------|-------|
| ID | D-06 |
| Resolved | 2026-06-03 |
| Resolution | **Possibility B confirmed.** Investigation of views-faoapi (`/home/simon/Documents/scripts/views_platform/views-faoapi/`) shows that `FAOApiManager` downloads from Appwrite, wraps in `FAO_PGMDataset`, and serves via HTTP with NO column renaming. `dataframe_to_dict()` (api.py:182-191) passes columns through as-is. `_METADATA_COLS` in handlers.py:1146-1156 lists the postprocessor's exact column names. The column renaming from postprocessor names to FAO contract names (Release Note 01 Topic C) was never implemented. FAO receives `country_iso_a3`, `admin1_gaul1_code`, `pg_xcoord` — not UN M49, `ADM1_CODE`, `lat`. This is a genuine schema mismatch between contract and implementation, but it is NOT this repo's responsibility to fix — the renaming belongs in views-faoapi. The postprocessor should keep its current column names. |

---

## Register Conventions

- **ID format:** `C-xx` for concerns, `D-xx` for disagreements. IDs are permanent — gaps in numbering indicate merged or resolved entries
- **Sources:** `repo-assimilation`, `expert-review`, `test-review`, `falsification-audit`, `clean-architecture-review`, `pr-review`, `tech-debt-audit`, `incident`, `manual`
- **Resolution:** Move to "Resolved Concerns" or "Resolved Disagreements" with date and summary
- **Header counts:** Manually maintained — update whenever a concern is added or resolved
- **Governed by:** ADR-010
