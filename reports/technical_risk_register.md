# Technical Risk Register

| Register Info     | Details                              |
|-------------------|--------------------------------------|
| Project           | views-postprocessing                 |
| Owner             | Dylan Pinheiro / PRIO MD&D Team      |
| Last Updated      | 2026-07-19                           |
| Total Concerns    | 47                                   |
| Open Concerns     | 26                                   |
| Resolved Concerns | 21                                   |

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
**✅ MOSTLY RESOLVED 2026-06-24:** the mapper deletion (C-39) removed the `mapping.py` error-hiding sites — **C-12, C-20, C-21 are resolved**, and the remaining ◻ fix-strategy items (geometry-error log level, exception-scope narrowing, `logger.error` before `mapping.py` raises) describe deleted code and are **moot**. Only the manager-side residue remains: **C-19** (3 `unfao.py` raises) and **C-22** (post-delivery correction process).

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

**Update 2026-06-24 (narrowed):** the `mapping.py` dimension is gone (C-39 — the `geopandas`/`shapely`/`joblib`/`multiprocessing` imports were deleted; `cachetools` dropped from `pyproject.toml`). Residual: `unfao.py` imports `pandas`/`polars`/`python-dotenv` undeclared, arriving transitively via `views-pipeline-core` (which *is* declared). Much smaller surface (Tier 4-ish); consider resolving outright if the transitive-via-pipeline-core guarantee is deemed sufficient.

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

**Update 2026-06-24 (narrowed to the datafactory dimension):** this repo's mapper area-math (`mapping.py:649-650,920,1192,1428`) is deleted (C-39); no degree-based area math runs in this repo anymore. The remaining concern is the **views-datafactory** area-majority script's degree-based area math at high latitudes — a cross-repo views-datafactory concern (this repo now consumes the lookup built from those parquets, so any distortion is upstream). Tracked there, not here.

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

**Mitigation landed (S5, 2026-06-26, `sprint/fao-input-integrity`):** a representation-free `delivery/provenance.py` (`build_provenance`) assembles structured provenance — `lookup_version`, `region`, `expected_cell_count`, `actual_cell_count`, `unmapped_count` — sourced from the enricher + S1 coverage + a new `extraction.unmapped_cell_count` seam (nothing hardcoded). Both `_save` uploads now carry it via `_delivery_description`. **Carrier constraint:** pipeline-core's `upload_data` exposes **no structured field** — only free-text `description` — so the dict is JSON-encoded into `description` behind a human prefix for now. A dedicated metadata field is requested upstream (**pipeline-core #245**); when it lands, only the manager's attach step changes (the provenance shape is already representation-free). `fill_count` is omitted until a fabricated-value count is available (cf. C-26). Residual is now just the carrier abuse, tracked by #245.

See also C-14 (stale cache without version tracking), C-22 (no post-delivery correction process), C-26 (fabricated zeros — the eventual `fill_count` source).

---

### C-19: Systematic ADR-008 non-compliance — 23 of 24 raises lack preceding log — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-19 |
| Resolved | 2026-06-28 |
| Resolution | Every live-path structural raise now logs-before-raise. The mapper portion (20 raises) went with the deleted runtime mapper (C-39); the 3 `unfao.py` manager raises were fixed in #13; and the residual `enrichment.py` (`:42,:50,:103`) + `extraction.py` (`:39`, a module logger was added) raises got `logger.error`-then-raise in the tech-debt-cleanup pass (2026-06-28). The only raises now lacking a preceding log are in `unfao/frames.py` (the views-frames conformance adapter), which is **not on the live delivery path** and is tracked separately by **C-45**. ADR-008 compliance holds across the live path. |
| Tier | 3 |
| Source | `falsification-audit` (2026-06-02) |
| Trigger | When a structural failure occurs in `GaulLookupEnricher` (lookup missing/incomplete, or an absent gid column) or in the `extraction` seam and the operator searches logs for context, verify the exception was preceded by a `logger.error` — these raises currently have none |
| Location | `views_postprocessing/unfao/enrichment.py:42,50,103`; `views_postprocessing/unfao/extraction.py:39` |

ADR-008 requires structural failures to be both logged persistently AND raised explicitly. Three validation methods in mapping.py and the C-01 fix in unfao.py were fixed with log-before-raise. 20 raises in mapping.py and 3 in unfao.py remain unfixed.

Part of Cluster B (expanded scope).

