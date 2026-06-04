# Technical Risk Register

| Register Info     | Details                              |
|-------------------|--------------------------------------|
| Project           | views-postprocessing                 |
| Owner             | Dylan Pinheiro / PRIO MD&D Team      |
| Last Updated      | 2026-06-02                           |
| Total Concerns    | 24                                   |
| Open Concerns     | 22                                   |
| Resolved Concerns | 2                                    |

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
**⚠ CONTINGENT ON ADR-011:** If precomputed lookup table replaces mapping.py, this entire cluster is eliminated. Defer until ADR-011 is executed.

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
**⚠ CONTINGENT ON ADR-011:** If precomputed lookup table replaces mapping.py, this entire cluster is eliminated. Defer until ADR-011 is executed.

### Cluster D: Mapper-manager boundary contract
**Root cause:** No explicit contract declares what columns the mapper produces and the manager consumes.
**Entries:** C-04, C-17
**Highest tier:** 2 (C-04)
**Fix strategy:** Define `ENRICHMENT_SCHEMA` constant. Harmonize forward/reverse thresholds. Add end-to-end integration test.
**Resolution scope:** Full
**⚠ CONTINGENT ON ADR-011:** If precomputed lookup table replaces mapping.py, the boundary simplifies to a Parquet schema. C-17 is eliminated; C-04 is eliminated (no runtime forward/reverse divergence).

### Cluster F: CIC-code drift (documentation describes aspirational, not actual behavior)
**Root cause:** CICs were written as design contracts and never validated against the code. Multiple guarantees are false.
**Entries:** Campaign findings 1.1, 1.2 — affecting CIC PriogridCountryMapper §3/§5/§6 and CIC UNFAOPostProcessorManager §3/§6
**Highest tier:** Not a code risk — documentation accuracy risk
**Fix strategy:** Update CICs to describe actual code behavior. Specifically: (1) cache guarantee needs C-05 caveat, (2) return types need full key listing, (3) §6 log level should say DEBUG not WARNING, (4) ADR-008 compliance claim needs qualifying, (5) env var boundary validation claim needs qualifying. Pure documentation, no code changes.
**Resolution scope:** Full

### Cluster E: Replace runtime mapper with precomputed lookup table
**Root cause:** The area-majority algorithm is a confirmed FAO requirement (D-05 resolved), but it doesn't need 3,100 lines of geopandas runtime code — a one-time precomputation produces a ~65K-row Parquet lookup table that replaces the entire mapper with a dictionary join.
**Entries:** C-23, D-05 (resolved), and transitively: Clusters A (cache), C (import side effect), plus C-07, C-08, C-11
**Highest tier:** 2 (C-23)
**Fix strategy:** (1) One-time precomputation job: run the current mapper against all ~65K PRIO-GRID cells, store the result as a Parquet file. (2) Replace `mapping.py` with a simple Parquet-join enricher. (3) Remove 774 MB shapefile bundle, geopandas dependency, and all cache machinery.
**Resolution scope:** Full — resolves Clusters A and C entirely. Eliminates C-07, C-08, C-11. Reduces Cluster B to manager-side concerns only (C-19 unfao.py raises, C-21 batch tracking, C-22 correction process).

---

## Open Concerns

### C-02: Module-level side effect blocks package import on shapefile failure

| Field | Value |
|-------|-------|
| ID | C-02 |
| Tier | 2 |
| Source | `repo-assimilation` (2026-06-02) |
| Trigger | When updating, relocating, or removing any shapefile in `views_postprocessing/shapefiles/`, verify that import of the package still succeeds |
| Location | `views_postprocessing/unfao/mapping/mapping.py:3122` |

Line 3122 calls `set_default_mapper()` at module scope, which instantiates `PriogridCountryMapper` and loads 4 large shapefiles (Natural Earth 10m, PRIO-GRID, GAUL L1, GAUL L2). If any shapefile is missing or malformed, the import of `mapping.py` raises an exception. Because `unfao.py` imports `get_default_mapper` from this module, and the `managers/__init__.py` re-exports `UNFAOPostProcessorManager`, any consumer importing from this package will fail — even code paths that do not need the mapper. This makes the package entirely unusable if a single shapefile is corrupted.

