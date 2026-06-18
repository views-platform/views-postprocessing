# UNFAOPostProcessorManager

A postprocessor manager for transforming ViEWS pipeline predictions into UN FAO-compatible formats with geographic metadata enrichment.

## Overview

The `UNFAOPostProcessorManager` is a specialized postprocessor that prepares VIEWS conflict prediction data for delivery to the United Nations Food and Agriculture Organization (UN FAO). It handles:

- Reading historical observation data from Viewser
- Downloading forecast predictions from the Appwrite datastore
- Enriching data with geographic metadata (coordinates, country codes, admin boundaries)
- Validating output schema compliance
- Uploading processed data to the UN FAO Appwrite storage bucket

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  UNFAOPostProcessorManager                      │
│     (extends PostprocessorManager + ForecastingModelManager)    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐    ┌──────────────────┐                  │
│  │  Historical Data │    │   Forecast Data  │                  │
│  │   (Viewser)      │    │   (Appwrite)     │                  │
│  └────────┬─────────┘    └────────┬─────────┘                  │
│           │                       │                             │
│           └───────────┬───────────┘                             │
│                       ▼                                         │
│           ┌───────────────────────┐                             │
│           │   GaulLookupEnricher   │                            │
│           │  (Geographic Metadata) │                            │
│           └───────────┬───────────┘                             │
│                       ▼                                         │
│           ┌───────────────────────┐                             │
│           │   Validation Layer    │                             │
│           └───────────┬───────────┘                             │
│                       ▼                                         │
│           ┌───────────────────────┐                             │
│           │  UN FAO Appwrite      │                             │
│           │  (Output Storage)     │                             │
│           └───────────────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

1. **Read Phase** (`_read`)
   - Fetches historical data from ViewsER via `ViewsDataLoader`
   - Downloads latest forecast predictions from Appwrite production forecasts bucket

2. **Transform Phase** (`_transform`)
   - Enriches both historical and forecast dataframes with geographic metadata
   - Uses `GaulLookupEnricher` to merge a precomputed GAUL lookup onto PRIO-GRID cells (ADR-011)

3. **Validate Phase** (`_validate`)
   - Ensures all required metadata columns are present
   - Checks for schema compliance before output

4. **Save Phase** (`_save`)
   - Saves processed data to local parquet files
   - Uploads to UN FAO-specific Appwrite bucket with metadata

## Installation

Part of `views-postprocessing` package:

```bash
pip install views-postprocessing
```

## Configuration

### Required Environment Variables

The manager requires several environment variables for Appwrite connectivity. These should be set in the `.env` file found at the root of views-models:

```bash
# Appwrite Connection
APPWRITE_ENDPOINT=https://cloud.appwrite.io/v1
APPWRITE_DATASTORE_PROJECT_ID=your_project_id
APPWRITE_DATASTORE_API_KEY=your_api_key

# Production Forecasts Bucket (Input)
APPWRITE_PROD_FORECASTS_BUCKET_ID=production_forecasts
APPWRITE_PROD_FORECASTS_BUCKET_NAME=Production Forecasts
APPWRITE_PROD_FORECASTS_COLLECTION_ID=forecasts_metadata
APPWRITE_PROD_FORECASTS_COLLECTION_NAME=Forecasts Metadata

# UN FAO Bucket (Output)
APPWRITE_UNFAO_BUCKET_ID=unfao_data
APPWRITE_UNFAO_BUCKET_NAME=UN FAO Data
APPWRITE_UNFAO_COLLECTION_ID=unfao_metadata
APPWRITE_UNFAO_COLLECTION_NAME=UN FAO Metadata

# Metadata Database
APPWRITE_METADATA_DATABASE_ID=file_metadata
APPWRITE_METADATA_DATABASE_NAME=File Metadata
```

## Usage

### Basic Usage

