# views-postprocessing

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Poetry](https://img.shields.io/badge/dependency%20management-poetry-blueviolet)](https://python-poetry.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

The **post-forecast delivery layer** for the **VIEWS** (Violence Early-Warning System)
pipeline. It takes finished VIEWS forecasts, enriches them with geographic metadata,
guards their integrity, and delivers them to a partner store.

Two partner deliveries run on the same partner-neutral machinery in `contract/`: the **UN FAO** path (`views_postprocessing/unfao/`), serving FAO-FSFC since 2026-07-27, and **CRAF'd** (`views_postprocessing/crafd/`), added 2026-08-03 with its upload interlock still closed.

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

Requires **Python 3.11**, and only 3.11.

`pyproject.toml` still declares `>=3.11,<3.15`. **That declaration is wrong** and is
tracked as **#295**: the lockfile resolves on 3.11 alone, because `ingester3` caps
`levenshtein >=0.20,<0.21` and no release in that range publishes a 3.12+ wheel.
Measured 2026-08-25 against the index. CI and the delivery's own environment both run
3.11, so nothing in production is affected — the cost is that a contributor arriving on
3.12 or 3.13 is told the project supports them and then cannot install it.

Narrowing the declaration is a one-line edit that invalidates `poetry.lock` and forces a
full re-resolve, which would move `pyarrow` off the 16.1.0 the ADR-013 §10 byte-parity
fixtures are pinned to (C-72). So it is #295's own change, not a documentation fix.

### Dependencies

| Package | Version | Why |
|---------|---------|-----|
| `views-pipeline-core` | `>=3.0.0,<4.0.0` (with the `appwrite` extra) | The framework: lifecycle base classes, data loader, dataset container, Appwrite/datastore tools |
| `views-frames` | `>=1.10.2,<2` | The frame data contract — **the live delivery representation** since #126. There is no pandas in this package at all since #90 |
| `pyarrow` | `>=16.1.0,<17.0.0` | The wire's serialisation. **Pinned deliberately** — the CVE fix past 17 changes delivered bytes (register C-72) |
| *dev group* | `pytest`, `ruff` | Not installed by `pip install views-postprocessing`; `poetry install` includes them |

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
| **Save** | `_save` → `_save_contract` | Builds the ADR-013 wire — arrow shards, the §5 GAUL sidecar, the historical artifact — commits the run **manifest last**. The historical artifact carries structured provenance in its store-document `description` (C-15); the forecast leg's uploads carry `{name, category, loa, filename, doc_type, targets}` and **no `description`** — a gap, not a design. |

The pandas metadata-join and history-clip stages were retired with the legacy delivery path
in #149; their rules survive as called invariants under `delivery/`. See the
[manager README](views_postprocessing/unfao/managers/README.md) for what moved where.

### If a delivered value turns out to be wrong

`docs/operations/correction_procedure.md` — how to establish which deliveries are
affected, confirm the fault offline, and supersede on the wire. The contract has no
retraction primitive; a correction is a new complete run, manifest last.

### If a delivery fails loudly

Since **1.2.0** a run can stop in ways it previously would not, and each one replaces a
silent failure with a refusal. A launcher may see:

| exception | what it means |
|---|---|
| `DeliveryNotFindableError` | the upload succeeded but the consumer's own query does not find **this** run — the failure where every call reports success and the partner sees nothing |
| `FindabilityUnverifiedError` | the check above could not run; *"could not ask"* is deliberately not *"asked and got nothing"* |
| `ProducerClientUnavailable` | the producer client would not load, so the observed-data boundary is unknown. Refuses rather than shipping the unobserved tail as observed history |
| `TornRunError` | a run failed partway through uploading. Names every object confirmed uploaded and the one that failed; deletes nothing |

If one fires after an upgrade it is reporting a condition that was already wrong and
already invisible. [`CHANGELOG.md`](CHANGELOG.md) carries the detail.

### Output schema (geographic metadata columns)

These 9 columns are the delivered geography contract, declared in
`contract/gaul_schema.py`. **The order below is normative** (ADR-013 §5.1) and is
byte-pinned by the §10 golden fixture — a reader that reorders them reads the wrong
column. `tests/test_doc_accuracy.py` checks this table against the declaration.

| Column | Wire type | Description |
|--------|-----------|-------------|
| `pg_xcoord` | float64 | PRIO-GRID cell centroid longitude |
| `pg_ycoord` | float64 | PRIO-GRID cell centroid latitude |
| `country_iso_a3` | string | ISO 3166-1 alpha-3 country code |
| `admin1_gaul1_code` | float64 | GAUL level-1 (province) code |
| `admin1_gaul1_name` | string | GAUL level-1 (province) name |
| `admin1_gaul0_code` | float64 | GAUL level-0 (country) code |
| `admin1_gaul0_name` | string | GAUL level-0 (country) name |
| `admin2_gaul2_code` | float64 | GAUL level-2 (district) code |
| `admin2_gaul2_name` | string | GAUL level-2 (district) name |

*(Corrected 2026-08-03: this table had `admin1_gaul0_*` before `admin1_gaul1_*` —
the reverse of the normative order — and typed the four `*_code` columns `int`. They
are **float64 on the wire, always**, by the §5.1 ruling: the codes are nullable and
arrow has no nullable int in this contract. Both errors survived because nothing
compared the table to the declaration.)*

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
    │   ├── provenance.py           # structured upload provenance
    │   └── findability.py          # does the consumer's query find THIS run?
    ├── contract/                 # HOW A DELIVERY IS BUILT — partner-neutral
    │   ├── wire/                    # the ADR-013 contract (header, shard, sidecar,
    │   │                            #   run_manifest, sink, source_selection, naming)
    │   ├── frames.py                # PredictionFrame / TargetFrame constructors
    │   ├── frame_extraction.py      # THE representation seam (frame → primitives)
    │   ├── track_a_source.py        # Hop-A archive → frame
    │   ├── historical.py            # the historical artifact, built pandas-free
    │   ├── gaul_lookup.py           # the GAUL asset: path, version, one read
    │   ├── gaul_schema.py           # the 9-column contract, declared as data
    │   ├── source_metadata.py       # producer (datafactory) facts
    │   ├── store_metadata.py        # prediction-store facts
    │   └── launch_config.py         # the delivery mode the launcher must declare
    ├── unfao/                    # WHO A DELIVERY IS FOR — the FAO-specific code
    │   ├── product.py               # targets, consumer name, S_MIN, upload interlock
    │   ├── appwrite_env.py          # the declared store coordinates
    │   └── managers/unfao.py        # UNFAOPostProcessorManager
    ├── crafd/                    # WHO A DELIVERY IS FOR — the CRAF'd-specific code
    │   ├── product.py               # same three files, same shape (register C-33 on
    │   ├── appwrite_env.py          #   why the manager is a copy, and what would
    │   └── managers/crafd.py        #   make it time to stop copying)
    └── data/gaul_lookup.parquet  # the precomputed GAUL lookup (ADR-011)
```

**Dependencies point one way only:** `<partner>/` → `contract/` → `delivery/`. Nothing
in `contract/` may import a partner package — that is what lets a new partner reuse the
machinery without inheriting another partner's product, and it is enforced by
`tests/test_clone_readiness.py`, not by convention. The partner list lives in one place
(`tests/conftest.py`) and is itself checked against the filesystem, so a package added
without being declared fails rather than passing quietly.
See [`docs/CLONING.md`](docs/CLONING.md).

---

## Configuration

Each delivery reads Appwrite connection settings from the environment. The required
names are **declared** per partner — `unfao/appwrite_env.py`, `crafd/appwrite_env.py` —
and validated fail-loud before any store is constructed: a missing or empty variable
raises, naming every one that is absent, rather than half-configuring a client.

**The names are below; the values are not.** Coordinates live in the Appwrite Seam
Contract's registry, which this repo references by pinned URL and never copies (þing-01
sáttmál S6 — copies were the platform's original failure). The launcher supplies the
values; the API key is an operator slot.

```bash
# Appwrite connection
APPWRITE_ENDPOINT=...
APPWRITE_DATASTORE_PROJECT_ID=...
APPWRITE_DATASTORE_API_KEY=...        # operator-issued secret

# Production-forecasts store (input — shared by every partner)
APPWRITE_PROD_FORECASTS_BUCKET_ID=...
APPWRITE_PROD_FORECASTS_BUCKET_NAME=...
APPWRITE_PROD_FORECASTS_COLLECTION_ID=...
APPWRITE_PROD_FORECASTS_COLLECTION_NAME=...

# UN FAO store (output)
APPWRITE_UNFAO_BUCKET_ID=...
APPWRITE_UNFAO_BUCKET_NAME=...
APPWRITE_UNFAO_COLLECTION_ID=...
APPWRITE_UNFAO_COLLECTION_NAME=...

# CRAF'd store (output)
APPWRITE_CRAFD_BUCKET_ID=...
APPWRITE_CRAFD_BUCKET_NAME=...
APPWRITE_CRAFD_COLLECTION_ID=...
APPWRITE_CRAFD_COLLECTION_NAME=...

# Metadata database (shared)
APPWRITE_METADATA_DATABASE_ID=...
APPWRITE_METADATA_DATABASE_NAME=...
```

*(Corrected 2026-08-03: four production-forecasts coordinate **values** were written out
above, two lines below the sentence saying they never are. The value-copy guard scanned
only `.py`; it now scans markdown too.)*

---

## Documentation

| Doc | What it covers |
|-----|----------------|
| [`docs/architecture/role_and_seams.md`](docs/architecture/role_and_seams.md) | **Start here** — role vs the sibling repos + internal seams |
| [`docs/ADRs/`](docs/ADRs/) | Architecture decisions (esp. ADR-011 mapper→lookup; ADR-012 ontology) |
| [`docs/CICs/`](docs/CICs/) | Class intent contracts — one per partner manager; the CRAF'd one is stated as a delta against the UN-FAO one |
| [`CHANGELOG.md`](CHANGELOG.md) | **What changed for a consumer**, per release — behaviour a launcher can observe, failure modes first |
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