---

### C-03: Test coverage gaps across mapper-manager boundary and manager code

| Field | Value |
|-------|-------|
| ID | C-03 |
| Tier | 3 |
| Source | `repo-assimilation` (2026-06-02), `test-review` (2026-06-02) |
| Trigger | When modifying the manager's `_validate()` or the mapper's `find_*` methods, verify that the test suite covers the changed behavior — integration-level coverage across the mapper-manager boundary is still absent |
| Location | `tests/test_mapping.py`, `tests/test_validation.py`, `views_postprocessing/unfao/managers/unfao.py` |

Initial state was zero test coverage. A 73-test suite was written (2026-06-02) covering the mapper's core guarantees (determinism, largest-overlap, admin assignment, cache equivalence, GID-not-found, missing shapefile, C-05 disk-cache bug) and the validation logic (missing columns, null rejection, error messages). Remaining gaps: (1) the validation tests replicate `_validate()` logic in a standalone function because `views-pipeline-core` is unavailable in test environments — if the real `_validate()` diverges, tests pass while production fails; (2) no end-to-end test enriches through the mapper then validates through the manager; (3) the `ThreadPoolExecutor` code path is never exercised in tests; (4) no tests run against real shapefiles (Git LFS not installed). CI pytest step has been uncommented.

Tier recalibrated from 2 to 3 during review-rr (2026-06-02): 73 tests now exist covering core mapper guarantees. The gap is maintainability (test-code divergence, missing integration path), not structural fragility.

---

### C-04: Inconsistent forward/reverse mapping breaks expected bijection

| Field | Value |
|-------|-------|
| ID | C-04 |
| Tier | 2 |
| Source | `repo-assimilation` (2026-06-02) |
| Trigger | When using `find_gids_for_country()` to enumerate cells for aggregation, verify that the result set is consistent with what `find_country_for_gid()` would assign to that country |
| Location | `views_postprocessing/unfao/mapping/mapping.py:920-922,662-668` |