```python
from views_pipeline_core.managers.postprocessor import PostprocessorPathManager
from views_postprocessing.unfao.managers import UNFAOPostProcessorManager

# Initialize with path manager
path_manager = PostprocessorPathManager("un_fao")
manager = UNFAOPostProcessorManager(
    model_path=path_manager,
    wandb_notifications=True,
    use_prediction_store=False
)

# Execute the full pipeline
manager.execute()
```

### CLI Execution

From the postprocessor directory:

```bash
python main.py
```

### Step-by-Step Execution

```python
# Initialize
manager = UNFAOPostProcessorManager(path_manager)

# Read data
manager._read()  # Loads historical + forecast data

# Transform (add geographic metadata)
manager._transform()

# Validate schema
manager._validate()

# Save and upload
manager._save()
```

## Class Reference

### UNFAOPostProcessorManager

```python
class UNFAOPostProcessorManager(PostprocessorManager, ForecastingModelManager):
    def __init__(
        self,
        model_path: PostprocessorPathManager,
        wandb_notifications: bool = True,
        use_prediction_store: bool = False,
    ) -> None
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model_path` | PostprocessorPathManager | Required | Path manager for the postprocessor |
| `wandb_notifications` | bool | True | Enable Weights & Biases logging |
| `use_prediction_store` | bool | False | Whether to use prediction store (legacy) |

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `_historical_dataframe` | pd.DataFrame | Historical observation data from ViewsER |
| `_forecast_dataframe` | pd.DataFrame | Forecast predictions from ensemble |
| `_historical_dataset` | PGMDataset | Wrapped historical data with utilities |
| `_forecast_dataset` | PGMDataset | Wrapped forecast data with utilities |
| `_enricher` | GaulLookupEnricher | Precomputed-lookup geographic enrichment (ADR-011) |
| `ensemble_path_manager` | EnsemblePathManager | Path manager for source ensemble |

## Methods

### _read_historical_data()

Fetches historical observation data from ViewsER.

```python
manager._read_historical_data()
# Populates: _historical_dataframe, _historical_dataset
```

**Process:**
1. Uses `ViewsDataLoader` to fetch data for "forecasting" partition
2. Reads saved dataframe from `data_raw` directory
3. Creates `PGMDataset` wrapper with configured targets

### _read_forecast_data()

Downloads latest forecast predictions from Appwrite.

```python
manager._read_forecast_data()
# Populates: _forecast_dataframe, _forecast_dataset
```

**Process:**
1. Reads ensemble name from config
2. Initializes `EnsemblePathManager` for the source ensemble
3. Configures Appwrite connection from ensemble's `.env`
4. Downloads latest forecast file with `category="forecast"` filter
5. Creates `PGMDataset` wrapper

**Raises:**
- `ValueError`: If ensemble name not configured
- `Exception`: If download fails

### _append_metadata(dataset)

Enriches a dataset with geographic metadata.

```python
enriched_df = manager._append_metadata(dataset)
```

**Parameters:**
- `dataset`: PGMDataset to enrich

**Returns:** DataFrame with added metadata columns

**Added Columns:**
| Column | Description |
|--------|-------------|
| `pg_xcoord` | PRIO-GRID cell X coordinate (longitude) |
| `pg_ycoord` | PRIO-GRID cell Y coordinate (latitude) |
| `country_iso_a3` | ISO 3166-1 alpha-3 country code |
| `admin1_gaul1_code` | GAUL level 1 admin code |
| `admin1_gaul1_name` | GAUL level 1 admin name |
| `admin1_gaul0_code` | Parent country GAUL code |
| `admin1_gaul0_name` | Parent country name |
| `admin2_gaul2_code` | GAUL level 2 admin code |
| `admin2_gaul2_name` | GAUL level 2 admin name |

### _transform()

Applies geographic metadata to both dataframes.

```python
manager._transform()
# Updates: _historical_dataframe, _forecast_dataframe
```

### _validate()

Validates that required metadata columns are present.