**Update 2026-06-24:** the mapper portion (20 of the 23 raises, in `mapping.py`) is gone with the deleted runtime mapper (C-39); the **3 raises in `unfao.py`** remain (tracked by issue #13). Narrowed to the manager.

**Update 2026-06-28 (re-scoped after `review-base-docs`):** the `unfao.py` residual is **resolved** — the 3 manager raises got log-before-raise in #13 (`unfao.py:72,84,293`), and the `FileNotFoundError` at `:112` is logged by its enclosing `_read_forecast_data` try/except. So both historical locations (mapper, manager) are now clear. **The live ADR-008 residual moved to two modules the original audit never covered:** `enrichment.py` (`:42` lookup-missing, `:50` lookup-missing-columns, `:103` absent gid column) and `extraction.py:39` (the seam's index/column `KeyError`) — these raise without a preceding `logger.error`. Practical risk is low (the raises are loud, not swallowed — the messages are descriptive); the gap is uniform log-before-raise convention in live code. Tier 3 (observability/maintainability, no silent corruption). *(This residual was then fixed the same day — see the Resolution field above.)*

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

**Mitigation landed (S3, 2026-06-26, `sprint/fao-input-integrity`):** `_read_forecast_data` now resolves the file id, fetches its metadata, and asserts identity (`delivery/identity.assert_forecast_identity`) against the configured ensemble (`{name: ensemble_path_manager.model_name, loa: "pgm"}`) **before** download — a stray `category="forecast"` upload now fails loud instead of shipping silently. **Residual (verify before relying on it):** the guard assumes the producer's uploaded `name`/`loa` equal `model_name`/`"pgm"`; this is checked against pipeline-core's code but **not a live Appwrite upload**. If the contract differs, the guard fails loud on *every* run — caught at the first smoke-test delivery (option A / S6 #57), **not** silently — so the residual is an availability / false-positive risk, not a corruption one. Confirm the field match at the option-A run; until then C-25 stays open.

See also C-13 (no timeout on the same calls), C-15 (upload metadata lacks provenance to detect this downstream), C-43 (the same "verify at the first live run" debt pattern on the enrichment swap).

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

Verified 2026-06-12: of the datafactory's 64,818 `land`-region cells, 64,736 have complete area-majority metadata; exactly 82 are unassigned across all 7 GAUL fields — all remote sub-Antarctic islands FAO's GAUL 2024 boundaries do not cover (Macquarie, Auckland Islands, Prince Edward; sample gids 51078, 51798, 53979, 62356, 94776, 99027). The mitigation must be a named exclusion-list constant with the gids, count-asserted in both the enricher and a test, logged at WARNING, and disclosed to FAO — not a generic `code != -1` filter, which would silently absorb future coverage regressions. Generalizes the previously documented "5 ocean cells" of africa_me_legacy (those 5 are among the excluded set).

**Count drift corrected 2026-06-26 (the frozen-list tripwire working as designed):** deriving the exclusions from the live producer (datafactory **v1.4.0**) gives **64,742** complete + **76** excluded, *not* the 64,736 / 82 verified on 2026-06-12. Cause: datafactory **#163 (ADR-043)** supplemented **6 Azorean cells** (gids 182470, 183190, 183909, 183910, 186058, 186778) into `land_gaul` — they are now covered, not excluded. vpp's *own* built lookup (`data/gaul_lookup.parquet`) already ships 64,742, so the old 64,736 pin would have false-positived against our own artifact. NB the authoritative exclusion source is the **region complement** `land − land_gaul` (76), not the raw `gaul0_code == -1` (82) — the latter does not reflect the ADR-043 curation.

**Mitigation landed (S4, 2026-06-26, `sprint/fao-input-integrity`):** the 76 excluded gids are pinned as a frozen manifest in `delivery/coverage.py` (`EXCLUDED_GIDS_BY_REGION`), the count is corrected to 64,742, `assert_no_excluded_cells` is wired into the manager's `_check_coverage` **region-gated** (a no-op for unpinned `africa_me_legacy`, so its 5 ocean cells are unaffected), the 76 are disclosed in `docs/fao_excluded_cells.md`, and a test cross-checks the manifest against the datafactory sibling when present (drift tripwire). **Residual:** still Tier 1 until the live `land_gaul` run (views-platform/views-models#127) exercises it end-to-end — the guard is unit-proven but not yet run against a real global delivery.

See also D-10 (handling decision), C-34 (coverage contract).

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

**Update 2026-06-24 (reframe — now near-term, not deferred):** this is no longer a someday concern. FAO (`rusty_bucket`) sidesteps reconciliation entirely (pure-grid ensemble aggregated *up* — sums by construction), but the **next UN-agency deliverable** is an FAO-like grid ensemble that **does** reconcile against a CM model, with **full pooled draws (~1024)** → **probabilistic** reconciliation. The reconciler is already probabilistic-ready (fully vectorized over samples), so the open question is purely C-37's: does that deliverable reconcile grid draws to a country **point total** (well-defined, no alignment needed) or to country **draws** (needs a defined draw-alignment — and today CM models are point-only / independently trained, so no aligned draws exist)? **This decision gates the probabilistic-reconciliation-on-`PredictionFrameEnsembleManager` work** (pipeline-core#200, under epic #193); resolve it once the UN models / CM target are defined.

**Calibration note (review-rr 2026-06-24):** stays **Tier 3 while unwired**, but **escalate to Tier 2 the moment reconciliation is wired into a delivery** — at that point a wrong sample-alignment assumption silently delivers *meaningless uncertainty* (a correctness risk, not maintainability). The wiring (pipeline-core#200) is the escalation trigger.

**Update 2026-06-26 (home change):** the reconciler (`proportional.py`, `grouping.py`, `module.py`) is relocating from this repo to the **`views_frames_reconcile` sibling** in the views-frames distribution (Epic 11, views-platform/views-frames#131) — its correct foundation home (CRP/SDP: a frame operation belongs in the frames family, not bolted onto FAO delivery). **C-37 and C-38 move with it** — track them in views-frames going forward. vpp's copy is deleted in #62 once views-frames v1.7.0 ships (release → repoint views-models#191 → delete).

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

**Update 2026-06-24 — compute RESOLVED.** The per-group `np.nonzero(inverse == gi)` was replaced with **group-by-sort** (`argsort(inverse)` + contiguous slices from `np.unique` counts, O(N log N), one index array). Parity stays **bit-exact** (`tests/test_reconciliation_grouping.py`, `test_reconciliation_e2e_parity.py` → 0.0) and a scale guard (`tests/test_reconciliation_scale.py`) protects against regression. **Residual (relocated with the code):** the module holds the whole pgm frame in memory at once; at global volume the **caller must chunk by time** (reconciliation is independent across months). The reconciler — and this chunk-by-time obligation — **left vpp**: the algorithm now lives in `views_frames_reconcile` and the vpp `ReconciliationModule` CIC was retired (#62 / PR #63, merged to `development` 2026-06-26). The global-volume verification is now a **consumer-side obligation at reconciliation-wiring time** (pipeline-core#200/#221), not a vpp concern. Tracked cross-repo via C-42; no further vpp action.

**Update 2026-06-24 (reframe — residual now near-term):** the memory residual is no longer "verify someday." The upcoming UN-agency deliverable reconciles **frames with ~1024 pooled draws** — squarely in the >100 GB-at-global regime. When pipeline-core's `PredictionFrameEnsembleManager` wires probabilistic reconciliation (pipeline-core#200, under epic #193), the **caller must chunk by time** (reconciliation is independent across months) and **measure peak memory on a global-volume dry-run** as part of that work. The reconciler code itself is unchanged (compute already O(N log N)); this is a consumer-side obligation.

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

**Priority raised by the samples/uncertainty requirement (2026-06-27).** The delivery is moving from point estimates to **predictions-with-uncertainty (S samples per cell)**. This makes the pandas gate (consequence b) materially worse, not just cosmetic:
- **views-frames** stores a distribution as a native contiguous `(N, S)` float32 array (sample axis always explicit; point = S=1). **pandas `PGMDataset`** stores it as **object-dtype list-in-cell** — each of N cells holds a separate length-S numpy array (`_ViewsDataset._convert_to_arrays` / `_check_prediction_samples` in pipeline-core `data/handlers.py`).
- Cost of the object-dtype representation scales ~linearly with S: memory blow-up (this is pipeline-core's own OOM, **#181/#189** — "~18 GB, kills runs" off list-in-cell DataFrames), an encode/decode tax at every parquet/API boundary (faoapi's inverse `_convert_to_arrays`), and a silent `np.resize` pad on mismatched sample counts (feature path).
- At S=1 the penalty is invisible; at S≈1000 it dominates → the uncertainty work is the strongest driver for the frame migration.

**Concrete pipeline-core gate (what "DataFrame retirement" actually requires).** vpp inherits three *concrete* pandas pieces (the abstract `PostprocessorManager` base is fine): the input loader (`ViewsDataLoader.get_data` → parquet→pandas), the container (`PGMDataset`/`_ViewsDataset`, object-dtype cells), and the prediction-store parquet I/O. Closing the gate = pipeline-core **Epic #186 + #207** landing: frame-native input loader (**#161**, gated on the datafactory↔core output contract **#162/#136**), a frame container replacing/re-backing `PGMDataset` (**#159**), frame/arrow store I/O, and retiring the legacy pandas report path (**#211**, the #181 OOM source). It is an epic, not a PR. The half **vpp owns and can do now** (unblocked): the thin-shell de-inheritance above — extract enrich/validate into a pipeline-core-free core the manager *calls*, so the eventual frame swap is a one-seam change. Dependency direction confirmed: pipeline-core does **not** import vpp; vpp **is-a** pipeline-core postprocessor (Template-Method subclass), so it inherits pipeline-core's representation rather than choosing its own.

**Migration backlog (2026-06-28):** the full pandas→views-frames map + sequenced, parity-preserving removal plan is now tracked as epic **#85** ("Push pandas to the seams") with stories #86–#92 and tracking #93. The unilateral arc (S1–S3: generalize `frames.py` to S>1, frame-native extraction siblings, forecast convert-at-the-door) makes vpp's interior carry `(N,S)` behind frozen wires; S6 (#91, outbound arrow wire) is gated on faoapi #45, and S7 (#92, historical inbound) is gated on this entry's pipeline-core gate above.

**Wire contract posted (2026-07-03) — the S6/#45 circular wait is dissolved.** A three-way audit (pipeline-core / producers / consumer+substrate, all on `origin/development` + maintainer-authored issues) established: (i) there are **two wire hops** (producer→store; vpp→faoapi) and the roadmap's arrow work covered only the second; (ii) **no publish path from PFE to the prediction store exists at all** — models#143's "no pipeline-core change required" is **falsified** (PFE's `use_prediction_store` is stored then only logged, `prediction_frame_ensemble.py:141/:799`; `PredictionIOManager._upload_to_prediction_store` raises `NotImplementedError`, `io.py:117`); (iii) full global draws ≈ **9.5 GB/target**, so the wire mandates per-month sharding; (iv) the "platform ADR-046" cited as the format authority **does not exist** (phantom). **ADOPTED 2026-07-15 as ADR-013** *(post-adoption: F1 invisibility confirmed live — six stranded orange_ensemble forecast docs in unfao_bucket, forecast serving has been empty all along; both §11.4 legacy guards merged same day, Hop-B guard must reach production before vpp's first contract upload — faoapi C-161)* after five reviewed iterations (two seat reviews, reconciliation, owner-ratified F1) — maintainer sign-off on views-models#149. The v1 proposal history: Hop A = Track A zip archive per (run,target,month) + manifest-last commit marker (new **pipeline-core#269**); Hop B = per-month `views_frames.io.arrow` (#91/faoapi#100); interior = per-target 2-D `PredictionFrame`; the 9 GAUL columns move to a **gid-keyed sidecar**; the **#149 no-collapse boundary is named: vpp `delivery/draws.py`** (a new invariant, sibling of coverage/identity — follow-on vpp work with the durable vpp ADR after explicit sign-off); target vocabulary **decided: `lr_ged_sb/ns/os`**, producers rename at publish (models#146).

See also C-07/C-27/C-29 (pipeline-core coupling symptoms), C-39 (the dead-mapper cleanup that precedes any unfao restructuring), **#45** (the delivery-side draw carrier — ship `(N, S)` uncollapsed as a native frame, the producer half of this same problem), and **epic #85** (the migration backlog).

---

### C-42: Reconciliation migration is stranded across three repos; production runs the old path and the migration-state was mis-stated

| Field | Value |
|-------|-------|
| ID | C-42 |
| Tier | 3 |
| Source | `manual` (2026-06-26) — cross-repo verification on `origin/development` |
| Trigger | When a cross-repo agent next acts on reconciliation (merges pipeline-core PR #217, repoints any consumer, **deletes vpp's copy**, or builds a new reconciliation feature), confirm which copy it targets against `origin/development` first — do **not** assume #217 is merged, the cycle is broken, or vpp's copy is unused (views-models imports it live; deletion is hard-gated on C1) |
| Location | pipeline-core `origin/development`: `managers/ensemble/ensemble.py:747`, `managers/ensemble/dataframe_ensemble.py:921`, `modules/reconciliation/__init__.py:4` (live `views_reporting.reconciliation` imports); `views-models/reconciliation/reconciler_factory.py:54` (**unguarded live import of `views_postprocessing.reconciliation`** — ADR-014 composition root); `views_postprocessing/reconciliation/` (parity-proven, **consumed by views-models**); the plan file + issue #39 (carried the false "merged" premise) |

Verified 2026-06-26 on `origin/development`: pipeline-core **still imports `views_reporting.reconciliation`** (3 sites above) — the pipeline-core↔views-reporting reconciliation **cycle is live**, and production reconciliation still runs through views-reporting (torch). **PR #217** (the DIP port + adapter that would decouple it, #195) is **OPEN/unmerged** — the port `domain/reconciliation.py` exists on dev but the adapter does not. So **three reconciler copies are in flight**: views-reporting (live via pipeline-core), vpp (parity-proven, PR #30), views-frames (now SHIPPED — v1.7.0 on PyPI 2026-06-26).

**CORRECTION 2026-06-26 (exploration-verified): vpp's `reconciliation/` is NOT "unused/stranded."** `views-models/reconciliation/reconciler_factory.py:54` does an **unguarded** live import `from views_postprocessing.reconciliation import ReconciliationModule` (the ADR-014 composition root, constructed at runtime by reconciling ensembles). The earlier "unused by any production consumer" wording here was wrong — and it was itself an instance of this entry's own hazard (state-drift that could prompt an unsafe action). **Deletion-safety consequence:** deleting vpp's `reconciliation/` **hard-breaks views-models** unless C1 (repoint views-models → `views_frames_reconcile`) lands and goes green **first**. All other importers are guarded (`pytest.importorskip`): views-frames `test_reconcile_head_to_head.py`, views-models `test_reconciliation_factory.py`. pipeline-core / views-reporting do not import vpp. The hazard remains **acting on a false state** (e.g. merging the throwaway #217 port, or deleting a copy that is in fact a live dependency). No silent data corruption (the production path works; it is just the old one) → **Tier 3** (coordination / state-drift / cost-of-change).

**Mitigation:** do **not** merge #217 as a throwaway bridge. The "release" leg is complete (v1.7.0 on PyPI). Cutover order: **repoint** (views-models#191 = C1; pipeline-core#221 = collapse the port, parallel) → **delete** (vpp #62 = C2, only after C1 green) → retire views-reporting reconciliation (vpp #40 / views-reporting#72, after #221).

**Update 2026-06-26 (cutover landed — the mis-stated-state hazard has resolved):** all three legs are done and verified on `origin/development`. **release** — views-frames v1.7.0 on PyPI. **repoint** — views-models **PR #202** merged (`reconciler_factory.py` imports `views_frames_reconcile`); **pipeline-core chose Decision K, not C** — **PR #217 merged** (`6427b9d`): it reconciles via its `Reconciler` DIP port with `views_frames_reconcile.ReconciliationModule` injected (the C-cutover issue #221 was closed unused). **delete** — vpp's copy removed in **#62 / PR #63** (merged to `development`, `c9e38402`). A full cross-repo sweep confirms no unguarded importer of `views_postprocessing.reconciliation` anywhere. The original hazard (acting on a *mis-stated* migration state) is **resolved** — every actor was verified against `origin/development` before acting. **The one residual is split out as C-43:** pipeline-core still imports `views_reporting.statistics.ForecastReconciler`, so the pipeline-core↔views-reporting edge is not fully severed and views-reporting retirement (#40 / views-reporting#72) is still blocked. This entry can move to **Resolved** once C-43 is filed (it is); kept open here only pending a /review-rr relocation.

See also C-37 / C-38 (the reconciler concerns — relocating to views-frames with the code), views-platform/views-frames#131 (the final home), #62 (retire vpp's copy), views-platform/views-models#191 (repoint), pipeline-core PR #217 (the merged DIP port, Decision K).

**Residual tail (verified 2026-06-26 — already tracked cross-repo, no new vpp entry):** pipeline-core still imports `views_reporting.statistics.ForecastReconciler` (`modules/statistics/__init__.py:5`), so the pipeline-core↔views-reporting edge is not yet fully severed and views-reporting's `reconciliation/` + `torch` retirement (#40 / views-reporting#72) is still blocked. But this is **not an untracked hazard**: the re-export is explicitly marked *"remove after downstream consumers update"*; `ForecastReconciler`'s only pipeline-core consumers are the transitional **golden-output equivalence tests** (#119 / #196, "new frames-native == old torch"); and **pipeline-core #198** already owns the removal — its scope note names *"the `reconciliation/` package **and** the `ForecastReconciler` class"* and it triggers vpp **#40** / views-reporting#72. Blocked on pipeline-core #197 (views-postprocessing/views-frames must be "default and stable") first. So C-42 stays open as a thin tracker until #198 lands; no separate vpp entry warranted (would duplicate #198). *(A speculative residual-coupling entry was drafted then withdrawn here after verification showed it was a duplicate of pipeline-core #198.)*

---

### C-43: ADR-011 enrichment swap shipped without its output-equivalence proof — and the proof is now unrecoverable

| Field | Value |
|-------|-------|
| ID | C-43 |
| Tier | 2 |
| Source | `manual` (2026-06-26) — user-flagged rigor loss on accepting option A; verified against git history (`eba1df8` / PR #42) |
| Trigger | When the `africa_me_legacy` smoke-test delivery (option A) is accepted as the swap's verification, and — more acutely — when Stage 4 flips the region to `land_gaul` (64,736 cells, views-platform/views-models#127): the go-global run is the first time the lookup enricher's output reaches FAO at scale with **no** equivalence check against the previously-trusted mapper. Also fires if FAO / faoapi reports geographic metadata that looks wrong for specific cells. |
| Location | `views_postprocessing/unfao/enrichment.py` (`GaulLookupEnricher`); `views_postprocessing/unfao/managers/unfao.py:129` (`_append_metadata`), `:147-172` (`_validate` — the 9-column NULL gate, checks presence not correctness); umbrella #20 / issues #21, #23, #24 (the baseline+diff procedure, now unrunnable); deleted in `eba1df8` (PR #42): `mapping.py` + both ADR-011 diff scripts |

ADR-011 swapped FAO geo-enrichment from the runtime geopandas mapper to the GAUL lookup enricher (commit `65635b6`). The swap's own plan (umbrella #20) required an **output-equivalence proof** before trusting it in production: Stage 0 (#21) run the OLD mapper on real `africa_me_legacy` data to archive a ground-truth baseline; Stage 2 (#23) diff the new enricher against it with *"zero unexplained differences."* That proof was **never produced** — no `baseline_schema.md` or baseline parquet was ever committed — and on 2026-06-24 the old mapper **and both diff scripts** were deleted (`eba1df8`, PR #42, C-39). So the equivalence check is now **unrecoverable** short of `git revert`-ing the mapper back.

The accepted path forward (**option A**) is a single smoke-test delivery: "the run is green and the output looks sane," which proves the path *runs*, not that it produces the *same / correct* values the trusted mapper did. The manager's `_validate` enforces only that the 9 GAUL columns are **non-null** — it does not check value correctness — so a latent bug in the lookup build or the merge-by-gid (wrong join key, stale `lookup_version`, gid misalignment) would ship **wrong-but-non-null** geographic metadata to FAO with **no error signal**.

**Why not Tier 1:** the lookup is built from views-datafactory's authoritative area-majority GAUL parquets — the canonical *producer* source (D-07). The new path sources from the gold standard; the old mapper was the *less*-trusted path being retired (C-31, C-23). So the missing diff is a lost cross-check, not "unverified code," and the Stage-1 enricher unit tests + coverage guards (C-30/C-34) cover part of the build. **Why Tier 2:** the residual silent-wrong-value path is real, the null gate cannot catch it, the one guard that would have is gone for good, and the trigger (go-global to 64k cells) is concrete and imminent.

**Mitigation if assurance is wanted before go-global** (cheaper than reverting the mapper): forward-check a sample of `land_gaul` cell assignments directly against the datafactory GAUL parquet, or add a lightweight value-level assertion into the enricher path (a forward check against the producer source — *not* a resurrection of the deleted old-mapper diff).

See also C-03 (the sibling enrich→validate test-coverage gap), C-22 (no post-delivery correction/recall process — the consequence if wrong values do ship), C-39 / C-31 / C-23 (the resolved mapper-deletion cluster this emerged from), C-30 / C-32 / C-34 (the go-global scale risks where this bites), D-08 (the swap-to-lookup-first decision whose verification debt this is).

---

### C-44: views-pipeline-core 3.0.0 dependency bump is pending and must not land until the platform runs on development across all repos

| Field | Value |
|-------|-------|
| ID | C-44 |
| Tier | 3 |
| Source | `manual` (2026-06-26) — surfaced while consolidating a stranded local commit after the input-integrity sprint merge |
| Trigger | When views-pipeline-core 3.0.0 is published to PyPI **and** the platform is confirmed running smoothly on `development` across all consumer repos — then bump `pyproject.toml` to a reproducible version pin (`views-pipeline-core = ">=3.0.0,<4.0.0"`), re-lock, and PR. Do **not** land the bump before both conditions hold, and do **not** source it from a moving git branch. |
| Location | `pyproject.toml:13` (currently `views-pipeline-core = ">=2.1.3,<3.0.0"`); `poetry.lock` (pins `views-pipeline-core 2.3.0`, a reproducible PyPI wheel); the deferred change preserved on local branch `backup/pipeline-core-3.0.0-git-source` (commit `78d238e`) |

`development` currently pins `views-pipeline-core = ">=2.1.3,<3.0.0"` and the committed `poetry.lock` resolves it to **2.3.0** from PyPI — reproducible, and the merged input-integrity sprint (#64) was CI-proven green against it. **3.0.0 is not yet on PyPI (political hold).** A local-only commit (`78d238e`, authored 2026-06-25 in a separate session, never pushed) repoints the dependency to pipeline-core's **git `development` branch** to track the unreleased 3.x "in tandem with other consumers."

That change was deliberately **not** landed on `development` (2026-06-26), for three reasons: (a) sourcing from a **moving git branch** makes builds **non-reproducible** (the branch advances under us); (b) it is a **major-version switch** (2.x→3.x) whose breaking changes were never exercised against the just-merged sprint code; (c) it would require a **full re-lock** resolving 3.x + its transitive tree, rippling through `poetry.lock`. The maintainer's standing constraint: **the platform must run smoothly on `development` across all repos before taking the major dependency bump.** Until then the bump is premature.

No silent corruption and no current breakage (development is green on 2.3.0) → **Tier 3** (coordination / release-sequencing / reproducibility). The deferred work is preserved (backup branch) and becomes a trivial, reproducible one-line pin once 3.0.0 ships and the cross-repo gate clears. Cross-refs C-40 (the underlying pipeline-core inheritance coupling that makes major bumps high-blast-radius), C-07 (the transitive-via-pipeline-core dependency surface), C-09 (publish-workflow version handling).

---

### C-45: `unfao/frames.py` is an unused views-frames conformance adapter carried on no live path

| Field | Value |
|-------|-------|
| ID | C-45 |
| Tier | 4 |
| Source | `repo-assimilation` (2026-06-27) |
| Trigger | When the C-40 representation migration (pandas → views-frames) begins — confirm whether `frames.py` becomes the live conversion seam or should be removed; or when a contributor assumes it is on the delivery path (its own docstring says it is not) |
| Location | `views_postprocessing/unfao/frames.py` (the only `views_frames` importer); exercised solely by `tests/test_views_frames_conformance.py` |

`unfao/frames.py` (`to_prediction_frame` / `to_target_frame`) converts the repo's pandas tables into views-frames `PredictionFrame`/`TargetFrame` `(N, 1)` value objects to prove they satisfy the published views-frames contract. It is the **only** module importing `views_frames`, and **no live path calls it** — its sole consumer is the conformance test (the module's own docstring states "nothing in the live delivery path calls it yet"). It is forward-looking scaffolding for the C-40 frame migration: harmless, but a maintenance/confusion surface (a reader can mistake it for an active code path, and it hardcodes `S=1`, i.e. point-only, which will need revisiting for the draws/uncertainty work). No correctness or reliability impact → **Tier 4**.

**Partly addressed by S1 (epic #85 / #86, 2026-06-28).** `frames.py` was reworked to the declare-don't-guess design (D-11): it now exposes `build_prediction_frame` / `build_target_frame` over **declared primitives** (a 2-D `(N, S)` array + `(time, unit)`), supports **S>1** (the `S=1` hardcode is gone), is **pandas-free** (no longer the lone pandas importer — it sits alongside `delivery/`), and fails loud rather than inferring/reshaping. So the *S=1-hardcode*, *inference-risk*, and *pandas-coupling* dimensions are resolved. **Residual (entry stays open):** the module is still **not called by the live delivery path** — that wiring is S3 (#88, forecast convert-at-the-door). C-45 resolves when S3 lands (or, if S3 is abandoned, when the module is removed).

See also C-40 (the pandas gate this adapter anticipates), #45 (the draws carrier that will need the `S>1` version), epic **#85** / **#86** (the S1 rework) / **#88** (the S3 wiring that closes this), **D-11** (the declare-don't-guess decision).

---

### C-46: `test_datafactory_deploy_readiness` is hardcoded to a local path — CI-skipped, and currently failing on the one machine that runs it

| Field | Value |
|-------|-------|
| ID | C-46 |
| Tier | 4 |
| Source | `repo-assimilation` (2026-06-27) |
| Trigger | When treating `test_datafactory_deploy_readiness` as a release gate (it never runs in CI), or when a contributor's local `pytest` fails on it — re-promote / re-pin the strict-xfail now that views-datafactory has advanced to `1.5.0`-dev past its `v1.4.0` tag |
| Location | `tests/test_datafactory_deploy_readiness.py` (`_DF = Path("/home/simon/.../views-datafactory")`, `skipif(not _DF.exists())`) |

The cross-repo deploy-readiness gates introduced under C-36 are guarded by `skipif` on a **hardcoded local datafactory checkout path**, so they are **skipped in CI** and only ever execute on one developer's machine. There, `test_version_bumped_past_latest_tag` is currently **failing**: it is an `xfail(strict)` that flipped to XPASS because datafactory moved to `1.5.0`-dev past its `v1.4.0` tag — exactly the auto-flip C-36's resolution anticipated, but because of the hardcoded path the flip surfaces as a **local red** rather than a CI signal, and breaks local `pytest` runs (the suite is run with this test deselected). No correctness/reliability impact on the delivery → **Tier 4** (test hygiene). C-36 (resolved) converted these gates to strict-xfail but did not capture the local-path / CI-skip dimension.

See also C-36 (the resolved strict-xfail conversion this extends), C-44 (the datafactory version-state coupling).

---

### C-47: Stale untracked `reconciliation/__pycache__/` survives the module's retirement and misrepresents the package tree

| Field | Value |
|-------|-------|
| ID | C-47 |
| Tier | 4 — pure hygiene: not importable (no `__init__.py`, no sources), untracked, no correctness or reliability impact; its only effect is misleading humans and tools that inventory the tree |
| Source | `manual` (2026-07-19) — maintainer question "I thought reconciliation had moved out?" during the ADR-013 read-through; directory listing showed a phantom `reconciliation/` package |
| Trigger | When the D-12 repo-rename assessment (or any repo-structure audit / fresh assimilation) next inventories `views_postprocessing/` and takes the phantom `reconciliation/` dir as evidence the module still lives here — as happened in-session 2026-07-19 |
| Location | `views_postprocessing/reconciliation/__pycache__/` (untracked bytecode leftovers; sources deleted in #62 / PR #63, `6af2020`) |

The reconciliation retirement (C-42 cutover leg C2) deleted all tracked sources, but the untracked `__pycache__/` bytecode directory survived on the working machine. Directory listings therefore still show a `views_postprocessing/reconciliation/` package, which already misled one in-session inspection into reporting the migration unfinished. Deletion is a one-liner (`rm -rf views_postprocessing/reconciliation`) deferred by maintainer decision; tracked as a GitHub issue. Resolves on deletion (verify `git status` stays clean and the vpp suite green — trivially expected).

Cross-refs: C-42 (the migration this is residue of), D-12 (the rename assessment it could mislead).

---

## Disagreements

### D-12: Post-Run-0 infrastructure & naming intents — repo rename, internal-store transport, compute co-location

| Field | Value |
|-------|-------|
| ID | D-12 |
| Source | Maintainer direction during the ADR-013 read-through (2026-07-19); assessment in-session |
| Location | Repo-wide (rename); ADR-013 §3/§8 (store transport, co-location); mirrored as dated deferred intents in ADR-013 §8 |

Three maintainer-raised intents, assessed and **deliberately deferred** — all sequenced strictly after (1) Run 0 proves the wire as adopted and (2) a §3.5 retention owner exists (infrastructure ownership must exist before infrastructure multiplies):

1. **Rename this repo** to a delivery-screaming name (e.g. `views-delivery`). The repo is already purely delivery code (reconciliation retired to `views_frames_reconcile`, #62 closed 2026-06-26), so the name is the only mismatch with the screaming-architecture rubric. GitHub redirects soften the repo rename; the `views_postprocessing` *package* rename (cross-repo imports, views-models launchers) is the real churn and may trail.
2. **Move `production_forecasts` off Appwrite** to self-managed storage (e.g. Hetzner object storage) — no external consumer reads the internal store. Contract-tolerant: §3 payload + manifest-last semantics are transport-agnostic; only the store-document addressing needs a bounded amendment.
3. **Co-locate delivery compute with the internal store** to kill the ~29 GB/run upload-download round-trip — while **keeping the logical hop** (complete-or-invisible commit marker, hash verification, schedule independence, multi-partner fan-out). Fusing producer and delivery into one machine is **explicitly rejected** — it would rebuild the coupling ADR-013 dissolved.

**Re-open trigger:** Run 0 verified AND retention owner named — then sequence 2→3 (or 2 alone) as an infrastructure epic, and 1 whenever wire churn is calm. See also C-40 (the migration this rides on), ADR-013 §8.

---

### D-11: Pandas→frames seam — concrete siblings + delete vs a polymorphic abstraction

| Field | Value |
|-------|-------|
| ID | D-11 |
| Source | `expert-code-review` (2026-06-28) — review of pandas-migration epic #85 |
| Location | epic #85 / stories #86 (`unfao/frames.py`), #87 (`unfao/extraction.py` + new frame module), #88/#91 (`unfao/managers/unfao.py` source/sink seams) |

The pandas→views-frames migration (epic #85) deliberately swaps each seam by adding a **concrete** frame-native sibling next to the pandas one and later **deleting** the pandas path — rather than introducing a polymorphic abstraction (an `Extractor` Protocol / a representation port) that both implementations satisfy.

- **Position A — concrete siblings + delete (the plan's choice; Martin/Beck-pragmatic, WET-before-DRY).** pandas and frames do **not** coexist at runtime — it is a migration, not a permanent dual representation — so a polymorphic interface would be speculative (YAGNI/ISP: don't force an interface nobody dispatches on). The seam stays readable, each representation is one-concept-per-file, and retirement is a clean file-delete. The invariants already depend on **primitives** (the real abstraction, DIP-satisfied at that boundary), so no port is needed above them.
- **Position B — abstraction/port (Hickey/strict-OCP).** Depending on a representation port would make the swap "extend, not modify," and would let the two paths coexist cleanly during cutover.

**Decision: A**, consistent with the maintainer's WET-before-DRY rule and the "migration not coexistence" reality. **Re-open trigger (the one acute case):** S6 (#91) introduces a temporary **dual-write** (legacy parquet + arrow sample-frame) for parity during the faoapi cutover — *if that coexistence proves long-lived* (rather than a brief cutover window), a small abstraction may then earn its place; revisit only then. Until then, concrete-and-delete stands.

See also C-40 (the inheritance/representation coupling this migration unwinds), #85 (the migration epic), #45 (the faoapi wire / S6 dual-write).

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

## Resolved Concerns

### C-35: Invalid `-99` country code shipped to FAO for Somaliland cells — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-35 |
| Resolved | 2026-06-24 |
| Resolution | The mapper that sourced `country_iso_a3` from Natural Earth (emitting the `-99` sentinel for Somaliland, N. Cyprus, Kosovo, …) was deleted (C-39, PR #42). Enrichment now uses the GAUL lookup, which has **zero `-99` codes** across all 64,742 global cells (Somaliland → `SOM`, matching FAO's GAUL). The defect is eliminated as a side effect of the engine swap. |

---

### C-31: Runtime mapper unverified and unverifiable at global scale — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-31 |
| Resolved | 2026-06-24 |
| Resolution | The runtime mapper (`mapping.py`) was deleted (C-39, PR #42), so a global run *via the mapper* can no longer happen — this entry's hazard is moot. The enricher-path global-scale concerns are tracked separately (C-30 coverage, C-32 memory, C-34 coverage contract). D-08 (the swap-to-lookup-first decision this entry argued for) was executed. |

---

### C-23: Algorithmic divergence — area-based vs centroid-based GAUL mapping across VIEWS platform — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-23 |
| Resolved | 2026-06-24 |
| Resolution | The platform mapping divergence was resolved upstream (views-datafactory area-majority, 2026-06-12), and the residual ISO-code difference disappeared when ADR-011's GAUL lookup replaced the runtime mapper (C-39, PR #42). The lookup (built from the factory's GAUL parquets) is now the single enrichment source — no second algorithm remains to diverge from. |

---

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

### D-07: Historical data route — keep pipeline-core dispatcher vs call datafactory directly — RESOLVED

| Field | Value |
|-------|-------|
| ID | D-07 |
| Source | `expert-code-review` (2026-06-12) |
| Perspectives | Ousterhout/Hickey: the postprocessor uses ~20% of `ViewsDataLoader`'s services (it passes `use_saved=False, validate=False, self_test=False`) while paying 100% of the seven-hop indirection — call `datafactory_query.load_dataset()` directly and own the three renames. Martin/GoF/Feathers: the dispatcher seam absorbed the viewser→datafactory migration with zero consumer changes and will absorb the next one; bypassing it re-couples the postprocessor to the current backend. |
| Location | `views_postprocessing/unfao/managers/unfao.py:44-59`; views-pipeline-core `modules/dataloaders/dataloaders.py:1088-1224` |
| Status | Open. Review recommendation: keep the pipeline-core route, but pass explicit `month_first/month_last` instead of partition semantics, consume `get_data()`'s return value (C-29), and re-enable validation once it supports datafactory sources. Decide alongside ADR-011 since both touch the same manager. |

**Resolved (2026-06-26) — maintainer's data-sourcing principle.** *Data-related facts — data, metadata, validity dates, country/admin codes — come from the **producer** (views-datafactory, or viewser until phased out), **not** routed through pipeline-core. pipeline-core is the orchestration framework, not a data pass-through; depending on it for data facts couples the delivery to an unstable, mid-migration hub (SDP) and risks cycles (ADP).*

Concretely: **(1)** producer-published facts (e.g. `last_valid_month_id`, region cell-counts) are read **directly from the producer** — pipeline-core must not be a lossy intermediary that drops them. First instantiated in S2 (#52): `views_postprocessing/unfao/source_metadata.py` reads `last_valid_month_id` straight from datafactory's `.zattrs`, never via the loader that discards it. **(2)** This decides the disagreement toward the Ousterhout/Hickey side **for facts**, but does **not** mandate ripping out the dispatcher wholesale: its source-abstraction (viewser↔datafactory routing) retains value for the **bulk data fetch** during the viewser phase-out. The principle is *'don't route through pipeline-core just for the sake of it / don't depend on it for what it merely passes through or drops'* — not *'never use the dispatcher.'* The earlier review recommendations for the bulk fetch (explicit month range; consume `get_data()`'s return value — C-29) still stand. Net: **the producer is the source of truth for data + facts; pipeline-core orchestrates.**

---

### D-10: The 82 GAUL-uncovered cells — exclude, crash, or negotiate with FAO — RESOLVED

| Field | Value |
|-------|-------|
| ID | D-10 |
| Source | `expert-code-review` (2026-06-12) |
| Perspectives | Fail-loud purism: let validation crash and force the conversation — never silently drop cells. Pragmatic exclusion: drop with a named, count-asserted, logged exclusion list. Diplomatic: ask FAO before shipping anything. |
| Location | `views_postprocessing/unfao/managers/unfao.py:188-221`; the 82 gids enumerated in C-30 |
| Status | **Resolved direction (2026-06-12): fix upstream in views-datafactory.** User decision, superseding the review's exclusion-list adjudication. A new bundled curated region (`land ∩ gaul0_code != -1`, 64,736 cells — e.g. `land_gaul`) is added to `datafactory_query` alongside `land` and `africa_me_legacy`, with generation script, provenance, and a count-pinning test. The postprocessor keeps zero spatial knowledge; its invariant simplifies to "every arriving cell must enrich completely — any null crashes" (the existing `_validate()` gate, unchanged). The `land` region itself is NOT redefined (other consumers depend on its physical-land semantics). Forecast-path residual: unmatched gids null→crash via left merge + validation; pin with one test. FAO disclosure of the 82 excluded sub-Antarctic cells still required in the release note. Closes the postprocessor side of C-30; C-34's coverage test becomes "100% completeness for the configured region." |

---

### D-08: Global delivery path — scale up the runtime mapper vs swap to the precomputed lookup first — RESOLVED

| Field | Value |
|-------|-------|
| ID | D-08 |
| Source | `expert-code-review` (2026-06-12) |
| Perspectives | Feathers' instinct: the mapper is production-proven and the region change is one config line — don't swap components days before a deadline. Kleppmann/Nygard/Ousterhout: the mapper is *unverifiable at global scale before running it* (C-31: unknown null count, runtime, memory; C-08 newly in scope), while the lookup's complete global failure set is exactly 82 named cells, verified locally (C-30). |
| Location | `views_postprocessing/unfao/managers/unfao.py:154-160`; `mapping.py`; views-datafactory `data/raw/gaul_admin/*.parquet` |
| Status | Open — user decision pending. Review adjudication: **swap to the lookup first, then go global.** The "don't swap before a deadline" rule assumes the old part is known-good for the new job; here it is known-good only for a job 5× smaller and cannot be tested for the new job until the moment it matters. Enumerable risk beats discoverable risk on a deadline. Prerequisite: shadow diff old-vs-new on africa_me (13,110 cells) on the production machine. |

**Resolved by events (2026-06-24):** the swap was executed — the runtime mapper was deleted (C-39, PR #42) and `GaulLookupEnricher` is the enrichment path. The review adjudication ('swap to the lookup first, then go global') is now the shipped state.

---

### D-05: Strategic direction — eliminate runtime mapper vs keep area-based algorithm — RESOLVED

| Field | Value |
|-------|-------|
| ID | D-05 |
| Source | `manual` (2026-06-02) — external assessment |
| Perspectives | Path A: area-based is a FAO requirement → precompute lookup table. Path B: centroid-based acceptable → eliminate mapping.py entirely. Both eliminate 774 MB shapefiles, geopandas, and 3,100-line mapper. |
| Resolution | **Resolved (2026-06-02): Path A confirmed.** FAO-FSFC provided written confirmation (Release Note 02, `summary.tex`) agreeing to area-majority allocation as the locked aggregation rule: "Each PRIO-GRID cell is assigned to a single country using an area-majority rule." The area-based algorithm is a contractual requirement, not a historical accident. Path B (centroid-based) is off the table. Next step: build a one-time precomputed area-based lookup table (~65K rows, Parquet) and replace the 3,100-line runtime mapper with a dictionary lookup. This still eliminates geopandas, the shapefile bundle, and the runtime spatial operations — but preserves the area-majority assignment rule. |
| Update 2026-06-12 | **Upstream resolution deployed.** views-datafactory shipped area-majority GAUL assignment (issue #115 → PR #127, ADR-039 there, v1.2.28/29). All 7 GAUL parquets (codes + names + iso3) regenerated June 11 as area-majority, 259,200 rows each, mutually consistent (13,105/13,110 africa_me cells fully attributed; 5 pure-ocean cells unassigned). The precomputed lookup table can now be built by joining the factory parquets — no LFS, no shapefiles, no this-repo mapper run needed. The platform-level mapping divergence (centroid in factory vs area-majority here) no longer exists. See `docs/cross_repo_integration_report.md` and ADR-011 assessment §10. |

---

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