`find_country_for_gid()` assigns a GID to the country with the largest overlap regardless of magnitude (a 30% overlap wins if it's the largest). `_find_dominant_country_gids()` (used by `find_gids_for_country()`) requires `overlap_ratio > 0.5` to include a GID (line 922). A border cell with 40% overlap in country A and 35% in country B will be assigned to A by the forward lookup but excluded from `find_gids_for_country("A")`. Any downstream aggregation using the reverse lookup will silently miss cells that the enrichment step assigned to that country.

---

### C-05: Multiple methods crash when disk caching is active

| Field | Value |
|-------|-------|
| ID | C-05 |
| Tier | 2 |
| Source | `repo-assimilation` (2026-06-02), `graphify` (2026-06-02) |
| Trigger | When calling `batch_country_mapping()`, `batch_admin_mapping()`, `find_multiple_countries_by_iso_a3()`, `get_cache_stats()`, or `clear_cache()` on a mapper initialized with `use_disk_cache=True`, the call will raise `AttributeError` |
| Location | `views_postprocessing/unfao/mapping/mapping.py:786-787,1665-1668,2331-2332,286-294,332-344` |

Multiple methods directly access `self._country_cache`, `self._admin1_cache`, and `self._admin2_cache`, which are in-memory LRU/TTL cache attributes only created when `use_disk_cache=False`. When `use_disk_cache=True`, the `__init__` method only creates `self._disk_*_cache` variants and never initializes the in-memory attributes. Affected methods: `batch_country_mapping()` (line 787), `batch_admin_mapping()` (lines 1665-1668), `find_multiple_countries_by_iso_a3()` (line 2331), `clear_cache()` (lines 286-294), and `get_cache_stats()` (lines 332-344). The default mapper is initialized with `use_disk_cache=True` (line 3102), making this the default failure mode for all these methods.

Graphify graph traversal (2026-06-02) identified the broader scope: the same `self._*_cache` pattern appears in 6 methods beyond the originally identified `batch_country_mapping`.

See also C-03 (no tests to catch this), C-06 (duplication is the root cause — each cache branch has its own API surface).

---

### C-06: Massive code duplication across disk/memory cache branches

| Field | Value |
|-------|-------|
| ID | C-06 |
| Tier | 3 |
| Source | `repo-assimilation` (2026-06-02) |
| Trigger | When fixing a bug in the spatial overlap logic within any `find_*` method, verify that the fix is applied to BOTH the disk-cache and memory-cache branches of that method |
| Location | `views_postprocessing/unfao/mapping/mapping.py:609-775,807-900,1130-1362,1364-1612` |

Every method supporting both cache modes (`find_country_for_gid`, `find_admin1_for_gid`, `find_admin2_for_gid`, `find_gids_for_country`) contains the full spatial lookup implementation duplicated in both `if self.use_disk_cache` branches. The `find_country_for_gid` method alone has ~165 lines of identical logic in each branch. Total duplication accounts for approximately 1500 of the file's 3122 lines (~48%). A bug fixed in one branch may be missed in the other, creating divergent behavior depending on cache mode.

See also C-05 (an example of this risk materializing).

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

### C-10: Manager-to-Mapper coupling via module-level global state

| Field | Value |
|-------|-------|
| ID | C-10 |
| Tier | 3 |
| Source | `graphify` (2026-06-02) |
| Trigger | When writing unit tests for `UNFAOPostProcessorManager` that need to mock the mapper, verify that the dependency is injectable — currently it is hard-wired through the `_DEFAULT_MAPPER` global |
| Location | `views_postprocessing/unfao/mapping/mapping.py:3088-3122`, `views_postprocessing/unfao/managers/unfao.py:43` |

Graphify graph traversal revealed that `UNFAOPostProcessorManager` (component 4) and `PriogridCountryMapper` (component 0) are in completely disconnected graph components — they share no structural edge despite being tightly coupled at runtime. The connection goes through `get_default_mapper()` which returns the module-level `_DEFAULT_MAPPER` global (line 3116). In `unfao.py` line 43, the manager calls `self._mapper = get_default_mapper()`, coupling it to a singleton created at import time rather than accepting the mapper as an injected dependency. This makes the manager untestable in isolation (our test suite had to intercept `gpd.read_file` at conftest module level to work around this), and prevents using different mapper configurations in different contexts.

See also C-02 (the same module-level side effect that creates the global mapper).

---

### C-11: PriogridCountryMapper is a god class bridging 3 architectural concerns

| Field | Value |
|-------|-------|
| ID | C-11 |
| Tier | 3 |
| Source | `graphify` (2026-06-02) |
| Trigger | When adding a new spatial lookup method or output format, verify whether it belongs in the mapper or should be extracted into a separate class with a focused responsibility |
| Location | `views_postprocessing/unfao/mapping/mapping.py:133-3085` |

Graphify community detection identified `PriogridCountryMapper` as the highest-betweenness node in the repository graph (0.111), with 50 edges bridging 3 distinct functional communities: Spatial Mapping Engine (core overlap logic), Country Lookup Methods (`find_country_by_iso_a3`, `search_countries_by_name`, `get_country_summary`), and Utilities & Visualization (`visualize_grid_and_country`, `calculate_capital_distance`, `cached_haversine`). The class cohesion score is 0.04, indicating its internal methods are weakly interconnected. This single 3000-line class mixes spatial intersection logic, country metadata retrieval, DataFrame enrichment, batch processing, cache management, multiprocessing orchestration, and matplotlib visualization — violating the single-responsibility principle. The god class pattern increases the cost of change: modifying visualization code risks breaking spatial assignment, and vice versa.

Deep graph traversal (2026-06-02) quantified the structural fragility: 33.2% of all nodes are articulation points (removing any one disconnects subgraphs) and 37.7% of edges are bridges. Both metrics exceed the 30% threshold for tree-like fragility, confirming that the codebase has a star topology centered on this single class rather than a resilient mesh.

See also C-06 (code duplication within the same class amplifies the SRP violation).

---

### C-12: Silent wrong-country assignment when geometry intersection fails

| Field | Value |
|-------|-------|
| ID | C-12 |
| Tier | 2 |
| Source | `expert-review` (2026-06-02) |
| Trigger | When Natural Earth or GAUL shapefiles contain an invalid polygon for a country that is the correct assignment for a PRIO-GRID cell, verify that the geometry error is surfaced — currently the cell is silently assigned to the next-best country |
| Location | `views_postprocessing/unfao/mapping/mapping.py:658-660` (also duplicated at ~line 1192, 1428 in admin1/admin2 branches) |

In `find_country_for_gid()`, the overlap calculation loop (line 644-660) wraps each `country["geometry"].intersection(grid_geometry)` call in a bare `except Exception` that logs at DEBUG and skips the country with `continue`. The identical pattern exists in 7 locations across both cache branches: lines 659, 744 (country), 925 (reverse lookup), 1202, 1320 (admin1), 1436, 1562 (admin2). All 7 use `logger.debug` — invisible in production where DEBUG is disabled. The exception type is `Exception` (widest possible), catching not just `GEOSException` but also `TypeError`, `KeyError`, and any code bug.

If the correct country's polygon has an invalid geometry, its intersection fails, it's skipped, and the cell is assigned to the next-best country. The output contains no error signal — `method` still reads `"largest overlap"`. The wrong result is cached persistently by `joblib.Memory`. Critically, this is a *correlated* failure: if country X's polygon is invalid, ALL cells overlapping country X are misassigned — not just one. The UN FAO would receive data showing country X has zero conflict predictions while neighbors show inflated numbers. The failure is both systematic and undetectable from the output.

The mapper's own `_validate_naturalearth_data` (line 473-477) detects invalid geometries at load time and logs a WARNING, but does not call `make_valid()` or reject the data — a validate-then-proceed-anyway pattern. D-04 resolved (2026-06-02) to apply `make_valid()` at load time in all three `_load_*` methods. `make_valid()` has been applied to all three methods.

Critically, the manager's `_validate()` method — the only safety gate before upload — is structurally incapable of catching Cluster B's primary failure mode. `_validate()` checks column presence and null counts. A misassigned cell has a valid ISO code (just the wrong one), non-null values, and all required columns present. Validation passes. The safety net has a hole shaped exactly like the failure mode it should catch: wrong-but-valid geographic assignments are invisible to every automated check in the pipeline.

Tier recalibrated from 1 to 2 during post-campaign review-rr (2026-06-02): `make_valid()` now applied at load time mitigates the root cause. With valid geometries, intersection failures are limited to precision edge cases. The 7 DEBUG handlers remain but are defense-in-depth, not the primary failure path. Campaign Claim 2.1-2.4 confirmed correct algorithm behavior.

See also C-08 (a different mechanism for wrong-country at high latitudes), D-05 (if mapper eliminated, this concern is moot). Contingent on ADR-011.

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

### C-14: Stale disk cache returns outdated mappings after shapefile update

| Field | Value |
|-------|-------|
| ID | C-14 |
| Tier | 2 |
| Source | `expert-review` (2026-06-02) |
| Trigger | When updating GAUL or Natural Earth shapefiles to a new version, verify that the disk cache at `~/.priogrid_mapper_cache/` is manually cleared — there is no automatic invalidation |
| Location | `views_postprocessing/unfao/mapping/mapping.py:55-69,183-192` |

The `joblib.Memory` disk cache at `~/.priogrid_mapper_cache/` stores spatial mapping results keyed by function arguments (GID values), not by shapefile content or version. When shapefiles are updated (e.g., GAUL boundary revision, Natural Earth ISO code correction), the cache continues returning results computed against the old shapefiles. No staleness signal is emitted. The `clear_cache()` method exists but must be called manually — nothing in the initialization or shapefile loading path checks whether the cached results match the current shapefiles. A shapefile hash or modification timestamp in the cache key would provide automatic invalidation.

Wrong assignments persist in three layers beyond the cache: (1) joblib disk cache, (2) local timestamped parquet files in `data_generated/`, (3) Appwrite UN FAO bucket. Correcting a discovered error requires clearing the cache, re-running the pipeline, re-uploading to Appwrite, and notifying the partner — but no documented procedure exists for identifying which uploaded files contain affected GIDs or triggering a partner-side data retraction.

Additionally, stale cache violates the PriogridCountryMapper CIC's determinism guarantee ("the same GID always maps to the same country given the same input shapefiles"). Two environments with different cache states produce different output.

FAO Release Note 01, Topic C confirms: "FAO will release updated GAUL boundaries annually. Only boundaries that change will be updated." This establishes an annual regeneration cadence for the precomputed lookup table (ADR-011). Partial boundary updates mean only affected cells need re-mapping, but the current cache has no mechanism to identify which cells are affected by a partial shapefile update.

See also C-05 (cache API bugs), C-22 (no post-delivery correction process), ADR-011 (precomputed lookup replaces runtime cache).

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

### C-16: Thread-unsafe caches under concurrent enrichment

| Field | Value |
|-------|-------|
| ID | C-16 |
| Tier | 1 |
| Source | `expert-review` (2026-06-02) |
| Trigger | When `enrich_dataframe_with_pg_info` processes >1000 unique GIDs (triggering the `ThreadPoolExecutor` path at line 2546), concurrent threads read/write the shared `self._country_cache` LRUCache — verify thread safety of cache access |
| Location | `views_postprocessing/unfao/mapping/mapping.py:2557,697-774,1250-1362,1490-1612` |

`enrich_dataframe_with_pg_info` dispatches concurrent threads via `ThreadPoolExecutor` (line 2557) when `use_multiprocessing=True` (the default) and `total_ids > batch_size`. Each thread calls `find_country_for_gid`, `find_admin1_for_gid`, and `find_admin2_for_gid`, all of which read and write the shared `self._country_cache`, `self._admin1_cache`, and `self._admin2_cache` instances. The `cachetools` documentation explicitly states: "all these classes are not thread-safe. Access to a shared cache from multiple threads must be properly synchronized." Concurrent cache mutations can corrupt the internal `OrderedDict`, causing `RuntimeError: dictionary changed size during iteration`, `KeyError` on entries that should exist, or silently returning wrong cached values. The race window is a classic TOCTOU: thread A checks `cache_key in cache` (True), thread B evicts that key (LRU full), thread A reads `cache[cache_key]` → `KeyError` or wrong value.

See also C-05 (cache attribute bugs), D-02 (disagreement on fix approach).

---

### C-17: Implicit column naming contract between mapper and manager

| Field | Value |
|-------|-------|
| ID | C-17 |
| Tier | 3 |
| Source | `expert-review` (2026-06-02) |
| Trigger | When Natural Earth updates their shapefile and renames or adds columns (e.g., `ISO_A3` → `ISO_A3_EH`), verify that the mapper's 3-step column derivation still produces the names the manager expects in `filter_cols` |
| Location | `views_postprocessing/unfao/mapping/mapping.py:675,2709-2714`, `views_postprocessing/unfao/managers/unfao.py:146-158` |

The manager expects columns like `country_iso_a3` (unfao.py:151). The mapper produces this via a 3-step chain: Natural Earth column `ISO_A3` → `find_country_for_gid` dict key `iso_a3` (mapping.py:675) → `_process_pg_batch` prepends `country_` prefix (mapping.py:2709) → `country_iso_a3`. No explicit contract declares this mapping. Furthermore, when `country_cols=None` (the default), `_process_pg_batch` (lines 2710-2714) dumps ALL shapefile columns with the `country_` prefix, making the output schema dependent on external shapefile content. A Natural Earth column rename would silently break the chain, causing `_validate()` to reject the enriched data with a confusing "missing required metadata column" error that doesn't mention the shapefile as the root cause.

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

---

### C-20: ZeroDivisionError on degenerate zero-area cells

| Field | Value |
|-------|-------|
| ID | C-20 |
| Tier | 3 |
| Source | `falsification-audit` (2026-06-02) |
| Trigger | When a new shapefile version introduces a near-zero-but-not-exactly-zero area cell geometry, verify the `== 0.0` guard catches it — very small positive areas bypass the guard |
| Location | `views_postprocessing/unfao/mapping/mapping.py` (7 guard sites) |

Zero-area guards (`if grid_geometry.area == 0.0: logger.warning; return None`) were added at all 7 overlap calculation sites including `_find_dominant_country_gids`. A degenerate cell now returns `None` with a WARNING instead of silently vanishing. Remaining theoretical risk: near-zero-but-not-exactly-zero areas (e.g., 5e-31 square degrees) bypass the `== 0.0` check. This is physically impossible for real PRIO-GRID cells (~0.25 sq degrees) but could be strengthened with an epsilon-based guard.

Tier recalibrated from 1 to 3 during review-rr (2026-06-02): all 7 sites now have guards. The concern is mitigated from "silent vanishing" to "theoretical precision edge case."

See also C-12 (geometry intersection failures in the same catch block).

---

### C-21: Batch enrichment failures produce incomplete DataFrames (observability-only fix)

| Field | Value |
|-------|-------|
| ID | C-21 |
| Tier | 2 |
| Source | `falsification-audit` (2026-06-02) |
| Trigger | When `enrich_dataframe_with_pg_info` or `enrich_dataframe_with_country_info` encounters a batch-level processing failure, verify whether the failure is surfaced to the caller — currently failed batches are logged but not raised |
| Location | `views_postprocessing/unfao/mapping/mapping.py:2597-2600,2636-2638,2871-2874,2902-2904` |

Four `except Exception: logger.error(...); continue` handlers drop failed batches during DataFrame enrichment in both `enrich_dataframe_with_pg_info` and `enrich_dataframe_with_country_info`. `failed_batches` counters and summary ERROR logs were added to both methods. However, the fix is observability-only: `failed_batches` and `failed_gids` are tracked and logged but NOT included in the return value or raised as an exception. The caller receives the partial DataFrame with no programmatic signal. This does not satisfy ADR-003's fail-loud requirement.

Part of Cluster B (expanded scope). See also C-06 (duplication root cause).

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

## Disagreements

### D-01: Cache strategy refactoring — extract now vs. characterize first

| Field | Value |
|-------|-------|
| ID | D-01 |
| Source | `expert-review` (2026-06-02) |
| Perspectives | Martin/GoF (extract Strategy pattern now), Feathers/Beck (characterize disk-cache branch with tests first) |
| Resolution | **⚠ CONTINGENT ON ADR-011.** If precomputed lookup table replaces mapping.py, no cache to refactor — this disagreement is moot. Only resolve if mapper is kept. |

---

### D-02: Thread safety fix — lock caches vs. remove threading

| Field | Value |
|-------|-------|
| ID | D-02 |
| Source | `expert-review` (2026-06-02) |
| Perspectives | Nygard (threading.Lock), Beck (remove ThreadPoolExecutor), Hickey (sequential is simpler), Ousterhout (keep threading for speed) |
| Resolution | **⚠ CONTINGENT ON ADR-011.** If precomputed lookup table replaces mapping.py, no threading — this disagreement is moot. Only resolve if mapper is kept. |

---

### D-05: Strategic direction — eliminate runtime mapper vs keep area-based algorithm

| Field | Value |
|-------|-------|
| ID | D-05 |
| Source | `manual` (2026-06-02) — external assessment |
| Perspectives | Path A: area-based is a FAO requirement → precompute lookup table. Path B: centroid-based acceptable → eliminate mapping.py entirely. Both eliminate 774 MB shapefiles, geopandas, and 3,100-line mapper. |
| Resolution | **Resolved (2026-06-02): Path A confirmed.** FAO-FSFC provided written confirmation (Release Note 02, `summary.tex`) agreeing to area-majority allocation as the locked aggregation rule: "Each PRIO-GRID cell is assigned to a single country using an area-majority rule." The area-based algorithm is a contractual requirement, not a historical accident. Path B (centroid-based) is off the table. Next step: build a one-time precomputed area-based lookup table (~65K rows, Parquet) and replace the 3,100-line runtime mapper with a dictionary lookup. This still eliminates geopandas, the shapefile bundle, and the runtime spatial operations — but preserves the area-majority assignment rule. |

---

---

## Resolved Concerns

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

## Resolved Disagreements

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