```python
manager._validate()
```

**Required Columns:**
- `pg_xcoord`, `pg_ycoord`
- `country_iso_a3`
- `admin1_gaul1_code`, `admin1_gaul1_name`
- `admin1_gaul0_code`, `admin1_gaul0_name`
- `admin2_gaul2_code`, `admin2_gaul2_name`

**Raises:**
- `ValueError`: If any required column is missing

### _save()

Saves and uploads processed data to UN FAO Appwrite bucket.

```python
manager._save()
```

**Output Files:**
- `historical_dataset_{timestamp}.parquet` - Historical data with metadata
- `forecast_dataset_{timestamp}.parquet` - Forecast data with metadata

**Upload Metadata:**
| Field | Historical | Forecast |
|-------|-----------|----------|
| `name` | Postprocessor name | Ensemble name |
| `loa` | "pgm" | "pgm" |
| `type` | "model" | "model" |
| `category` | "historical" | "forecast" |
| `targets` | From config | Prediction columns |

## Output Schema Example

The processed dataframes have the following structure:

```
Index: (month_id, priogrid_gid)

Columns:
├── Target Variables
│   ├── ged_sb_dep (or configured targets)
│   ├── ged_ns_dep
│   └── ged_os_dep
│
├── Predictions (forecast only)
│   ├── pred_ln_sb_best
│   ├── pred_ln_ns_best
│   ├── pred_ln_os_best
│   ├── pred_ln_sb_prob
│   ├── pred_ln_ns_prob
│   └── pred_ln_os_prob
│
└── Geographic Metadata
    ├── pg_xcoord
    ├── pg_ycoord
    ├── country_iso_a3
    ├── admin1_gaul1_code
    ├── admin1_gaul1_name
    ├── admin1_gaul0_code
    ├── admin1_gaul0_name
    ├── admin2_gaul2_code
    └── admin2_gaul2_name
```

## Error Handling

### Common Errors

**Appwrite Connection Failed:**
```
Error while trying to download the latest forecast data...
```
*Solution:* Verify environment variables are set correctly in the ensemble's `.env` file

**Missing Metadata Columns:**
```
ValueError: Historical dataframe is missing required metadata column: country_iso_a3
```
*Solution:* Ensure the `GaulLookupEnricher`'s lookup table (`views_postprocessing/data/gaul_lookup.parquet`) is present and covers the requested cells

## Dependencies

- `views-pipeline-core`: Core pipeline infrastructure
- `views-postprocessing`: Postprocessor base classes and mapping utilities
- `pandas`: DataFrame operations
- `polars`: Alternative DataFrame operations
- `python-dotenv`: Environment variable management

## Example Workflow

```python
import logging
from views_pipeline_core.managers.postprocessor import PostprocessorPathManager
from views_postprocessing.unfao.managers import UNFAOPostProcessorManager

# Setup logging
logging.basicConfig(level=logging.INFO)

# Initialize
path_manager = PostprocessorPathManager("un_fao")
manager = UNFAOPostProcessorManager(path_manager)

# Full execution
try:
    # 1. Load data
    manager._read()
    print(f"Historical shape: {manager._historical_dataframe.shape}")
    print(f"Forecast shape: {manager._forecast_dataframe.shape}")
    
    # 2. Add geographic metadata
    manager._transform()
    print(f"Added columns: {manager._historical_dataframe.columns.tolist()}")
    
    # 3. Validate output
    manager._validate()
    print("Validation passed!")
    
    # 4. Save and upload
    manager._save()
    print("Data uploaded to UN FAO bucket")
    
except Exception as e:
    print(f"Pipeline failed: {e}")
```

## See Also

- [GaulLookupEnricher](../../../docs/CICs/GaulLookupEnricher.md) - Precomputed-lookup enrichment (ADR-011)
- [PriogridCountryMapper](../mapping/README.md) - Legacy runtime mapper (retained, no longer used by the manager)