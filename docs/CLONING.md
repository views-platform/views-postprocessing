# Adding a new partner delivery

Read this **before** adding a partner package to this repository, or cutting a partner
API repository that consumes one. It is short on purpose.

> **Corrected 2026-08-03 (#211). This document used to say "before cutting
> `views-crafdapi`", and that framed the job wrongly.** `views-crafdapi` and
> `views-productionapi` are **consumer** APIs, cut from `views-faoapi`. They do not
> clone *this* repository. This repository is the single **producer** that serves every
> partner, and a new partner is added here as a package alongside `unfao/` and
> `crafd/` — not as a new producer repo.
>
> The three-things-to-supply structure below survives that correction unchanged, because
> it was always describing the same three files. What changes is where they go: into a
> new directory in this repo, not into a new repository. The "Hard rules" section below
> is where the distinction actually mattered, and it is corrected there too.

## What you get for free

Two packages, reusable as-is. Neither names a partner, and a test proves it
(`tests/test_clone_readiness.py` imports them in a fresh interpreter and fails if the
partner package arrives with them).

| package | what it gives you |
|---|---|
| **`delivery/`** | The rules that make a delivery valid: coverage, no-collapse, gid parity, observed-range, provenance. Representation-free — primitives in, verdict out. |
| **`contract/`** | How a delivery is built: the whole ADR-013 wire (header, shard, sidecar, run manifest, sink, source selection), the frame seam, the GAUL asset, the historical artifact builder, and the launch-declaration guard. |

## What you must supply

Three things. They are the only partner-specific files in the repository, so the shape
of your work is: **copy these three from an existing partner, change them, keep
everything else.** `crafd/` is the worked example. One caveat if you read it as a
template: it did *not* copy `unfao/managers/README.md`, the operational summary that
sits beside the FAO manager. That was an omission rather than a decision — write one.

Register them as you add them: `tests/conftest.py` holds the repository's single
declared partner list (`PARTNER_PACKAGES`), and a partner missing from it is exempt
from every guard below. A test asserts that list against the filesystem, so forgetting
fails CI rather than passing quietly — which is what happened when `crafd/` landed.

### 1. Your product — `<partner>/product.py`

Four declarations, and nothing may be inferred:

- **`TARGETS`** — the target set a run must carry to be complete. Wire vocabulary only,
  never internal model names.
- **`CONSUMER_DOCUMENT_NAME`** — the store-document `name` your consumer filters on. Get
  this wrong and your documents are invisible to it, silently. (This exact mismatch
  stranded six forecast documents in `unfao_bucket` for months — ADR-013 §4.1a.)
- **`S_MIN`** — the no-collapse floor. How few draws is too few to be a distribution.
- **`UPLOAD_ENABLED`** — the interlock. **Leave it `False`** until your consumer's
  selection guard is deployed in production, not merely merged.

### 2. Your store coordinates — `<partner>/appwrite_env.py`

The env-var names your delivery requires, validated fail-loud before any store is
constructed. Names come from the **Appwrite Seam Contract's coordinate registry** (homed in
views-appwrite) and are referenced **by URL at a pinned commit, never copied**. The
secret stays an operator slot.

### 3. Your manager — `<partner>/managers/<partner>.py`

The pipeline-core seam. **The partner managers are the only modules in the repository
that import `views_pipeline_core`**, and a test holds them to an explicit allowlist.
Yours will orchestrate read → transform → validate → save and *call* the invariants —
never inherit them.

Today the two managers are near-identical. See for yourself rather than trusting a
number here — the number went stale twice while this paragraph was being written:

```
diff views_postprocessing/unfao/managers/unfao.py \
     views_postprocessing/crafd/managers/crafd.py
```

Sixteen lines differ on each side and **none of them changes behaviour**: the import,
the class name, the two partner-named methods and their two call sites, the four
env-var literals, one line that both selects which env tuple is validated and labels
the store, one runtime refusal message, and four lines of prose.

**That is deliberate** — WET before DRY, and the second copy is what finally showed the
seam is a config object rather than a behavioural one. Register **C-33** carries the
extraction trigger: a **third** in-repo partner, or the first bug that has to be
hand-patched identically in both files. If you are the third, read C-33 before copying
a fourth time.

## Hard rules, and why each exists

**Your manager may import `views_pipeline_core.modules.{appwrite,datastore}`.
Nothing else in this repository may — and you add yourself to the allowlist by hand.**
`tests/test_doc_accuracy.py::test_views_pipeline_core_is_confined_to_the_partner_managers` pins the
importer set to an explicit list of manager files. Adding a partner means editing that
list deliberately. That is the cost of a new partner, not a formality: the coupling is
bounded only because someone has to write the file's name down.

Pipeline-core declines to export that surface, and this repository's own import of it is
how a two-repo defect became three (register **C-40**). Unwinding it is deferred under
issue **#146** behind a **named trigger — þ01-D8's supply trigger firing on the C-221
decomposition, explicitly not on this repository's convenience**. Do not read the
deferral as "not done yet"; it is a decision with a condition attached (ADR-014 §4).

**If you are cutting a consumer API repo, the rule inverts: do *not* import them.**
þing-02 **S24(5)** binds the repositories cut from views-faoapi — `views-crafdapi`
(the þing records call it `un-crafdapi`) and `views-productionapi`. It does not reach a
partner package inside this producer, which is why `crafd/managers/crafd.py` may import
what a consumer API may not. An earlier version of this document cited the verdict as a
flat prohibition and over-claimed it. Write a thin client against the SDK, as
views-faoapi did.

**Check the store's result. It is load-bearing, not boilerplate.**
`_ContractStorePort.upload` inspects `result.success` and raises. It looks like
defensive noise and is not. When metadata storage fails after the file is already
uploaded, the pipeline-core store logs the error and **returns
`OperationResult(success=False, code="PARTIAL_SUCCESS")`** — it reports the failure
faithfully and simply does not raise. A caller that discards the result therefore
proceeds as though the delivery were complete, leaving a file with no metadata
document: invisible to the consumer, exactly like a wrong document name. That happened
to run-0's historical artifact on 2026-07-27.

This matters more than it reads, because of a date. þing-02 **D10/S30** required this
repository's legacy path to be guarded or retired **before 2026-11-30**, when the
current key expires — an unguarded path on that day *reports success and ships nothing*.
The legacy path itself was retired in #149 (register C-63), so what the obligation now
amounts to is keeping this guard on the contract path. If you copy a manager you inherit
it; do not tidy it away.

**Get your own key before the first run, not after.**
Free at t=0, a migration later. One key per identity per environment (the Appwrite Seam Contract
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

## Before your first delivery, not after

**Answer your partner's correction questions before you ship to them, not after a bad
delivery.** `docs/operations/correction_procedure.md` is FAO's, and its steps 1–3 and 5
transfer unchanged — they are contract mechanics, not partner specifics. **Step 4 does
not:** who contacts your partner, through what channel, how fast, and whether they
expect a retraction or a supersession are answers only your partner can give.

This repo shipped run-0 to the UN FAO on 2026-07-27 with that step undecided (register
C-22), and it is still undecided. Do not inherit that.

## Where the reasoning lives

`docs/ADRs/013_sampled_forecast_wire_contract.md` — the wire contract ·
`docs/ADRs/012_revised_ontology.md` — what each package is for ·
`docs/ADRs/002_topology_and_dependency_rules.md` — the one-way dependency rule ·
`reports/technical_risk_register.md` — C-69 (why this separation exists), C-40 (the
coupling that remains).
