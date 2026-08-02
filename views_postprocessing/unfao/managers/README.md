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
`read → transform → validate → save` lifecycle. The representation-free input-integrity
rules live in `views_postprocessing/delivery/` and are **called** by the manager (via the
`contract/frame_extraction.py` seam), never inherited into it.

It is **406 lines**, against a 450-line budget enforced by
`tests/test_doc_accuracy.py::test_the_manager_stays_within_its_line_budget`. It was 636
before #149. ADR-012 deliberately stopped calling it "thin" and states a number instead —
a word nobody can check became a bound a test can.

It is also **the only module in this repository that imports `views_pipeline_core`**, and a
test keeps it that way (register C-40).

It does **not** transform prediction values (no collapse, no reconciliation — those are
downstream). It joins metadata, guards integrity, and delivers.

## Stages

| Stage | Method(s) | What happens |
|-------|-----------|--------------|
| **Read** | `_read_historical_frame`, `_read_forecast_data_contract` | Historical actuals arrive **frame-native** (#126) via the inherited loader; the forecast run is resolved from the Appwrite store by its **run manifest**, and each shard's header is verified on load (`contract/wire/source_selection.py`, ADR-013 §4.3). |
| **Transform** | `_transform` | Resolution only. Metadata is no longer joined onto a pandas frame here — the GAUL columns are attached where each artifact is built. |
| **Validate** | `_validate`, `_check_coverage` | Asserts the read **resolved** (frame + forecast run present), then enforces the region coverage contract (`delivery/coverage.py`, C-34 / C-30). |
| **Save** | `_save` → `_save_contract` | Builds the ADR-013 wire — arrow shards, the §5 GAUL sidecar, the historical artifact — and commits the run **manifest last**. Each upload is stamped with structured provenance (`delivery/provenance.py`, C-15). |

**Where the null-gate went.** It is no longer in `_validate`. The 9 metadata columns are
gated at artifact-build time by `contract/historical.assert_metadata_complete`, and the
forecast's guarantees are the wire's own verified chain: content hashes, header asserts,
per-target coverage inside each lease's `load()`, the §6 no-collapse gate, and gid parity
at `_save`.

The 9 metadata columns are the single-source contract in `contract/gaul_schema.py`
(`COLUMNS` → `METADATA_COLS`, register C-70).

**Retired in #149** (epic #148). Named here deliberately — older issues and PRs still
reference them, and a reader who greps for one deserves an answer rather than a gap:

| retired | what it was | where the work went |
|---|---|---|
| `_append_metadata` <!-- legacy-ok: retirement record --> | the pandas GAUL metadata join | attached per artifact at build time |
| `_clip_observed_history` <!-- legacy-ok: retirement record --> | dropped zero-padded tail months | the rule survives as `delivery/observed_range.py` |
| `_delivery_description` <!-- legacy-ok: retirement record --> | the store-document text | `delivery/provenance.py` |

The pandas delivery path they belonged to is gone. There is one path, and a launcher that
has not declared it is refused by name (`contract/launch_config.py`, register C-63).

## Running it

```python
from views_pipeline_core.managers.postprocessor import PostprocessorPathManager
from views_postprocessing.unfao.managers import UNFAOPostProcessorManager

manager = UNFAOPostProcessorManager(model_path=PostprocessorPathManager("un_fao"))
manager.execute()   # read → transform → validate → save
```

In production this is invoked by **views-models** (`postprocessors/un_fao/main.py`), not
directly. The manager cannot be instantiated without `views-pipeline-core` + Appwrite env,
so its stage logic is covered by source-scan and seam tests rather than by instantiating
it — `tests/test_validation.py`, `tests/test_input_integrity_e2e.py`,
`tests/test_hop_b_sink_e2e.py` and the ADR-013 conformance suite. See the CIC §10.

## Configuration

Appwrite settings are read from the environment and **validated fail-loud before any store
is constructed** — `unfao/appwrite_env.py` declares the required names and refuses a partial
environment, naming every missing variable (þing-01 D6, #134). This package loads no dotenv;
the launcher assembles the environment. The full variable set is documented in the repo
[README](../../../README.md#configuration); note `APPWRITE_PROD_FORECASTS_COLLECTION_ID` is
flagged there as needs-verify (the previously-documented value was found absent in live
Appwrite).

## See also

- [`role_and_seams.md`](../../../docs/architecture/role_and_seams.md) — role + seams
- [CIC: UNFAOPostProcessorManager](../../../docs/CICs/UNFAOPostProcessorManager.md) — class contract
- [CIC: GaulLookupEnricher](../../../docs/CICs/GaulLookupEnricher.md) — the enrichment join
- ADR-011 (mapper → lookup), ADR-012 (current ontology)
