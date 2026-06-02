
# Class Intent Contract: PriogridCountryMapper

**Status:** Active  
**Owner:** PRIO MD&D Team  
**Last reviewed:** 2026-06-02  
**Related ADRs:** ADR-001, ADR-003, ADR-009  

---

## 1. Purpose

> **What is this class for?**

`PriogridCountryMapper` is the spatial mapping engine that maps PRIO-GRID cell IDs to administrative boundary metadata (country, admin level 1, admin level 2) using largest-overlap spatial intersection against bundled shapefiles.

It is the single authoritative source of geographic assignment in this repository.

---

## 2. Non-Goals (Explicit Exclusions)

- This class does **not** perform data pipeline orchestration or delivery
- This class does **not** fetch data from external services (Appwrite, ViewsER)
- This class does **not** manage pipeline lifecycle (read/transform/validate/save)
- This class does **not** modify or persist prediction data
- This class does **not** perform geodesic area calculations — it uses planar area on EPSG:4326 geometries
- This class does **not** handle partner-specific output formatting

---

## 3. Responsibilities and Guarantees

- Guarantees deterministic assignment: the same GID always maps to the same country/admin region given the same input shapefiles and equivalent cache state (caveat: stale disk cache from before a shapefile update violates this — see C-14)
- Guarantees that assignment uses the **largest overlap** rule: the administrative region with the highest area overlap ratio with the grid cell wins
- Guarantees that all loaded shapefiles have invalid geometries fixed via `make_valid()` and are validated for required columns and CRS at initialization
- Guarantees that spatial indices are built for all loaded GeoDataFrames to enable efficient queries
- Guarantees that cache mode (disk vs memory) does not affect mapping results — only performance
- Provides batch processing capabilities for enriching DataFrames with geographic metadata
- Provides both forward (GID → country) and reverse (country → GIDs) lookup

---

## 4. Inputs and Assumptions

- Requires 4 shapefiles at initialization: Natural Earth 10m countries, PRIO-GRID cells, GAUL 2024 L1, GAUL 2024 L2
- Assumes all shapefiles use EPSG:4326 (WGS84) coordinate reference system
- Assumes Natural Earth data contains columns: `ISO_A3`, `NAME_EN`, `geometry`
- Assumes PRIO-GRID data contains column: `gid`, `geometry`
- Assumes GAUL data contains columns: `gaul1_code`/`gaul2_code`, `gaul1_name`/`gaul2_name`, `iso3_code`, `geometry`
- Assumes `joblib` is available for disk caching and `cachetools` for memory caching

Assumptions that are not met **must cause failure**, not fallback behavior.

---

## 5. Outputs and Side Effects

**Outputs:**
- `find_country_for_gid(gid)` → dict with `iso_a3`, `country_name`, `overlap_ratio`, `method`, or `None`
- `find_admin1_for_gid(gid)` → dict with `gaul1_code`, `gaul1_name`, `iso3_code`, `method`, or `None`
- `find_admin2_for_gid(gid)` → dict with `gaul2_code`, `gaul2_name`, `iso3_code`, `method`, or `None`
- `find_gids_for_country(iso_a3)` → list of integer GIDs
- `enrich_dataframe_with_pg_info(df)` → DataFrame with added geographic columns

**Side Effects:**
- Creates disk cache directory (`~/.priogrid_mapper_cache/`) if disk caching enabled
- Writes joblib cache files to disk (persistent across sessions)
- Allocates a multiprocessing Pool (cleaned up in `__del__`)
- Logs progress at INFO level during batch operations

---

## 6. Failure Modes and Loudness

- **Missing shapefiles:** `FileNotFoundError` at initialization — the mapper cannot be instantiated
- **Invalid geometries in shapefiles:** Fixed automatically via `make_valid()` at load time. If intersection still fails at runtime, logged as WARNING and the country is skipped in the overlap calculation.
- **GID not found:** Returns `None` — this is not an error (ocean cells legitimately have no country)
- **Zero-area grid geometry:** Returns `None` with WARNING log — a degenerate cell (collapsed polygon) cannot have meaningful overlap
- **Invalid point geometry:** Raises `ValueError`
- **Required columns missing from shapefiles:** Raises `ValueError` at initialization

The following **must never** fail silently:
- Shapefile loading failures
- CRS validation failures
- Required column absence

---

## 7. Boundaries and Interactions

**Allowed interactions:**
- Reads shapefiles from the `views_postprocessing/shapefiles/` directory (Geographic Data Assets layer)
- Reads/writes to disk cache directory
- Uses `geopandas`, `shapely`, `joblib`, `cachetools` for spatial operations and caching

**Must not depend on:**
- Pipeline Managers (`UNFAOPostProcessorManager` or any orchestration code)
- External services (Appwrite, ViewsER)
- Environment variables or runtime configuration beyond cache directory path

This anchors the class within ADR-002 (topology): it sits at the Spatial Mapping Engine layer, above Geographic Data Assets, below Pipeline Managers.

---

## 8. Examples of Correct Usage

```python
from views_postprocessing.unfao.mapping.mapping import PriogridCountryMapper

mapper = PriogridCountryMapper(use_disk_cache=True)

# Single lookup
result = mapper.find_country_for_gid(148345)
# Returns: {"gid": 148345, "iso_a3": "TZA", "country_name": "Tanzania", "overlap_ratio": 0.95, "method": "largest overlap", ...}

# DataFrame enrichment
enriched = mapper.enrich_dataframe_with_pg_info(df, pg_id_col="priogrid_gid", batch_size=1000)
```

---

## 9. Examples of Incorrect Usage

- **Using the mapper to infer country from coordinates without going through the shapefile intersection** — this bypasses the declared assignment algorithm
- **Calling `batch_country_mapping()` with disk cache enabled** — this method only works with in-memory cache due to a known bug (C-05 in risk register)
- **Modifying `countries_gdf` or `priogrid_gdf` attributes directly** — these are loaded at initialization and treated as immutable reference data
- **Assuming `find_gids_for_country()` returns the exact inverse of `find_country_for_gid()`** — they use different threshold rules (known inconsistency, C-04 in risk register)

---

## 10. Test Alignment

- **Green tests:** Known-good GID → country mappings for unambiguous cells; schema compliance of enriched DataFrames; determinism across repeated calls
- **Beige tests:** Border cells (cells spanning 2+ countries); batch processing with mixed valid/invalid GIDs; both cache modes producing identical results
- **Red tests:** Non-existent GIDs; ocean-only cells; extreme latitude cells where planar distortion is maximal; corrupted geometries

Currently: **no tests exist** (C-03 in risk register). This contract defines what tests must verify when written.

---

## 11. Evolution Notes

- The assignment algorithm (largest overlap) is considered **stable** — changes require a new ADR
- Cache implementation details are **evolving** — may be refactored to eliminate duplication (C-06)
- The forward/reverse lookup inconsistency (C-04) is a known defect to be resolved
- `batch_country_mapping` crash with disk cache (C-05) is a known defect to be resolved

---

## End of Contract

This document defines the **intended meaning** of `PriogridCountryMapper`.

Changes to behavior that violate this intent are bugs.  
Changes to intent must update this contract.
