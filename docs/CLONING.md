# Cloning this repository for a new partner

Read this **before** cutting `views-crafdapi`, `views-productionapi`, or any future
partner delivery. It is short on purpose.

## What you get for free

Two packages, reusable as-is. Neither names a partner, and a test proves it
(`tests/test_clone_readiness.py` imports them in a fresh interpreter and fails if the
partner package arrives with them).

| package | what it gives you |
|---|---|
| **`delivery/`** | The rules that make a delivery valid: coverage, no-collapse, gid parity, observed-range, provenance. Representation-free — primitives in, verdict out. |
| **`contract/`** | How a delivery is built: the whole ADR-013 wire (header, shard, sidecar, run manifest, sink, source selection), the frame seam, the GAUL asset, the historical artifact builder, and the launch-declaration guard. |

## What you must supply

Three things. They are the only FAO-specific files in the repository, so the shape of
your work is: **replace these three, keep everything else.**

### 1. Your product — `unfao/product.py`

Four declarations, and nothing may be inferred:

- **`TARGETS`** — the target set a run must carry to be complete. Wire vocabulary only,
  never internal model names.
- **`CONSUMER_DOCUMENT_NAME`** — the store-document `name` your consumer filters on. Get
  this wrong and your documents are invisible to it, silently. (This exact mismatch
  stranded six forecast documents in `unfao_bucket` for months — ADR-013 §4.1a.)
- **`S_MIN`** — the no-collapse floor. How few draws is too few to be a distribution.
- **`UPLOAD_ENABLED`** — the interlock. **Leave it `False`** until your consumer's
  selection guard is deployed in production, not merely merged.

### 2. Your store coordinates — `unfao/appwrite_env.py`

The env-var names your delivery requires, validated fail-loud before any store is
constructed. Names come from the **PLATFORM-001 coordinate registry** (homed in
views-appwrite) and are referenced **by URL at a pinned commit, never copied**. The
secret stays an operator slot.

### 3. Your manager — `unfao/managers/unfao.py`

The pipeline-core seam. **This is the only module in the repository that imports
`views_pipeline_core`**, and a test keeps it that way. Yours will orchestrate
read → transform → validate → save and *call* the invariants — never inherit them.

## Hard rules, and why each exists

**Do not import `views_pipeline_core.modules.{appwrite,datastore}`.**
þing-02 **S24(5)**, binding. This repository's own import of those is how a two-repo
defect became three (register C-40); pipeline-core declines to offer the surface, and
that refusal is deliberate. Write a thin client against the SDK, as views-faoapi did.

**Get your own key before the first run, not after.**
Free at t=0, a migration later. One key per identity per environment (PLATFORM-001
§5.3). Do not reuse another service's key — this repository ran for months under a key
named for pipeline-core, and nobody could state its scopes from evidence.

**Turn on secret scanning and push protection at creation.**
Also free at t=0. `git clone` copies all history, so a clone made today inherits
whatever is in it — and deletion is not removal while stale branches keep blobs
fetchable.

**Do not pin an installer to `@main` without checking what is on it.**
A launcher installing from an unchecked branch is a delivery you have not read.

**Declare your launch config; never infer it.**
`contract/launch_config.py` refuses a launcher that omits `wire_contract` or declares a
`data_format` other than `feature_frame`. That refusal is the feature — an omitted key
used to select a retired code path silently (register C-63).

## Before you cut

1. Is the partner's consumer guard **deployed**, or only merged? `UPLOAD_ENABLED` stays
   `False` until deployed.
2. Does your key exist, with its scopes written down?
3. Have you read ADR-013 §0 and §11.4? The contract is the same for every partner; only
   the product differs.
4. Run `pytest tests/test_clone_readiness.py` in the clone. If it fails, the boundary
   moved.

## Where the reasoning lives

`docs/ADRs/013_sampled_forecast_wire_contract.md` — the wire contract ·
`docs/ADRs/012_revised_ontology.md` — what each package is for ·
`docs/ADRs/002_topology_and_dependency_rules.md` — the one-way dependency rule ·
`reports/technical_risk_register.md` — C-69 (why this separation exists), C-40 (the
coupling that remains).
