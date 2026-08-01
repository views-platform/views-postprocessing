
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
- Logs structural failures before raising them (ADR-008): the config/`loa` guards, the `_validate` gates, and the dataset/`_save` guard all `logger.error`-then-raise (#13 / C-19 resolved); the `delivery/` invariants raise representation-free, with the manager logging context at each call site

---

## 4. Inputs and Assumptions

- Requires a `PostprocessorPathManager` at initialization pointing to valid model paths
- Requires `configs` dict to contain an `ensemble` key naming the source ensemble
- Requires environment variables for Appwrite connectivity (endpoint, project ID, API key, bucket/collection IDs)
- Requires the ensemble's `.env` file to be loadable via `dotenv`
- Requires the Appwrite production forecasts bucket to contain at least one file with `category="forecast"`
- Requires the precomputed GAUL lookup parquet to be present so `GaulLookupEnricher` can load it at construction

Assumptions that are not met **must cause failure**, not fallback behavior. **Known gap:** the Appwrite env vars are read via `os.getenv()` without a startup validation — a missing var yields `None`, which is passed to `AppwriteConfig` unchecked rather than failing loud at the boundary (tracked by **C-19-adjacent / #11**; a fail-loud env check is the cheap fix).

---

## 5. Outputs and Side Effects

**Outputs:**
- `_historical_frame`: the historical actuals as a `views_frames.FeatureFrame` (#126). Geography is **not** joined into it — it attaches at artifact build (`contract/historical.py`)
- `_forecast_resolution`: `{target: TargetLease}` — the resolved run. Manifests and pinned shard ids only; frames materialise one target at a time inside the sink (the run-0 OOM fix)

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
- **Wrong forecast selected:** structurally impossible since #149. Selection is by **run manifest** — a commit marker whose contents are hash-verified — not by scanning the bucket for the newest `category="forecast"` upload. Declared identity is additionally checked **per shard header** against the launched ensemble inside `TargetLease.load()` (`contract/wire/source_selection.py:73-81`), so identity comes from the artifact's own content. The metadata-field check this bullet used to describe (`delivery/identity.py`) was retired in #150 and the legacy reader it served in #149; register C-25 is closed as *superseded by mechanism*
- **Launch config incomplete:** raises `LaunchConfigError` naming the missing key. A launcher that omits `wire_contract` or declares a `data_format` other than `feature_frame` is **refused**, never quietly routed into a fallback (ADR-003, register C-63)
- **Region coverage mismatch:** Raises `CoverageError` in `_check_coverage()` (called from `_validate()`) if a pinned region's delivered cell count is wrong (S1/C-34) or a GAUL-uncovered excluded cell leaks into the delivery (S4/C-30)
- **Fabricated historical tail:** `_read_historical_frame()` drops months beyond the producer's `last_valid_month_id` at the read (`_clip_observed_history` was the pandas equivalent, retired with that path in #149) so unobserved zero-padding is not shipped as observed history (S2/C-26); **degrades open** (skips the clip with a WARNING) if the boundary cannot be resolved
- **Upload provenance:** every upload's `description` carries structured provenance (lookup version, region, expected/actual cell counts, unmapped count) via `_delivery_description()` (S5/C-15)

The following **must never** fail silently:
- Missing or None environment variables for Appwrite
- Network failures during download or upload
- Schema validation failures (missing columns or null values)
- A forecast file whose identity does not match the configured ensemble (S3/C-25)
- Wrong region coverage or a leaked GAUL-uncovered cell (S1/C-34, S4/C-30)

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

This anchors the class within ADR-002 (topology): `unfao/` → `contract/` → `delivery/`, one way only. It is **the repository's only importer of `views_pipeline_core`** (mechanically pinned by `tests/test_doc_accuracy.py`), which is what makes C-40's blast radius one file wide. 406 lines as of epic #148, down from 636 — not yet *thin*, and held under a 450-line budget by the same test.

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

Currently: the manager cannot be instantiated without `views-pipeline-core`, so its stage logic is covered by **source-scan and replica tests** — `tests/test_validation.py`, `tests/test_launch_config.py` (the refusals), `tests/test_gaul_lookup_access.py` (one lookup read, threaded). `tests/test_append_metadata.py` was deleted in #149 with the method it mirrored. A full end-to-end test against the live manager (C-03) still requires a production-like environment.

The input-integrity guards (S0–S6, epic #51) are representation-free invariants in `views_postprocessing/delivery/` that the manager **calls** (never inherits). Each has primitives unit tests — `tests/test_delivery_coverage.py` (S1/S4), `tests/test_delivery_observed_range.py` (S2), `tests/test_provenance.py` (S5), `tests/test_frame_extraction.py` (the seam), `tests/test_store_metadata.py` (store identity) — and `tests/test_input_integrity_e2e.py` drives the invariants on **primitives**, which is how the manager calls them. S3's forecast-identity rule moved to the wire layer (#150) and is covered by `tests/test_wire_source_selection.py`. The design contract (representation-free, called-not-inherited) is pinned by `tests/test_input_integrity_design_contract.py`.

---

## 11. Evolution Notes

- The pipeline stages (read/transform/validate/save) are **stable** — the interface contract with `PostprocessorManager`
- Partner-specific output formats are **evolving** — the UN FAO schema may change (see C-24, D-06 for schema divergence investigation)
- The source of forecast data (Appwrite bucket/collection) is **evolving** — operational configuration
- Null validation is **active** (C-01 resolved 2026-06-02)
- The enrichment source is the **precomputed GAUL lookup table** (`GaulLookupEnricher`, ADR-011), as of the Stage 3 swap; the old runtime mapper was **removed** (C-39 / PR #42) — it no longer exists in the repo

---

## End of Contract

This document defines the **intended meaning** of `UNFAOPostProcessorManager`.

Changes to behavior that violate this intent are bugs.  
Changes to intent must update this contract.
