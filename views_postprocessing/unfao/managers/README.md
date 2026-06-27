# UNFAOPostProcessorManager

The manager for the UN FAO delivery: it reads finished VIEWS forecasts + historical
actuals, enriches them with GAUL geographic metadata, enforces input-integrity invariants,
and uploads the result to the FAO Appwrite store.

> For the big picture — how this repo relates to pipeline-core / faoapi / datafactory and
> where its seams are — read [`docs/architecture/role_and_seams.md`](../../../docs/architecture/role_and_seams.md).
> For the class contract (guarantees, failure modes), see the
> [CIC](../../../docs/CICs/UNFAOPostProcessorManager.md). This file is the operational summary.

## What it is

`UNFAOPostProcessorManager` is a **concrete pipeline-core postprocessor** — it subclasses
`PostprocessorManager` + `ForecastingModelManager` (Template Method) and fills the
`read → transform → validate → save` lifecycle. It is a thin orchestrator: the
representation-free input-integrity rules live in `views_postprocessing/delivery/` and are
**called** by the manager (via the `unfao/extraction.py` seam), never inherited into it.

It does **not** transform prediction values (no collapse, no reconciliation — those are
downstream). It joins metadata, guards integrity, and delivers.

## Stages

| Stage | Method(s) | What happens |
|-------|-----------|--------------|
| **Read** | `_read_historical_data`, `_read_forecast_data` | Historical actuals via the inherited `ViewsDataLoader`; the forecast file from the Appwrite prediction store. The selected forecast file's **identity** (name/loa) is asserted before download (`delivery.identity`, C-25). |
| **Transform** | `_transform` → `_append_metadata` | Joins the 9 GAUL metadata columns via `GaulLookupEnricher` (a precomputed parquet lookup, ADR-011). |
| **Validate** | `_validate`, `_check_coverage` | Null-gate on the 9 metadata columns; region **coverage** + GAUL-**excluded-cell** guards (`delivery.coverage`, C-34 / C-30). |
| **Clip** | `_clip_observed_history` | Drops fabricated zero-padded tail months from the *historical* actuals (`delivery.observed_range`, C-26); the forecast is untouched. The boundary (`last_valid_month_id`) is read from the producer (datafactory) via `unfao/source_metadata.py`. |
| **Save** | `_save` | Writes timestamped parquet and uploads to the FAO bucket, stamping each upload with **structured provenance** (`delivery.provenance`, C-15). |

The 9 metadata columns are the single-source contract in `unfao/gaul_schema.py`
(`METADATA_COLS`).

## Running it

```python
from views_pipeline_core.managers.postprocessor import PostprocessorPathManager
from views_postprocessing.unfao.managers import UNFAOPostProcessorManager

manager = UNFAOPostProcessorManager(model_path=PostprocessorPathManager("un_fao"))
manager.execute()   # read → transform → validate → save
```

In production this is invoked by **views-models** (`postprocessors/un_fao/main.py`), not
directly. The manager cannot be instantiated without `views-pipeline-core` + Appwrite env,
so its stage logic is covered by replica tests (`tests/test_validation.py`,
`tests/test_append_metadata.py`) and the input-integrity e2e suite
(`tests/test_input_integrity_e2e.py`) — see the CIC §10.

## Configuration

Appwrite settings are read from the environment via `os.getenv` (no startup validation yet —
tracked in #11). The full variable set is documented in the repo
[README](../../../README.md#configuration); note `APPWRITE_PROD_FORECASTS_COLLECTION_ID` is
flagged there as needs-verify (the previously-documented value was found absent in live
Appwrite).

## See also

- [`role_and_seams.md`](../../../docs/architecture/role_and_seams.md) — role + seams
- [CIC: UNFAOPostProcessorManager](../../../docs/CICs/UNFAOPostProcessorManager.md) — class contract
- [CIC: GaulLookupEnricher](../../../docs/CICs/GaulLookupEnricher.md) — the enrichment join
- ADR-011 (mapper → lookup), ADR-012 (current ontology)
