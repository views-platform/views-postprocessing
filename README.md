# views-postprocessing

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Poetry](https://img.shields.io/badge/dependency%20management-poetry-blueviolet)](https://python-poetry.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

The **post-forecast delivery layer** for the **VIEWS** (Violence Early-Warning System)
pipeline. It takes finished VIEWS forecasts, enriches them with geographic metadata,
guards their integrity, and delivers them to a partner store.

The only live delivery today is the **UN FAO** path — its product in `views_postprocessing/unfao/`, running on the partner-neutral machinery in `contract/`.

> **New here? Read [`docs/architecture/role_and_seams.md`](docs/architecture/role_and_seams.md) first.**
> It explains what this repo is, how it relates to pipeline-core / faoapi / datafactory,
> and where its internal seams are. This README is install + quickstart only.

---

## What this is (and isn't)

- **It is** a concrete **pipeline-core postprocessor**: `UNFAOPostProcessorManager`
  subclasses pipeline-core's `PostprocessorManager` and fills the post-forecast lifecycle
  (`read → transform → validate → save`) for the FAO partner.
- **It enriches and delivers** — it joins GAUL administrative metadata onto predictions
  (via a precomputed lookup, **ADR-011**) and enforces input-integrity invariants before
  upload.
- **It is *not*** a spatial-mapping library (the old runtime spatial mapper was removed —
  see ADR-011 / C-39) and **not** a statistical post-processor. Draw-collapse (MAP/HDI) happens
  downstream in views-faoapi; reconciliation lives in `views_frames_reconcile`. See the
  orientation doc.

---

## Installation

```bash
# With Poetry (recommended)
git clone https://github.com/views-platform/views-postprocessing.git
cd views-postprocessing
poetry install

# Or with pip
pip install views-postprocessing
```

Requires **Python 3.11–3.14**.

### Dependencies

| Package | Version | Why |
|---------|---------|-----|
| `views-pipeline-core` | `>=2.1.3,<3.0.0` | The framework: lifecycle base classes, data loader, dataset container, Appwrite/datastore tools |
| `views-frames` | `>=1.0,<2` | The frame data contract — **the live delivery representation** since #126. pandas survives only in `contract/enrichment.py` (the build/verification path) |

---

## The UN FAO delivery

```python
from views_pipeline_core.managers.postprocessor import PostprocessorPathManager
from views_postprocessing.unfao.managers.unfao import UNFAOPostProcessorManager

path_manager = PostprocessorPathManager("un_fao")
manager = UNFAOPostProcessorManager(model_path=path_manager)
manager.execute()   # read → transform → validate → save
```

In practice the manager is constructed and run by **views-models**
(`postprocessors/un_fao/main.py`), not invoked directly.

### Pipeline stages

| Stage | Method(s) | What happens |
|-------|-----------|--------------|
| **Read** | `_read_historical_frame`, `_read_forecast_data_contract` | Historical actuals from views-datafactory arrive **frame-native** (#126); the forecast run is resolved from the Appwrite store by its **run manifest**, with each shard's header verified on load (ADR-013 §4.3). |
| **Transform** | `_transform` | Resolution only. Prediction values are **not** transformed — no collapse, no reconciliation. |
| **Validate** | `_validate`, `_check_coverage` | Asserts the read resolved, then enforces the region coverage + GAUL-excluded-cell contract (C-34 / C-30). The metadata null-gate fires later, at artifact build (`contract/historical.assert_metadata_complete`). |
| **Save** | `_save` → `_save_contract` | Builds the ADR-013 wire — arrow shards, the §5 GAUL sidecar, the historical artifact — commits the run **manifest last**, and stamps each upload with structured provenance (C-15). |

The pandas metadata-join and history-clip stages were retired with the legacy delivery path
in #149; their rules survive as called invariants under `delivery/`. See the
[manager README](views_postprocessing/unfao/managers/README.md) for what moved where.

### Output schema (geographic metadata columns)

These 9 columns are the delivered geography contract (declared in `contract/gaul_schema.py`):

| Column | Type | Description |
|--------|------|-------------|
| `pg_xcoord` | float | PRIO-GRID cell centroid longitude |
| `pg_ycoord` | float | PRIO-GRID cell centroid latitude |
| `country_iso_a3` | str | ISO 3166-1 alpha-3 country code |
| `admin1_gaul0_code` | int | GAUL level-0 (country) code |
| `admin1_gaul0_name` | str | GAUL level-0 (country) name |
| `admin1_gaul1_code` | int | GAUL level-1 (province) code |
| `admin1_gaul1_name` | str | GAUL level-1 (province) name |
| `admin2_gaul2_code` | int | GAUL level-2 (district) code |
| `admin2_gaul2_name` | str | GAUL level-2 (district) name |

---

## Package structure

```
views-postprocessing/
├── pyproject.toml
├── README.md
├── docs/
│   ├── architecture/role_and_seams.md   # READ FIRST — role + seams
│   ├── ADRs/                             # decisions + rationale
│   └── CICs/                             # class-level contracts
└── views_postprocessing/
    ├── delivery/                 # WHAT MAKES A DELIVERY VALID — representation-free
    │   ├── coverage.py             # region cell-count + excluded-cell guards
    │   ├── draws.py                # the §6 no-collapse gate
    │   ├── parity.py               # sidecar covers exactly the forecast's cells
    │   ├── observed_range.py       # fabricated-month decision
    │   └── provenance.py           # structured upload provenance
    ├── contract/                 # HOW A DELIVERY IS BUILT — partner-neutral
    │   ├── wire/                    # the ADR-013 contract (header, shard, sidecar,
    │   │                            #   run_manifest, sink, source_selection, naming)
    │   ├── frames.py                # PredictionFrame / TargetFrame constructors
    │   ├── frame_extraction.py      # THE representation seam (frame → primitives)
    │   ├── track_a_source.py        # Hop-A archive → frame
    │   ├── historical.py            # the historical artifact, built pandas-free
    │   ├── gaul_lookup.py           # the GAUL asset: path, version, one read
    │   ├── gaul_schema.py           # the 9-column contract, declared as data
    │   ├── enrichment.py            # GaulLookupEnricher (build/verification path)
    │   ├── source_metadata.py       # producer (datafactory) facts
    │   ├── store_metadata.py        # prediction-store facts
    │   └── launch_config.py         # the delivery mode the launcher must declare
    ├── unfao/                    # WHO A DELIVERY IS FOR — the only FAO-specific code
    │   ├── product.py               # targets, consumer name, S_MIN, upload interlock
    │   ├── appwrite_env.py          # the declared store coordinates
    │   └── managers/unfao.py        # UNFAOPostProcessorManager
    └── data/gaul_lookup.parquet  # the precomputed GAUL lookup (ADR-011)
```

**Dependencies point one way only:** `unfao/` → `contract/` → `delivery/`. Nothing in
`contract/` may import `unfao/` — that is what lets a new partner reuse the machinery
without inheriting FAO, and it is enforced by `tests/test_clone_readiness.py`, not by
convention. See [`docs/CLONING.md`](docs/CLONING.md).

---

## Configuration

The FAO delivery reads Appwrite connection settings from the environment. The required
names are **declared** in `unfao/appwrite_env.py` and validated fail-loud before any store
is constructed — a missing or empty variable raises, naming every one that is absent,
rather than half-configuring a client. Coordinates come from the Appwrite Seam Contract registry
(referenced by URL, never copied); the API key is an operator slot:

```bash
# Appwrite connection (secrets)
APPWRITE_ENDPOINT=https://cloud.appwrite.io/v1
APPWRITE_DATASTORE_PROJECT_ID=...
APPWRITE_DATASTORE_API_KEY=...

# Production-forecasts store (input)
APPWRITE_PROD_FORECASTS_BUCKET_ID=production_forecasts
APPWRITE_PROD_FORECASTS_BUCKET_NAME=Production Forecasts
APPWRITE_PROD_FORECASTS_COLLECTION_ID=production_forecasts
APPWRITE_PROD_FORECASTS_COLLECTION_NAME=Production Forecasts

# UN FAO store (output)
APPWRITE_UNFAO_BUCKET_ID=...
APPWRITE_UNFAO_BUCKET_NAME=...
APPWRITE_UNFAO_COLLECTION_ID=...
APPWRITE_UNFAO_COLLECTION_NAME=...

# Metadata database
APPWRITE_METADATA_DATABASE_ID=...
APPWRITE_METADATA_DATABASE_NAME=...
```

---

## Documentation

| Doc | What it covers |
|-----|----------------|
| [`docs/architecture/role_and_seams.md`](docs/architecture/role_and_seams.md) | **Start here** — role vs the sibling repos + internal seams |
| [`docs/ADRs/`](docs/ADRs/) | Architecture decisions (esp. ADR-011 mapper→lookup; ADR-012 ontology) |
| [`docs/CICs/`](docs/CICs/) | Class intent contracts (`UNFAOPostProcessorManager`, `GaulLookupEnricher`) |
| `reports/technical_risk_register.md` | Tracked risks — C-40 (the remaining pipeline-core inheritance), C-30/C-15 (delivery guards), C-43 (enrichment value verification) |

---

## Contributing

1. Branch off `development`.
2. Make the change; keep `ruff` and the test suite green (`ruff check . && PYTHONPATH=. pytest -q`).
3. Open a PR into `development`.

Contributor protocols (incl. the conventions for AI agents) are under
[`docs/contributor_protocols/`](docs/contributor_protocols/).

---

## License

MIT — part of the VIEWS platform developed at the **Peace Research Institute Oslo (PRIO)**.
See [LICENSE](LICENSE).

---

## Related packages

| Package | Role |
|---------|------|
| [`views-pipeline-core`](https://github.com/views-platform/views-pipeline-core) | The framework this repo extends |
| [`views-datafactory`](https://github.com/views-platform/views-datafactory) | Produces the data this repo consumes |
| [`views-faoapi`](https://github.com/views-platform/views-faoapi) | Serves the delivered FAO data (and collapses draws) |
| [`views-frames`](https://github.com/views-platform/views-frames) | The frame data contract + `views_frames_summarize` / `views_frames_reconcile` |
