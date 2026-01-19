# PRIO-GRID Spatial Mapping Module

## Overview

The `mapping.py` module provides a comprehensive spatial mapping solution for the VIEWS platform. It enables bidirectional mapping between **PRIO-GRID cells** (a standardized global grid system with ~50×50 km cells) and administrative boundaries at multiple levels:

- **Country level** (using Natural Earth data)
- **Admin Level 1** (GAUL 2024 - provinces/states)
- **Admin Level 2** (GAUL 2024 - districts/counties)

This module is critical for the UN FAO postprocessing pipeline, where conflict predictions made at the PRIO-GRID level need to be aggregated and reported at various administrative boundary levels.

---

## Table of Contents

1. [Key Concepts](#key-concepts)
2. [Data Sources](#data-sources)
3. [Classes](#classes)
4. [Mapping Decision Logic](#mapping-decision-logic)
5. [Caching Architecture](#caching-architecture)
6. [Key Methods](#key-methods)
7. [Usage Examples](#usage-examples)
8. [Performance Considerations](#performance-considerations)
9. [Configuration](#configuration)

---

## Key Concepts

### PRIO-GRID
The **Peace Research Institute Oslo GRID** (PRIO-GRID) is a standardized global grid system that divides the world into cells of approximately 0.5° × 0.5° (roughly 50×50 km at the equator). Each cell is identified by a unique **GID** (Grid ID). This grid provides a consistent spatial unit for conflict research and prediction.

### Administrative Boundaries
- **Country (GAUL Level 0)**: National boundaries using ISO A3 codes (e.g., 'USA', 'TZA', 'FRA')
- **Admin Level 1 (GAUL Level 1)**: First-level subdivisions (states, provinces, regions)
- **Admin Level 2 (GAUL Level 2)**: Second-level subdivisions (counties, districts)

### The Mapping Challenge
PRIO-GRID cells do not align perfectly with administrative boundaries. A single grid cell may:
- Fall entirely within one country/admin region
- Span multiple countries (e.g., border regions)
- Partially overlap water bodies
- Have its centroid in a different region than its majority area

This module implements sophisticated decision rules to handle these edge cases consistently.

---

## Data Sources

The module relies on the following shapefiles (paths configured relative to the module location):

| Data Source | Path | Description |
|------------|------|-------------|
| Natural Earth | `shapefiles/ne_110m_admin_0_countries/` | Country boundaries (110m resolution) |
| PRIO-GRID | `shapefiles/priogrid_cellshp/` | Global grid cell definitions |
| GAUL Admin 1 | `shapefiles/GAUL_2024_L1/` | First-level administrative boundaries |
| GAUL Admin 2 | `shapefiles/GAUL_2024_L2/` | Second-level administrative boundaries |

All shapefiles use **EPSG:4326** (WGS84) coordinate reference system.

---

## Classes

### `DistanceCache`

A simple LRU (Least Recently Used) cache for distance calculations.

```python
class DistanceCache:
    def __init__(self, maxsize=1000)
    def get(self, key) -> Optional[float]
    def set(self, key, value) -> None
```

**Purpose**: Caches haversine distance calculations to avoid redundant computations when calculating distances between grid cells and capital cities.

---

### `PriogridCountryMapper`

The main class that handles all spatial mapping operations.

#### Initialization

```python
mapper = PriogridCountryMapper(
    use_disk_cache=True,      # Enable persistent disk caching
    cache_dir=None,           # Custom cache directory (default: ~/.priogrid_mapper_cache)
    cache_ttl=None            # Cache time-to-live in seconds (None = no expiration)
)
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `countries_gdf` | GeoDataFrame | Natural Earth country boundaries |
| `priogrid_gdf` | GeoDataFrame | PRIO-GRID cell geometries with centroids |
| `admin1_gdf` | GeoDataFrame | GAUL Level 1 boundaries |
| `admin2_gdf` | GeoDataFrame | GAUL Level 2 boundaries |
| `priogrid_sindex` | SpatialIndex | R-tree index for fast PRIO-GRID queries |
| `admin1_sindex` | SpatialIndex | R-tree index for fast Admin1 queries |
| `admin2_sindex` | SpatialIndex | R-tree index for fast Admin2 queries |

---

## Mapping Decision Logic

### Country Assignment for a PRIO-GRID Cell

The `find_country_for_gid()` method uses a simple, deterministic **largest overlap** approach:

```
┌─────────────────────────────────────────────────────────────┐
│                    INPUT: PRIO-GRID GID                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 1: Find all countries that intersect the grid cell   │
│          using spatial index for performance               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 2: Calculate overlap ratio for each country          │
│          overlap_ratio = intersection_area / cell_area     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 3: Sort by overlap ratio (descending)                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 4: Assign to country with LARGEST OVERLAP            │
│          Method tag: "largest overlap"                     │
└─────────────────────────────────────────────────────────────┘
```

#### Why Largest Overlap?

The decision to use **only the largest overlap rule** (rather than a multi-rule hierarchy) provides several benefits:

1. **Simplicity** - One consistent rule is easier to understand, explain, and maintain
2. **Determinism** - The same input always produces the same output, regardless of centroid position
3. **Intuitive for aggregation** - When aggregating predictions, assigning to the region with the most area coverage makes sense (more of the cell's "land" belongs there)
4. **Handles all edge cases** - Works correctly for:
   - Cells entirely within one country (100% overlap)
   - Border cells spanning multiple countries
   - Coastal cells with partial water coverage (assigns to the country with most land area)

### Admin Level Assignment

The `find_admin1_for_gid()` and `find_admin2_for_gid()` methods use the same largest overlap approach:

1. **First determine the country** - Uses `find_country_for_gid()` to ensure admin regions are filtered to the correct country
2. **Calculate overlaps** - For all admin regions in that country that intersect the grid cell
3. **Assign to largest overlap** - The admin region with the highest overlap ratio wins

This approach ensures that:
- Admin regions are always consistent with the assigned country
- The assignment method is consistent across all administrative levels
- Results are deterministic and reproducible

---

## Caching Architecture

The module implements a sophisticated multi-layer caching system to optimize performance:

### Cache Types

```
┌─────────────────────────────────────────────────────────────┐
│                     CACHING ARCHITECTURE                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────┐     ┌─────────────────────┐
│   DISK CACHE        │     │   MEMORY CACHE      │
│   (Persistent)      │     │   (Session-based)   │
├─────────────────────┤     ├─────────────────────┤
│ • Survives restarts │     │ • Faster access     │
│ • Shared across     │     │ • Limited size      │
│   processes         │     │ • LRU or TTL-based  │
│ • Uses joblib       │     │ • Uses cachetools   │
│   Memory            │     │                     │
└─────────────────────┘     └─────────────────────┘

Default location: ~/.priogrid_mapper_cache/
├── country/    # GID → Country mappings
├── admin1/     # GID → Admin1 mappings
├── admin2/     # GID → Admin2 mappings
└── gid/        # Point → GID mappings
```

### Cache Configuration

| Cache Type | Max Size | Purpose |
|------------|----------|---------|
| Country Cache | 100,000 | GID → Country mappings |
| GID Cache | 100,000 | Point → GID lookups |
| GIDs for Country | 10,000,000 | Country → [GIDs] reverse mapping |
| Admin1 Cache | 100,000 | GID → Admin1 mappings |
| Admin2 Cache | 100,000 | GID → Admin2 mappings |

### Cache Methods

```python
# Clear all or specific caches
mapper.clear_cache(cache_type="all")  # "all", "country", "admin1", "admin2", "gid"

# Get cache statistics
stats = mapper.get_cache_stats()

# Pre-warm cache for frequently accessed data
mapper.warm_cache(gid_list=[123, 456, 789], iso_a3_list=['TZA', 'KEN'])
```

---

## Key Methods

### Core Mapping Methods

#### `find_country_for_gid(gid: int) -> dict`

Find country information for a PRIO-GRID cell.

**Returns:**
```python
{
    "gid": 123456,
    "iso_a3": "TZA",
    "country_name": "Tanzania",
    "overlap_ratio": 0.85,
    "method": "largest overlap",
    # ... additional Natural Earth fields
}
```

#### `find_admin1_for_gid(gid: int) -> dict`

Find Admin Level 1 region for a PRIO-GRID cell.

**Returns:**
```python
{
    "gid": 123456,
    "gaul1_code": 45678,
    "gaul1_name": "Dar es Salaam",
    "iso3_code": "TZA",
    "method": "largest overlap",
    "gaul0_code": 123,
    "gaul0_name": "Tanzania",
    # ... additional GAUL fields
}
```

#### `find_admin2_for_gid(gid: int) -> dict`

Find Admin Level 2 region for a PRIO-GRID cell.

**Returns:**
```python
{
    "gid": 123456,
    "gaul2_code": 78901,
    "gaul2_name": "Kinondoni",
    "iso3_code": "TZA",
    "method": "largest overlap",
    "gaul1_code": 45678,
    "gaul1_name": "Dar es Salaam",
    # ... additional GAUL fields
}
```

#### `find_gids_for_country(iso_a3: str) -> List[int]`

Find all PRIO-GRID cells belonging to a country (reverse mapping).

```python
gids = mapper.find_gids_for_country("TZA")
# Returns: [123456, 123457, 123458, ...]
```

### Batch Processing Methods

#### `batch_country_mapping(gid_list: List[int]) -> pd.DataFrame`

Process multiple GIDs with cache optimization.

```python
df = mapper.batch_country_mapping([123, 456, 789, ...])
```

#### `batch_country_mapping_parallel(gid_list, batch_size=1000) -> pd.DataFrame`

Process large datasets using multiprocessing.

```python
df = mapper.batch_country_mapping_parallel(gid_list, batch_size=1000)
```

#### `batch_admin_mapping(gid_list, admin_level="admin1") -> pd.DataFrame`

Batch mapping for admin regions.

```python
df = mapper.batch_admin_mapping(gid_list, admin_level="admin2")
```

### DataFrame Enrichment Methods

#### `enrich_dataframe_with_pg_info(df, ...)`

Enrich a DataFrame containing PRIO-GRID IDs with geographic metadata.

```python
enriched_df = mapper.enrich_dataframe_with_pg_info(
    df,
    pg_id_col="priogrid_id",
    time_id_col="month_id",
    include_country=True,
    include_admin1=True,
    include_admin2=True,
    include_pg_info=True,
    batch_size=1000,
    use_multiprocessing=True,
    show_progress=True
)
```

**Result columns added:**
- `country_iso_a3`, `country_name`, `country_overlap_ratio`, `country_method`
- `admin1_gaul1_code`, `admin1_gaul1_name`, `admin1_method`
- `admin2_gaul2_code`, `admin2_gaul2_name`, `admin2_method`
- `pg_xcoord`, `pg_ycoord`, `pg_geometry`, etc.

### Visualization Methods

#### `visualize_grid_and_country(gid: int)`

Visualize a PRIO-GRID cell and its assigned country.

```python
mapper.visualize_grid_and_country(123456)
```

#### `visualize_grid_and_admin(gid, admin_level="admin1", show_all_admins=False)`

Visualize a PRIO-GRID cell with admin boundaries.

```python
mapper.visualize_grid_and_admin(123456, admin_level="admin2", show_all_admins=True)
```

### Utility Methods

#### `find_gid_for_point(point_geometry) -> int`

Find which PRIO-GRID cell contains a point.

```python
from shapely.geometry import Point
gid = mapper.find_gid_for_point(Point(36.8, -1.3))  # Nairobi
```

#### `find_country_by_iso_a3(iso_a3: str) -> dict`

Get detailed country information by ISO code.

```python
info = mapper.find_country_by_iso_a3("TZA")
```

#### `search_countries_by_name(name_pattern, exact_match=False) -> List[dict]`

Search for countries by name pattern.

```python
results = mapper.search_countries_by_name("tanzania")
results = mapper.search_countries_by_name("united", exact_match=False)
```

---

## Usage Examples

### Basic Usage

```python
from views_postprocessing.unfao.mapping.mapping import PriogridCountryMapper

# Initialize mapper (loads shapefiles, builds spatial indices)
mapper = PriogridCountryMapper(use_disk_cache=True)

# Map a single PRIO-GRID cell to country
result = mapper.find_country_for_gid(148345)
print(f"GID 148345 belongs to {result['country_name']} ({result['iso_a3']})")
print(f"Assignment method: {result['method']}")

# Get all admin levels at once
all_info = mapper.find_all_admin_for_gid(148345)
```

### Batch Processing for Large Datasets

```python
import pandas as pd

# Your prediction data with PRIO-GRID IDs
predictions_df = pd.DataFrame({
    'priogrid_id': [148345, 148346, 148347, ...],
    'month_id': [553, 553, 553, ...],
    'predicted_fatalities': [0.5, 1.2, 0.3, ...]
})

# Enrich with geographic metadata
enriched_df = mapper.enrich_dataframe_with_pg_info(
    predictions_df,
    pg_id_col='priogrid_id',
    include_country=True,
    include_admin1=True,
    include_admin2=True,
    use_multiprocessing=True,
    show_progress=True
)

# Now you can aggregate by country, admin1, or admin2
country_totals = enriched_df.groupby('country_iso_a3')['predicted_fatalities'].sum()
```

### Using the Default Global Mapper

```python
from views_postprocessing.unfao.mapping.mapping import get_default_mapper

# A global mapper is automatically initialized when the module is imported
mapper = get_default_mapper()

# Use it directly
result = mapper.find_country_for_gid(148345)
```

### Cache Management

```python
# Check cache statistics
stats = mapper.get_cache_stats()
print(f"Cache type: {stats['cache_type']}")
print(f"Country cache size: {stats['country_cache_size']}")

# Clear cache before fresh analysis
mapper.clear_cache(cache_type="all")

# Pre-warm cache for a specific region
african_countries = ['TZA', 'KEN', 'UGA', 'RWA', 'BDI']
mapper.warm_cache(iso_a3_list=african_countries)
```

---

## Performance Considerations

### Spatial Indexing

The module uses **R-tree spatial indices** for all geographic datasets:
- Reduces point-in-polygon queries from O(n) to O(log n)
- Critical for batch processing thousands of grid cells

### Recommended Batch Sizes

| Operation | Recommended Batch Size | Notes |
|-----------|----------------------|-------|
| Country mapping | 1,000 | Good balance of memory and parallelization |
| Admin mapping | 500-1,000 | Admin2 is more complex |
| DataFrame enrichment | 1,000 | Depends on available memory |

### Memory Management

- Enable disk caching (`use_disk_cache=True`) for large datasets
- Use `only_metadata=True` in `enrich_dataframe_with_pg_info()` to minimize memory
- Clear caches periodically for long-running processes

### Multiprocessing vs Threading

The module uses **ThreadPoolExecutor** instead of multiprocessing to avoid:
- Pickling issues with GeoDataFrames
- Memory duplication across processes
- Complex IPC overhead

For CPU-bound tasks, consider running multiple single-threaded instances.

---

## Configuration

### Global Constants

```python
# Cache directory (default: ~/.priogrid_mapper_cache)
CACHE_DIR = Path.home() / ".priogrid_mapper_cache"

# Cache sizes
COUNTRY_CACHE_MAXSIZE = 100_000
GID_CACHE_MAXSIZE = 100_000
GIDS_FOR_COUNTRY_CACHE_MAXSIZE = 10_000_000
ADMIN1_CACHE_MAXSIZE = 100_000
ADMIN2_CACHE_MAXSIZE = 100_000
```

### Shapefile Paths

Paths are configured relative to the module location:

```python
NATURAL_EARTH_COUNTRY_PATH = Path(__file__).parent.parent.parent / "shapefiles" / "ne_110m_admin_0_countries" / "ne_110m_admin_0_countries.shp"
PRIOGRID_SHAPEFILE_PATH = Path(__file__).parent.parent.parent / "shapefiles" / "priogrid_cellshp" / "priogrid_cell.shp"
ADM_1_SHAPEFILE_PATH = Path(__file__).parent.parent.parent / "shapefiles" / "GAUL_2024_L1" / "GAUL_2024_L1.shp"
ADM_2_SHAPEFILE_PATH = Path(__file__).parent.parent.parent / "shapefiles" / "GAUL_2024_L2" / "GAUL_2024_L2.shp"
```

---

## Helper Functions

### `cached_haversine(lat1, lon1, lat2, lon2) -> float`

Calculate great-circle distance between two points with caching.

```python
distance_km = cached_haversine(
    lat1=-6.8, lon1=39.3,  # Dar es Salaam
    lat2=-1.3, lon2=36.8   # Nairobi
)
```

### `set_default_mapper() -> PriogridCountryMapper`

Initialize the global default mapper.

### `get_default_mapper() -> PriogridCountryMapper`

Retrieve the global default mapper instance.

---

## Error Handling

The module handles various edge cases:

| Scenario | Behavior |
|----------|----------|
| Invalid GID | Returns `None` |
| GID in water (no country) | Returns `None` or uses water handling rule |
| Invalid ISO A3 code | Returns `None` with warning |
| Missing shapefile | Raises `FileNotFoundError` during initialization |
| Invalid geometry | Logged as warning, skipped in calculations |
| Cache miss | Computes and caches result |

---

## Dependencies

```
pandas
geopandas
shapely
numpy
joblib
cachetools
matplotlib (optional, for visualization)
tqdm (optional, for progress bars)
```
