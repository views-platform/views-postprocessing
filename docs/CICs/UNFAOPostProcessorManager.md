
# Class Intent Contract: UNFAOPostProcessorManager

**Status:** Active  
**Owner:** PRIO MD&D Team  
**Last reviewed:** 2026-08-05  
**Related ADRs:** ADR-001, ADR-002, ADR-008, ADR-009  

---

> **Corrected 2026-08-03 — this document named a collaborator the manager has never
> called.** Six statements described enrichment as delegated to `GaulLookupEnricher`, <!-- legacy-ok: the 2026-08-03 correction note; naming the error is the record -->
> one naming the call `GaulLookupEnricher.enrich_dataframe_with_pg_info()`. The manager <!-- legacy-ok: the 2026-08-03 correction note; naming the error is the record -->
> contains **zero** references to it — `tests/test_gaul_lookup_access.py` actively
> asserts its absence — and the sibling CIC has long said *"the manager does not call
> this class."* Two contract documents asserted opposite things about the same call.
> Geography is attached by `contract/historical.py` and `contract/wire/sidecar.py` from
> a lookup the manager loads once per delivery. See register **C-75**.
>
> Five further claims in this file described deleted code and are corrected below:
> a `dotenv` load that no longer happens, a "known gap" in env validation that
> `assert_env_declared` closed, an upload count and file type that were wrong in three
> ways, a selection precondition weaker than `source_selection` enforces, and two
> "incorrect usage" examples for code paths that no longer exist.

## 1. Purpose

> **What is this class for?**

`UNFAOPostProcessorManager` orchestrates the end-to-end postprocessing pipeline that reads VIEWS conflict predictions, enriches them with geographic metadata from the precomputed GAUL lookup (ADR-011), validates the output schema, and delivers the enriched data to the UN FAO via Appwrite cloud storage.

It is the single entrypoint for producing and delivering UN FAO-formatted prediction data.

---

## 2. Non-Goals (Explicit Exclusions)

- This class does **not** perform spatial mapping logic — it reads the precomputed GAUL lookup (`contract/gaul_lookup.load()`) and the artifact builders attach geography from it
- This class does **not** train, evaluate, or modify prediction models
- This class does **not** define the spatial assignment algorithm
- This class does **not** manage shapefile data or geographic reference assets
- This class does **not** validate the correctness of spatial assignments — only their presence

---

## 3. Responsibilities and Guarantees

