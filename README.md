# views-postprocessing

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Poetry](https://img.shields.io/badge/dependency%20management-poetry-blueviolet)](https://python-poetry.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A modular postprocessing framework for the **VIEWS** (Violence Early-Warning System) pipeline. This package provides tools for enriching conflict prediction data with geographic metadata, transforming outputs for partner organizations, and managing spatial mappings between PRIO-GRID cells and administrative boundaries.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Package Structure](#package-structure)
- [Modules](#modules)
  - [UNFAO Postprocessor](#unfao-postprocessor)
  - [PRIO-GRID Spatial Mapping](#prio-grid-spatial-mapping)
- [Shapefiles](#shapefiles)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

The VIEWS platform generates conflict predictions at the **PRIO-GRID** level—a standardized global grid system with ~50×50 km cells. Partner organizations like the **UN Food and Agriculture Organization (FAO)** require this data enriched with administrative metadata (country codes, province names, coordinates) for operational use.

`views-postprocessing` bridges this gap by providing:

1. **Postprocessor Managers** - Pipeline components that read, transform, validate, and deliver prediction data
2. **Spatial Mapping Tools** - Bidirectional mapping between PRIO-GRID cells and multi-level administrative boundaries
3. **Geographic Enrichment** - Automatic addition of coordinates, ISO codes, and GAUL boundary identifiers

---

## Features

- 🗺️ **Multi-level Administrative Mapping** - Map PRIO-GRID cells to countries, Admin Level 1 (provinces), and Admin Level 2 (districts)
- ⚡ **High-Performance Caching** - Disk-based and in-memory LRU caching for spatial operations
- 🔄 **Pipeline Integration** - Seamless integration with `views-pipeline-core` managers
- 📦 **Appwrite Integration** - Read from and write to Appwrite cloud storage buckets
- 🌍 **Comprehensive Shapefiles** - Bundled Natural Earth and GAUL 2024 boundary data
- ✅ **Schema Validation** - Automatic validation of output data schemas

---

## Installation

### Using Poetry (recommended)

```bash
# Clone the repository
git clone https://github.com/prio-data/views-postprocessing.git
cd views-postprocessing

# Install with Poetry
poetry install
```

### Using pip

```bash
pip install views-postprocessing
```

### Dependencies

| Package | Version | Description |
|---------|---------|-------------|
| `views-pipeline-core` | >=2.1.3,<3.0.0 | Core pipeline managers and utilities |
| `cachetools` | ==6.2.1 | LRU and TTL caching for spatial lookups |

**Note:** This package requires Python 3.11 or higher (compatible up to 3.15).

---

## Package Structure

```
views-postprocessing/
├── pyproject.toml                     # Package configuration
├── README.md                          # This file
└── views_postprocessing/
    ├── shapefiles/                    # Bundled geographic data
    │   ├── GAUL_2024_L1/              # Admin Level 1 boundaries
    │   ├── GAUL_2024_L2/              # Admin Level 2 boundaries
    │   ├── ne_10m_admin_0_countries/  # Natural Earth countries (10m)
    │   ├── ne_110m_admin_0_countries/ # Natural Earth countries (110m)
    │   └── priogrid_cellshp/          # PRIO-GRID cell geometries
    └── unfao/                          # UN FAO-specific module
        ├── managers/
        │   ├── unfao.py               # UNFAOPostProcessorManager
        │   └── README.md              # Manager documentation
        └── mapping/
            ├── mapping.py             # PriogridCountryMapper
            └── README.md              # Mapping documentation
```

---

## Modules

### UNFAO Postprocessor

The `UNFAOPostProcessorManager` transforms VIEWS predictions for UN FAO consumption:

```python
from views_pipeline_core.managers.postprocessor import PostprocessorPathManager
from views_postprocessing.unfao.managers.unfao import UNFAOPostProcessorManager

# Initialize
path_manager = PostprocessorPathManager("un_fao")
manager = UNFAOPostProcessorManager(
    model_path=path_manager,
    wandb_notifications=True
)

# Execute full pipeline
manager.execute()
```

#### Pipeline Stages

| Stage | Method | Description |
|-------|--------|-------------|
| **Read** | `_read()` | Fetches historical data from ViewsER and forecast data from Appwrite |
| **Transform** | `_transform()` | Enriches data with geographic metadata using `PriogridCountryMapper` |
| **Validate** | `_validate()` | Ensures schema compliance and required columns |
| **Save** | `_save()` | Saves to local parquet and uploads to UN FAO Appwrite bucket |

#### Output Schema

The postprocessor enriches data with these columns:

| Column | Type | Description |
|--------|------|-------------|
| `pg_xcoord` | float | PRIO-GRID cell centroid X coordinate (longitude) |
| `pg_ycoord` | float | PRIO-GRID cell centroid Y coordinate (latitude) |
| `country_iso_a3` | str | ISO 3166-1 alpha-3 country code |
| `admin1_gaul1_code` | int | GAUL Level 1 administrative code |
| `admin1_gaul1_name` | str | GAUL Level 1 administrative name |
| `admin2_gaul2_code` | int | GAUL Level 2 administrative code |
| `admin2_gaul2_name` | str | GAUL Level 2 administrative name |

---

### PRIO-GRID Spatial Mapping

The `PriogridCountryMapper` class provides comprehensive spatial mapping capabilities:

```python
from views_postprocessing.unfao.mapping.mapping import PriogridCountryMapper

# Initialize with disk caching
mapper = PriogridCountryMapper(
    use_disk_cache=True,
    cache_dir="~/.priogrid_mapper_cache",
    cache_ttl=86400 * 7  # 7 days
)

# Single cell lookup
country = mapper.find_country_for_gid(123456)
print(f"Country: {country}")  # e.g., "TZA"

# Find all PRIO-GRID cells in a country
gids = mapper.find_gids_for_country("NGA")
print(f"Nigeria has {len(gids)} PRIO-GRID cells")

# Admin boundary lookups
admin1_info = mapper.find_admin1_for_gid(123456)
admin2_info = mapper.find_admin2_for_gid(123456)

# Batch processing
gid_list = [123456, 123457, 123458, 123459]
countries = mapper.batch_country_mapping(gid_list)

# DataFrame enrichment
enriched_df = mapper.enrich_dataframe_with_pg_info(df, gid_column="priogrid_gid")
```

#### Mapping Decision Logic

The mapper uses a **largest overlap** algorithm to handle cells spanning multiple boundaries:

1. Find all administrative regions intersecting the grid cell
2. Calculate overlap ratio for each region
3. Assign to the region with the largest overlap

This provides deterministic, reproducible results even for border cells.

#### Key Methods

| Method | Description |
|--------|-------------|
| `find_country_for_gid(gid)` | Get ISO A3 country code for a PRIO-GRID cell |
| `find_gids_for_country(iso_a3)` | Get all PRIO-GRID cells within a country |
| `find_admin1_for_gid(gid)` | Get GAUL Level 1 info for a cell |
| `find_admin2_for_gid(gid)` | Get GAUL Level 2 info for a cell |
| `batch_country_mapping(gids)` | Map multiple cells efficiently |
| `batch_country_mapping_parallel(gids)` | Parallel batch mapping |
| `enrich_dataframe_with_pg_info(df)` | Add all geographic columns to a DataFrame |
| `get_all_countries()` | Get list of all available countries |
| `get_all_country_ids()` | Get list of all country ISO codes |
| `get_all_priogrids()` | Get all PRIO-GRID cell data |
| `get_all_priogrid_ids()` | Get list of all PRIO-GRID GIDs |

---

## Shapefiles

The package bundles essential geographic datasets:

| Dataset | Resolution | Source | Use Case |
|---------|------------|--------|----------|
| **Natural Earth Countries (110m)** | 110m | Natural Earth | Fast country lookups |
| **Natural Earth Countries (10m)** | 10m | Natural Earth | Precise country lookups |
| **PRIO-GRID Cells** | 0.5° × 0.5° | PRIO | Grid cell geometries |
| **GAUL Level 1** | - | FAO GAUL 2024 | Province/state boundaries |
| **GAUL Level 2** | - | FAO GAUL 2024 | District/county boundaries |

All shapefiles use **EPSG:4326 (WGS84)** coordinate reference system.

---

## Quick Start

### Basic Postprocessing

```python
from views_pipeline_core.managers.postprocessor import PostprocessorPathManager
from views_postprocessing.unfao.managers.unfao import UNFAOPostProcessorManager

# Set up the manager
path_manager = PostprocessorPathManager("un_fao")
manager = UNFAOPostProcessorManager(model_path=path_manager)

# Run the complete pipeline
manager.execute()
```

### Standalone Spatial Mapping

```python
from views_postprocessing.unfao.mapping.mapping import PriogridCountryMapper
import pandas as pd

# Initialize mapper
mapper = PriogridCountryMapper(use_disk_cache=True)

# Create sample data
df = pd.DataFrame({
    "priogrid_gid": [123456, 123457, 123458],
    "prediction": [0.05, 0.12, 0.08]
})

# Enrich with geographic metadata
enriched = mapper.enrich_dataframe_with_pg_info(df, gid_column="priogrid_gid")
print(enriched.columns)
# Index(['priogrid_gid', 'prediction', 'pg_xcoord', 'pg_ycoord', 
#        'country_iso_a3', 'admin1_gaul1_code', 'admin1_gaul1_name', 
#        'admin2_gaul2_code', 'admin2_gaul2_name'], dtype='object')
```

---

## Configuration

### Environment Variables

For Appwrite integration, configure these in your `.env` file:

```bash
# Appwrite Connection
APPWRITE_ENDPOINT=https://cloud.appwrite.io/v1
APPWRITE_DATASTORE_PROJECT_ID=your_project_id
APPWRITE_DATASTORE_API_KEY=your_api_key

# Production Forecasts Bucket (Input)
APPWRITE_PROD_FORECASTS_BUCKET_ID=production_forecasts
APPWRITE_PROD_FORECASTS_BUCKET_NAME=Production Forecasts
APPWRITE_PROD_FORECASTS_COLLECTION_ID=forecasts_metadata

# UN FAO Bucket (Output)
APPWRITE_UNFAO_BUCKET_ID=unfao_data
APPWRITE_UNFAO_BUCKET_NAME=UN FAO Data
APPWRITE_UNFAO_COLLECTION_ID=unfao_metadata

# Metadata Database
APPWRITE_METADATA_DATABASE_ID=file_metadata
APPWRITE_METADATA_DATABASE_NAME=File Metadata
```

### Caching Configuration

```python
# Disk caching (persistent across sessions)
mapper = PriogridCountryMapper(
    use_disk_cache=True,
    cache_dir="/path/to/cache",  # Default: ~/.priogrid_mapper_cache
    cache_ttl=604800  # 7 days in seconds
)

# Memory-only caching (faster, but not persistent)
mapper = PriogridCountryMapper(
    use_disk_cache=False
)
```

---

## API Reference

For detailed API documentation, see the module-specific README files:

- [UNFAO Manager Documentation](views_postprocessing/unfao/managers/README.md)
- [PRIO-GRID Mapping Documentation](views_postprocessing/unfao/mapping/README.md)

---

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Clone and install in development mode
git clone https://github.com/prio-data/views-postprocessing.git
cd views-postprocessing
poetry install
```

---

## License

This project is part of the VIEWS platform developed by the **Peace Research Institute Oslo (PRIO)**. See the [LICENSE](LICENSE) file for details.

---

## Related Packages

| Package | Description |
|---------|-------------|
| [`views-pipeline-core`](https://github.com/views-platform/views-pipeline-core) | Core pipeline managers and utilities |

---