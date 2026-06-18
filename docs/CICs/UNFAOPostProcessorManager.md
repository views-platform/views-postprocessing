
# Class Intent Contract: UNFAOPostProcessorManager

**Status:** Active  
**Owner:** PRIO MD&D Team  
**Last reviewed:** 2026-06-02  
**Related ADRs:** ADR-001, ADR-002, ADR-008, ADR-009  

---

## 1. Purpose

> **What is this class for?**

`UNFAOPostProcessorManager` orchestrates the end-to-end postprocessing pipeline that reads VIEWS conflict predictions, enriches them with geographic metadata via the precomputed GAUL lookup (`GaulLookupEnricher`, ADR-011), validates the output schema, and delivers the enriched data to the UN FAO via Appwrite cloud storage.

It is the single entrypoint for producing and delivering UN FAO-formatted prediction data.

---

## 2. Non-Goals (Explicit Exclusions)

- This class does **not** perform spatial mapping logic — it delegates enrichment to `GaulLookupEnricher` (a merge against the precomputed GAUL lookup)
- This class does **not** train, evaluate, or modify prediction models
- This class does **not** define the spatial assignment algorithm
- This class does **not** manage shapefile data or geographic reference assets
- This class does **not** validate the correctness of spatial assignments — only their presence

---

## 3. Responsibilities and Guarantees

- Guarantees a 4-stage pipeline: read → transform → validate → save
- Guarantees that historical data is sourced from ViewsER via `ViewsDataLoader`
- Guarantees that forecast data is sourced from the Appwrite production forecasts bucket
- Guarantees that geographic metadata is added via `GaulLookupEnricher.enrich_dataframe_with_pg_info()` (a cell-id merge against the precomputed lookup)
- Guarantees that required metadata columns are validated before upload
- Guarantees that both historical and forecast datasets are uploaded to the UN FAO Appwrite bucket with correct metadata (name, loa, type, category)
- Guarantees that all structural failures are logged and raised (ADR-008)

---

## 4. Inputs and Assumptions

- Requires a `PostprocessorPathManager` at initialization pointing to valid model paths
- Requires `configs` dict to contain an `ensemble` key naming the source ensemble
- Requires environment variables for Appwrite connectivity (endpoint, project ID, API key, bucket/collection IDs)
- Requires the ensemble's `.env` file to be loadable via `dotenv`
- Requires the Appwrite production forecasts bucket to contain at least one file with `category="forecast"`
- Requires the precomputed GAUL lookup parquet to be present so `GaulLookupEnricher` can load it at construction

Assumptions that are not met **must cause failure**, not fallback behavior.

---

## 5. Outputs and Side Effects

**Outputs:**
- `_historical_dataframe`: Enriched pandas DataFrame with geographic metadata (multi-index: month_id, priogrid_gid)
- `_forecast_dataframe`: Enriched pandas DataFrame with geographic metadata (multi-index: month_id, priogrid_gid)

**Side Effects:**
- Downloads data from ViewsER (network I/O)
- Downloads forecast data from Appwrite (network I/O)
- Writes timestamped parquet files to `data_generated/` directory
- Uploads two parquet files to the UN FAO Appwrite bucket (network I/O)
- Loads `.env` from ensemble path (modifies process environment)
- Logs pipeline progress at INFO/ERROR levels

---

## 6. Failure Modes and Loudness

- **Missing `ensemble` config key:** Raises `ValueError` with descriptive message
- **Appwrite download failure:** Logs ERROR with full exception, then re-raises
- **Missing required metadata columns after enrichment:** Raises `ValueError` listing missing columns
- **Null values in required metadata columns:** Raises `ValueError` with null count and affected column name (C-01 resolved — validation active)
- **Dataset initialization failure:** Raises `ValueError` in `_save()` if datasets are None
- **Appwrite upload failure:** Propagates exception from `DatastoreModule`

The following **must never** fail silently:
- Missing or None environment variables for Appwrite
- Network failures during download or upload
- Schema validation failures (missing columns or null values)

---

## 7. Boundaries and Interactions

**Allowed interactions:**
- Delegates geographic enrichment to `GaulLookupEnricher` (a merge against the precomputed GAUL lookup)
- Uses `views-pipeline-core` managers for path resolution, data loading, and Appwrite integration
- Reads environment variables for external service configuration
- Writes to local filesystem and Appwrite cloud storage

**Must not depend on:**
- Shapefile loading or spatial intersection logic directly
- PRIO-GRID geometry details
- The internals of how the lookup table was built

This anchors the class within ADR-002 (topology): it sits at the Pipeline Manager layer, above the enrichment layer, consuming its outputs without knowledge of its internals.

---

## 8. Examples of Correct Usage

```python
from views_pipeline_core.managers.postprocessor import PostprocessorPathManager
from views_postprocessing.unfao.managers.unfao import UNFAOPostProcessorManager

path_manager = PostprocessorPathManager("un_fao")
manager = UNFAOPostProcessorManager(model_path=path_manager)

# Full pipeline execution
manager.execute()

# Or step-by-step
manager._read()
manager._transform()
manager._validate()
manager._save()
```

---

## 9. Examples of Incorrect Usage

- **Calling `_transform()` before `_read()`** — datasets will be None, causing AttributeError
- **Calling `_save()` without `_validate()`** — may upload incomplete data to partners
- **Accessing `_enricher` directly to bypass the enrichment pipeline** — violates the orchestration boundary
- **Hardcoding Appwrite configuration instead of reading from environment** — violates ADR-009

---

## 10. Test Alignment

- **Green tests:** Full pipeline execution with mocked Appwrite; schema compliance of output DataFrames; correct metadata columns present after transform
- **Beige tests:** Missing ensemble name in config; None environment variables; empty forecast bucket; DataFrames with unexpected index structure
- **Red tests:** Corrupted parquet downloads; network timeouts during upload; DataFrames where all cells map to None (all-ocean input)

Currently: **no tests exist** (C-03 in risk register). This contract defines what tests must verify when written.

---

## 11. Evolution Notes

- The pipeline stages (read/transform/validate/save) are **stable** — the interface contract with `PostprocessorManager`
- Partner-specific output formats are **evolving** — the UN FAO schema may change (see C-24, D-06 for schema divergence investigation)
- The source of forecast data (Appwrite bucket/collection) is **evolving** — operational configuration
- Null validation is **active** (C-01 resolved 2026-06-02)
- The enrichment source is the **precomputed GAUL lookup table** (`GaulLookupEnricher`, ADR-011), as of the Stage 3 swap; the runtime mapper (`mapping.py`) remains in the repo but is no longer used by this manager and is slated for removal after one verified production cycle

---

## End of Contract

This document defines the **intended meaning** of `UNFAOPostProcessorManager`.

Changes to behavior that violate this intent are bugs.  
Changes to intent must update this contract.