- Guarantees a 4-stage pipeline: read → transform → validate → save
- Guarantees that historical data is sourced from ViewsER via `ViewsDataLoader`
- Guarantees that forecast data is sourced from the Appwrite production forecasts bucket
- Guarantees that geographic metadata is attached from the precomputed lookup — by `contract/historical.py` for the historical artifact and `contract/wire/sidecar.py` for the §5 GAUL sidecar, each a keyed gather on cell id
- Guarantees that required metadata columns are validated before upload
- Guarantees that both historical and forecast datasets are uploaded to the UN FAO Appwrite bucket with correct metadata (name, loa, type, category)
- Logs structural failures before raising them (ADR-008): the config/`loa` guards, the `_validate` gates, and the dataset/`_save` guard all `logger.error`-then-raise (#13 / C-19 resolved); the `delivery/` invariants raise representation-free, with the manager logging context at each call site

---

## 4. Inputs and Assumptions

- Requires a `PostprocessorPathManager` at initialization pointing to valid model paths
- Requires `configs` dict to contain an `ensemble` key naming the source ensemble
- Requires environment variables for Appwrite connectivity (endpoint, project ID, API key, bucket/collection IDs)
- Requires the Appwrite production forecasts bucket to contain a **complete run**: a manifest matching `{category: "forecast", type: "sampled_forecast_manifest"}`, a manifest per declared target, and every shard those manifests name. A bucket holding merely *some* `category="forecast"` file raises `SourceSelectionError` (`contract/wire/source_selection.py`)
- Requires the precomputed GAUL lookup parquet to be present; it is read once per delivery via `contract/gaul_lookup.load()`

Assumptions that are not met **must cause failure**, not fallback behavior. The environment is validated fail-loud: `appwrite_env.assert_env_declared` runs before **both** `AppwriteConfig` constructions and names every missing variable, and an empty string counts as missing. *(This paragraph previously described that as a "known gap" with `os.getenv()` passing `None` through unchecked; C-19 closed it, and `tests/test_env_declaration.py` pins it.)*

---

## 5. Outputs and Side Effects

**Outputs:**
- `_historical_frame`: the historical actuals as a `views_frames.FeatureFrame` (#126). Geography is **not** joined into it — it attaches at artifact build (`contract/historical.py`)
- `_forecast_resolution`: `{target: TargetLease}` — the resolved run. Manifests and pinned shard ids only; frames materialise one target at a time inside the sink (the run-0 OOM fix)

**Side Effects:**
- Downloads data from ViewsER (network I/O)
- Downloads forecast data from Appwrite (network I/O)
- Writes timestamped parquet files to `data_generated/` directory
- Uploads to the UN FAO Appwrite bucket (network I/O) — **only when the §11.4 interlock is open**. `product.UPLOAD_ENABLED` is `False` by default, and the sink then makes **zero** store calls. Enabled, a run uploads one parquet per (target, month) — 108 at run-0 — plus the GAUL sidecar parquet, the historical parquet, and a **JSON** run manifest, committed last. Forecast-leg documents carry `{name, category, loa, filename, doc_type, targets}` and no `description`; only the historical artifact carries structured provenance
- Logs pipeline progress at INFO/ERROR levels

---

## 6. Failure Modes and Loudness

- **Missing `ensemble` config key:** Raises `ValueError` with descriptive message
- **Appwrite download failure:** Logs ERROR with full exception, then re-raises
- **Missing required metadata columns after enrichment:** Raises `ValueError` listing missing columns
- **Null values in required metadata columns:** Raises `ValueError` with null count and affected column name (C-01 resolved — validation active)
- **Dataset initialization failure:** Raises `ValueError` in `_save()` if datasets are None
- **Appwrite upload failure:** Propagates exception from `DatastoreModule`
- **Wrong forecast selected:** structurally impossible since #149. Selection is by **run manifest** — a commit marker whose contents are hash-verified — not by scanning the bucket for the newest `category="forecast"` upload. Declared identity is additionally checked **per shard header** against the launched ensemble inside `TargetLease.load()` (`contract/wire/source_selection.py:73-81`), so identity comes from the artifact's own content. The metadata-field check this bullet used to describe (`delivery/identity.py`) was retired in #150 and the legacy reader it served in #149; register C-25 is closed as *superseded by mechanism* <!-- legacy-ok: retirement record -->
- **Launch config incomplete:** raises `LaunchConfigError` naming the missing key. A launcher that omits `wire_contract` or declares a `data_format` other than `feature_frame` is **refused**, never quietly routed into a fallback (ADR-003, register C-63)
- **Region coverage mismatch:** Raises `CoverageError` in `_check_coverage()` (called from `_validate()`) if a pinned region's delivered cell count is wrong (S1/C-34) or a GAUL-uncovered excluded cell leaks into the delivery (S4/C-30)
- **Fabricated historical tail:** `_read_historical_frame()` drops months beyond the producer's `last_valid_month_id` at the read (`_clip_observed_history` was the pandas equivalent, retired with that path in #149) so unobserved zero-padding is not shipped as observed history (S2/C-26); **degrades open** (skips the clip with a WARNING) if the boundary cannot be resolved <!-- legacy-ok: retirement record -->
- **Upload provenance:** the historical artifact's `description` carries structured provenance (lookup version, region, expected/actual cell counts, unmapped count) built by `delivery/provenance.py` (`build_provenance` → `compact_description`) via the manager's `_historical_frame_description()` (S5/C-15). The **forecast** side carries no such description: its guarantee is the wire's verified chain — per-shard content hashes recorded in the §4.2 run manifest, header asserts on load, and manifest-last commit ordering. That is identity and integrity, not the C-15 provenance field set; the §4.2 manifest's keys are exactly `contract_version`, `run_id`, `targets`, `shards`, `expected_months`, `expected_cell_count`, `sidecar` — and it carries **no** `lookup_version`, `region` or `unmapped_count`. `_delivery_description()` was the pandas-path equivalent and was deleted with it in #149 <!-- legacy-ok: retirement record -->

The following **must never** fail silently:
- Missing or None environment variables for Appwrite
- Network failures during download or upload
- Schema validation failures (missing columns or null values)
- A forecast file whose identity does not match the configured ensemble (S3/C-25)
- Wrong region coverage or a leaked GAUL-uncovered cell (S1/C-34, S4/C-30)

---

## 7. Boundaries and Interactions

**Allowed interactions:**
- Reads the precomputed GAUL lookup once and passes it to the artifact builders, which attach geography
- Uses `views-pipeline-core` managers for path resolution, data loading, and Appwrite integration
- Reads environment variables for external service configuration
- Writes to local filesystem and Appwrite cloud storage

**Must not depend on:**
- Shapefile loading or spatial intersection logic directly
- PRIO-GRID geometry details
- The internals of how the lookup table was built

This anchors the class within ADR-002 (topology): `unfao/` → `contract/` → `delivery/`, one way only — and since #211 the same holds for `crafd/`, the second partner package. It is one of **the repository's only two importers of `views_pipeline_core`** (both mechanically pinned to an allowlist by `tests/test_doc_accuracy.py`), which keeps C-40's blast radius at one file per partner. Not yet *thin*: it came down from 636 lines at epic #148 and now sits just under a **450-line budget**, which `tests/test_doc_accuracy.py` applies to the whole `managers/` directory of each partner rather than to this file alone — a seam that holds its line count by moving 800 lines into a sibling module has not held anything. The exact figure is deliberately not repeated here; the test carries it.

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

- **Calling `_save()` without `_validate()`** — may upload incomplete data to partners
- **Hardcoding Appwrite configuration instead of reading from environment** — violates ADR-009
- **Reaching past the manager into `contract/` to publish** — the sink is driven through
  `_ContractStorePort` so the store is one seam; bypassing it also bypasses the
  `result.success` check that turns a partial upload into a refusal

*(Two entries were removed here on 2026-08-03 because they described code that no longer
exists: "calling `_transform()` before `_read()`" — `_transform` is a documented no-op
that cannot raise — and "accessing `_enricher` directly", an attribute removed in #152
/ C-66.)*

---

## 10. Test Alignment

- **Green tests:** Full pipeline execution with mocked Appwrite; schema compliance of output DataFrames; correct metadata columns present after transform
- **Beige tests:** Missing ensemble name in config; None environment variables; empty forecast bucket; DataFrames with unexpected index structure
- **Red tests:** Corrupted parquet downloads; network timeouts during upload; DataFrames where all cells map to None (all-ocean input)

Currently: the manager cannot be instantiated without `views-pipeline-core`, so its stage logic is covered by **source-scan and seam tests** — `tests/test_validation.py` (the metadata null-gate, tested against `contract/historical.assert_metadata_complete` where it fires, plus pins that it has not drifted back into `_validate`), `tests/test_launch_config.py` (the refusals), `tests/test_gaul_lookup_access.py` (one lookup read, threaded). There is no longer a replica of any manager method: `tests/test_validation.py` held one until S4 (#185) and it had diverged from `_validate` since #149, while `tests/test_append_metadata.py` was deleted in #149 with the method it mirrored. <!-- legacy-ok: retirement record --> A full end-to-end test against the **live manager** still requires a production-like environment and is tracked as **#18**; **þing-01 D2** forbids *integration* tests against the production Appwrite project while no non-production one exists — conditionally, and it **permits read-only preflight validation** (register C-95, C-96).

The input-integrity guards (S0–S6, epic #51) are representation-free invariants in `views_postprocessing/delivery/` that the manager **calls** (never inherits). Each has primitives unit tests — `tests/test_delivery_coverage.py` (S1/S4), `tests/test_delivery_observed_range.py` (S2), `tests/test_provenance.py` (S5), `tests/test_frame_extraction.py` (the seam), `tests/test_store_metadata.py` (store identity) — and `tests/test_input_integrity_e2e.py` drives the invariants on **primitives**, which is how the manager calls them. S3's forecast-identity rule moved to the wire layer (#150) and is covered by `tests/test_wire_source_selection.py`. The design contract (representation-free, called-not-inherited) is pinned by `tests/test_input_integrity_design_contract.py`.

---

## 11. Evolution Notes

- The pipeline stages (read/transform/validate/save) are **stable** — the interface contract with `PostprocessorManager`
- Partner-specific output formats are **evolving** — the UN FAO schema may change (see C-24, D-06 for schema divergence investigation)
- The source of forecast data (Appwrite bucket/collection) is **evolving** — operational configuration
- Null validation is **active** (C-01 resolved 2026-06-02)
- The enrichment source is the **precomputed GAUL lookup table** (`views_postprocessing/data/gaul_lookup.parquet`, ADR-011), as of the Stage 3 swap; the old runtime mapper was **removed** (C-39 / PR #42) — it no longer exists in the repo

---

## End of Contract

This document defines the **intended meaning** of `UNFAOPostProcessorManager`.

Changes to behavior that violate this intent are bugs.  
Changes to intent must update this contract.
