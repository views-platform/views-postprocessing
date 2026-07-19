# ADR-013: The Sampled-Forecast Wire Contract (v1.5)

**Status:** Accepted
**Date:** 2026-07-15
**Deciders:** Project maintainer (PRIO MD&D Team) — explicit sign-off, views-models#149
**Supersedes:** the "platform ADR-046" that platform issues cited as the format authority — no such *format* document ever existed (a pipeline-core ADR-046 exists but covers storage infrastructure only; see Erratum E2 in the Post-adoption record) — and the v1 proposal comment on views-models#149 (2026-07-02).

---

## Context

VIEWS forecasts are moving from one predicted number per map cell per month (a *point
estimate*) to roughly a thousand plausible numbers per cell (*samples*, also called
*draws* — independent possible outcomes drawn from the model's predictive
distribution). Those samples must travel from the model pipeline that produces them
all the way to FAO's API **without ever being collapsed back to a single number**
along the way.

That journey crosses four repositories and two storage transfers, and before this
document no written agreement governed it: the "ADR-046" everyone cited contained no
format decision, the pipeline had no code path that published samples at all, and
three repos were each waiting on another to move first. This ADR is that missing
agreement — the contract of record. It was produced through five reviewed iterations
(v1 → v1.5) with independent reviews from the producer and consumer sides; the full
iteration history is in Appendix A.

## Decision

The contract below (v1.5) is **adopted**. This ADR is the normative document; the
iteration draft `reports/wire_contract_DRAFT.md` is retained as history only.

## Vocabulary

Plain definitions of every term of art used below, in one place:

- **Wire** — any transfer of data between two systems. A *wire format* is the agreed
  shape of the bytes on such a transfer.
- **Hop** — one of the two storage transfers the forecast makes: **Hop A** = pipeline
  → the Appwrite `production_forecasts` store (internal warehouse); **Hop B** =
  views-postprocessing → the Appwrite `unfao_bucket` store (what views-faoapi serves
  FAO from). *Appwrite* is the cloud storage service both live on.
- **PFE** — the *PredictionFrameEnsemble*, pipeline-core's ensemble manager: the
  producer whose output this contract packages.
- **Run / target / month** — one production forecast generation (a *run*) predicts
  each *target* variable (state-based, non-state, one-sided violence deaths) for each
  of 36 future *months*, over ~64,742 PGM cells (*PGM* = PRIO-GRID monthly: one row
  per 0.5°×0.5° land grid cell per month; a cell's id is its `priogrid_id`, a month's
  id is the VIEWS `month_id` integer).
- **N and S** — a payload is a 2-D table of values with `N` rows (one per cell) and
  `S` columns (one per sample). Production aims at S≈1024.
- **Shard** — one piece of a run's data, cut per month, stored as one file. Sharding
  exists because a whole run (~9.5 GB per target at full S) is too big to move as one
  object.
- **Manifest** — a small JSON file listing every shard of a run with a SHA-256
  *content hash* (a fingerprint of the exact bytes) plus what the run is expected to
  contain. It is uploaded **last**, so its presence means "everything before me is
  complete" — we call that the *commit marker*. A run whose upload died halfway (a
  *torn run*) has no manifest and is therefore invisible to consumers.
- **Sidecar** — a separate small file carrying the static geography lookup (country,
  admin regions) per cell, shipped once per run instead of being copied into every
  row of every shard.
- **S_min** — the minimum sample count a consumer will accept before refusing to
  serve (protects FAO from accidentally-collapsed forecasts).
- **Anti-corruption layer** — the one component (views-postprocessing) that speaks
  both end formats so that neither end's format leaks into the other's code.

---

## §0 Status and provenance

**§0.1** The "platform ADR-046" cited across issues as declaring the FAO handoff
format was never written: the citations pointed at a format authority that did not
exist. *(Precision, per Erratum E2, 2026-07-16: a document numbered ADR-046 does
exist in views-pipeline-core — "Appwrite as Secondary Cloud Storage for views-faoapi"
— but it covers storage infrastructure only and contains no format content. The
format authority everyone assumed remained unwritten.)* This contract replaces it.
Before adoption the contract of record was *nothing*; on adoption it is this ADR plus
the ratifying comment on views-models#149.

**§0.2 Adoption mechanics.** Adoption = the maintainer's explicit sign-off on
views-models#149, **enacted by landing this ADR in views-postprocessing in the same
motion** — the ADR is the adoption act, not a follow-up. Implementation in any repo
before that point is out of contract. Sign-off required every cross-repo claim in
this contract to be confirmed by the repo that owns it; all preconditions were met
before adoption (the verification trail is in Appendix A).

**§0.3 Ownership table.** Who owns which leg of the wire:

| Leg | Owner |
|---|---|
| Hop A producer (PFE → prediction store) | views-pipeline-core (#269) |
| Hop A consumer + Hop B producer + **the no-collapse policy boundary (§6)** | **views-postprocessing** |
| Expected-target-set / run-completeness knowledge (§4.2a) | **views-postprocessing configuration** |
| Hop B consumer (`unfao_bucket` → serving) | views-faoapi (#100) |
| `production_forecasts` retention (§3.5) | named at sign-off (infrastructure owner) |

---

## §1 Topology — two hops, one interior representation

```
PFE (per-target y_pred.npy (N,S) float32 + identifiers.npz, local disk)
  ── Hop A: Track A archive (zip), one per (run, target, month);
            per-(run, target) manifest uploaded LAST = commit marker ──►  Appwrite `production_forecasts`
views-postprocessing
  (interior: per-target 2-D PredictionFrame via from_arrays; the anti-corruption layer;
   owns the §6 no-collapse policy boundary; awaits ALL targets per §4.2a)
  ── Hop B: one views_frames.io.arrow file per (target, month) + geo sidecar +
            ONE run manifest spanning all targets (LAST = commit marker) ──►  Appwrite `unfao_bucket`
views-faoapi (serve; MAP/HDI at the edge)
```

In words: the pipeline zips exactly the files it already writes to local disk and
uploads them to the internal store (Hop A). views-postprocessing downloads and
verifies them, holds them internally as views-frames `PredictionFrame` objects (the
platform's native N×S array type), runs the no-collapse gate (§6), and re-emits them
in the views-frames arrow format to the FAO-facing store (Hop B). views-faoapi reads
those and computes point summaries (MAP) and uncertainty intervals (HDI) at serving
time — the *edge* — so samples are never collapsed in transit.

views-postprocessing is the anti-corruption layer: neither end format leaks past it.
Hop A deliberately wraps what PFE already writes — zero new serialization code in
pipeline-core, compatible with their #207 on-disk-format deferral and orthogonal to
their #139 Track-B retirement. Hop B is the format views-postprocessing#91 and
views-faoapi#100 had already ratified.

---

## §2 Shared contract header (both hops)

Every payload carries the same self-describing label — the *header* — as
`metadata.json` inside the Hop-A archive, and inside the arrow file's `views_frames`
schema metadata (readable on load as `state["metadata"]`).

```json
{
  "contract_version": "1.5",
  "frame_type": "prediction",
  "representation": "samples",
  "sample_count": 1024,
  "dtype": "float32",
  "spatial_level": "pgm",
  "target": "lr_ged_sb",
  "time_id": 543,
  "run_id": "...",
  "generated_at": "...",
  "id_semantics": { "time": "views_month_id", "unit": "priogrid_id" },
  "provenance": {
    "ensemble": "<ensemble name>",
    "pipeline_core_version": "<self-reported; see caveat>",
    "reconciled": true
  },
  "sharding": { "scheme": "per_month", "index": 7, "count": 36 }
}
```

**§2.1 Clauses.** Readers MUST ignore header keys they do not know (the header is
open to additions; the keys defined here have fixed meaning). `contract_version`
works like software versions: a **MINOR** bump (1.1 → 1.2) is clarifying or additive
— an older reader still accepts the artifact; a **MAJOR** bump (1.x → 2.0) is
breaking and consumers MUST reject it. `sample_count` and `dtype` are **parameters,
not schema**: a run with few samples is still contract-conformant by construction —
consumers reject it only when `sample_count < S_min` (§6), never by renegotiating the
contract.

**§2.2 Identity and provenance.** `id_semantics` states explicitly what the
identifier arrays mean (`time` is the VIEWS month-id; `unit` is the `priogrid_id`) —
this platform has already paid once for leaving id vocabulary implicit (the gid/id
epic). `provenance` is exactly the three keys shown (strings/bool). **Caveat:**
`pipeline_core_version` is self-reported and will be unreliable until pipeline-core's
release train (their #261) cuts real releases — consumers must not treat it as
authoritative before then.

**§2.3 Governance hook.** Changing `sample_count` (wire thinning) or `dtype` on the
**FAO delivery** changes the published HDI/MAP numbers, and is therefore a
**re-baseline event**: it requires sign-off under views-faoapi **ADR-023
("Governance Gate for Re-baselining Published Forecasts", Accepted 2026-06-24)**
before production use. The wire stays flexible; the product stays governed.

---

## §3 Hop A: the Track A archive (views-pipeline-core, #269)

**§3.1 Shard.** One stored object per **(run, target, month)**: a zip containing
exactly what PFE already writes — `y_pred.npy` of shape `(N, S)` float32, plus
`identifiers.npz` (the time and unit arrays, row-aligned with `y_pred`) — plus
`metadata.json` (the §2 header). Its store document carries
`type="sampled_forecast_shard"`, `category="forecast"`, `loa`,
`targets=[<target>]`, and `name` per §3.3. Size ≈ 265 MB per shard per target at
S=1024 over 64,742 cells.

**§3.2 Manifest — one per (run, target).** A JSON document,
`type="sampled_forecast_manifest"`, listing the target's shards (store file-ids +
content hashes), the expected month set, and the expected cell count. It is
**uploaded last and is the commit marker for that target's leg**: consumers MUST
ignore shards no manifest lists, so a producer that dies mid-run leaves nothing
visible. *(Erratum E1, 2026-07-15: the sidecar hash is NOT a Hop-A manifest field —
the sidecar is produced downstream by views-postprocessing, so the producer has
nothing to hash; `sidecar_sha256` at Hop A is absent/null. The sidecar hash lives in
the Hop-B run manifest only, per §5.2.)* Hop A deliberately keeps **per-target**
manifests (unlike Hop B's one-per-run, §4.2): the producer's targets complete
independently, and the Hop-A consumer — views-postprocessing, unlike faoapi — can
trivially wait for all targets before acting (§4.2a). **Hash verification:**
views-postprocessing verifies each shard's content hash against this manifest on
read; it owns the integrity invariants.

**§3.3 Naming.** Shard name: `{run_id}__{target}__m{time_id:06d}.tap.zip`; manifest
name: `{run_id}__{target}__manifest.json`. Both templates live as **shared constants
with golden-string tests** (tests that assert the literal string, so a rename cannot
slip through) in the producing repo. **A name is a locator only — identity is the
manifest content plus the embedded header.** Consumers MUST NOT parse identity out
of filenames (the lesson of C-59/C-94).

**§3.4 Emission assertion (producer-side mechanism guard).** Before uploading, the
publish leg asserts that what it staged matches the frame it was handed — checked
**against the staged files, before zipping**: staged `y_pred` has
`S == frame.sample_count`, `dtype == float32`, `N == frame.n_rows`; staged
identifier arrays equal the frame's. The zip step itself is covered by a CI
round-trip test (archive → unzip → reload reconstructs the identical frame;
pipeline-core#269 acceptance), so the runtime assert stays cheap and runs on every
publish. Feasibility was verified at the attach point in pipeline-core's code
(Appendix B). This is a *mechanism* guard — each hop vouches for its own emission;
the FAO *policy* lives only at §6.

**§3.5 Retention.** A full-S run ≈ 28.6 GB (3 targets × 36 months × ~265 MB) lands
in `production_forecasts` and accumulates with every run. Verified: no
retention/TTL/quota mechanism exists anywhere in the store code today. **A retention
owner and policy (quota, TTL, or cleanup cadence) must be named at sign-off, before
the first full-S production run.**

---

## §4 Hop B: arrow delivery (views-postprocessing → `unfao_bucket` → views-faoapi)

**§4.1 Shard.** One `views_frames.io.arrow` file per **(target, month)**, with the
§2 header embedded. The **historical actuals+geography artifact is explicitly
unchanged** (pandas parquet, as today).

**§4.1a Store-document schema (pinned).** faoapi's metadata schema makes all five
fields **required at upload**, and its production query layer **unconditionally adds
a `name` filter** to every search (its model path always carries a model name) — so
a document uploaded under the wrong `name` is *invisible to the consumer*, not
merely degraded. Therefore every Hop-B contract document uploads with:

| Field | Value (Hop-B documents) |
|---|---|
| `category` | `"forecast"` |
| `type` | `"sampled_forecast_shard"` \| `"sampled_forecast_manifest"` \| `"sampled_forecast_sidecar"` |
| `name` | **the literal faoapi model name — `un_fao` today.** Config-owned by views-faoapi; changing it is a contract amendment, not a deploy detail. |
| `loa` | `"pgm"` |
| `targets` | shard: `[<target>]`; manifest/sidecar: the run's full target list |

Upload metadata must also remain compatible with faoapi's C-71 quarantine/approval
filtering (approval fields present).

**Explicit producer obligation.** views-postprocessing currently uploads its
forecast document under the *ensemble's* name (e.g. `rusty_bucket`), not the pinned
consumer name; only the historical artifact already complies. Under this schema,
**all Hop-B contract documents upload under the pinned consumer name** — an explicit
views-postprocessing change, owned by its **#91 sink-adapter leg**. (Code locations:
Appendix B.)

**Recorded inconsistency in the CURRENT (pre-contract) wire.** faoapi's `name`
filter exists on its deployed production branch too — so today's ensemble-named
forecast documents are **invisible** to faoapi already. This could not be resolved
from code alone (it may mean no forecast was ever served end-to-end via this path)
and MUST be ground-truthed against live Appwrite at run 0 (§11.2). *(Post-adoption:
confirmed live — see the Post-adoption record, 2026-07-15.)*

**§4.2 Run manifest — ONE per run, spanning all targets.** views-postprocessing
emits **a single manifest per run** to `unfao_bucket`: the full Hop-B shard list
across all (target, month) with content hashes, the expected month set, expected
cell count, the run's target list, and the sidecar hash.
`type="sampled_forecast_manifest"`, **uploaded last — after every target's shards —
as the run's single commit marker.** This closes the torn-run hole across the
*target* axis: with per-target manifests, a consumer refreshing between targets
could assemble a run with one target present and the others missing; with one run
manifest that state is structurally invisible.

**§4.2a Run completeness.** The **expected target set is views-postprocessing
configuration** (as the anti-corruption layer it owns the FAO product definition).
views-postprocessing translates a run only when **all configured targets' Hop-A
manifests** are present, and emits the §4.2 run manifest only after all targets'
Hop-B shards are uploaded. The run manifest carries the resolved target list, so
faoapi needs no target-set knowledge of its own.

**§4.3 Selection semantics.** The consumer serves only the **latest manifested
run**: resolve the newest manifest via
`get_latest_file_id(filters={"category": "forecast", "type": "sampled_forecast_manifest"})`
(plus faoapi's auto-injected `name` filter — verified to fit its existing machinery
unchanged), download it, then fetch exactly the shards it lists. Because §4.2 gives
each run exactly **one** commit marker, "newest manifest" is well-defined.

**§4.4 Cache identity and the operational control point.** The run manifest's
`file_id` is the run's cache key (it fits faoapi's existing single-file-id cache
validation). A new manifest ⇒ a new run ⇒ cache invalidation; no per-shard cache
bookkeeping. **The manifest is also the run's operational control point:**
quarantining the manifest's file-id (the C-71 blocklist) — or deleting the manifest
— atomically rolls the consumer back to the previous manifested run, without
touching the 100+ shard objects. Operators act on manifests, never on shards. (A
runbook line to land with faoapi#100.)

**§4.5 Ingest asserts (consumer-side mechanism guards, defense-in-depth).** At
ingest the consumer asserts:

- **(a)** loaded S equals the manifest/header `sample_count`;
- **(b) ordering** — the arrow file's `sample` column equals
  `np.tile(np.arange(S, dtype=np.int32), N)` *before* that column is discarded.
  Rationale: the arrow writer emits that exact column, but the loader never reads it
  — it reconstructs the (N, S) array purely by position — so a reordered or
  truncated table would yield plausible floats in the wrong sample slots, invisible
  downstream (code locations: Appendix B);
- **(c) hashes** — faoapi SHOULD verify shard content hashes against the run
  manifest at ingest (cheap; once per cache fill).

These are mechanism guards; the §6 policy is not duplicated here.

**§4.6 Capacity and the intended consumer model.** At the reference parameters a
fully assembled run is ≈ 28.6 GB in memory — larger than the serving host. **Before
a production S is chosen, the capacity inequality
`assembled-run size × safety factor ≤ consumer serving RAM` must be owned** —
either by choosing wire parameters that satisfy it, or (the intended direction) by
**lazy per-month consumption**: the per-(target, month) sharding exists precisely so
the consumer can load shards on demand with a month-keyed cache, which dissolves the
memory wall without memory-mapping. Documented caveat: `arrow.load` reads a whole
file into RAM (no mmap today; ~1.6 GB transient per full-S shard); per-month
sharding is the mitigation, and mmap/partitioned arrow remains future views-frames
work, not a contract dependency.

---

## §5 GAUL geography sidecar

(*GAUL* is FAO's Global Administrative Unit Layers — the standard country/admin
region coding the delivery labels cells with.)

**§5.1 Schema.** One sidecar per run (~64,742 rows), `type="sampled_forecast_sidecar"`
(store-document fields per §4.1a), keyed by `priogrid_id`, with **exactly these 9
columns**: `pg_xcoord` (float64), `pg_ycoord` (float64), `country_iso_a3` (string),
`admin1_gaul1_code`, `admin1_gaul1_name`, `admin1_gaul0_code`, `admin1_gaul0_name`,
`admin2_gaul2_code`, `admin2_gaul2_name` — the `*_name` and `country_iso_a3` columns
as **plain strings** (not categorical; verified the consumer applies no categorical
coercion), the `*_code` columns numeric (int64 when complete; float64 where NaN is
present). **Rows with missing GAUL codes are PRESERVED with NaN, never pre-dropped**
— the consumer drops them at aggregation under its own legacy-parity rule (its C-146
machinery, verified). Pre-dropping here would silently mislabel geography.

**§5.2 Consistency.** The sidecar's cell-id set must equal the forecast's cell-id
set (enforced by views-postprocessing's existing coverage/identity invariants,
extended to the sidecar). The sidecar hash is pinned in **the Hop-B run manifest
(§4.2)** *(Erratum E1: formerly "both manifests" — impossible at Hop A, where the
sidecar does not yet exist)*. Delivered once per run, not per shard — the whole
point is not replicating static strings ×S×36.

---

## §6 The no-collapse boundary — owner: **views-postprocessing** `delivery/draws.py`

The single place where the platform *decides* a forecast still carries genuine
uncertainty. A representation-free invariant module,
`views_postprocessing/delivery/draws.py` (sibling of the existing
coverage/identity/observed-range/provenance invariants), raises
`DrawsCollapseError` unless all of:

1. values are 2-D `(N, S)`;
2. payload S equals the header's `sample_count`;
3. `sample_count >= S_min` (config: 2 for the walking skeleton; region-pinned for
   production);
4. **globally**, at least one row has more than one distinct sample value.
   *Explicit non-rule: a single row with zero variance is legal — zero-conflict
   cells dominate PGM, so many rows are legitimately all-zeros; the degeneracy check
   is global-across-rows, never per-row.*

It runs before every FAO-facing forecast upload. This is the single **policy** gate;
the §3.4 and §4.5 asserts are per-hop **mechanism** guards that localize faults
without duplicating the policy (bulkheads plus one gate). **Note:** rule 2
deliberately re-validates what §4.5(a) already checked at ingest — the policy gate
vouches for its own input. This redundancy is intentional and MUST NOT be removed as
a "simplification."

---

## §7 Prerequisites

- **(a) Target naming — DECIDED (maintainer, 2026-07-02):** the canonical wire
  vocabulary is `lr_ged_sb` / `lr_ged_ns` / `lr_ged_os`; producers rename their
  internal names at publish (no `_best` suffixes on a samples wire). The
  internal→wire mapping lives in **one shared constant** in the producing repo,
  cited by the golden fixture.
- **(b)** The `APPWRITE_PROD_FORECASTS_COLLECTION_ID` config fix (views-models#230-A)
  — the documented `forecasts_metadata` collection does not exist in live Appwrite.
- **(c) ADR numbering:** views-faoapi's consumer-side ADR is **ADR-031** (verified:
  000–030 taken). faoapi#100 to be retitled off "ADR-046".

---

## §8 Non-goals (with recorded deferred intents)

- **cm level and the second store** (views-postprocessing#97): inherited later via
  the header's `spatial_level`; reconciliation already runs upstream in PFE,
  samples-aware.
- **Historical artifact format**: unchanged pandas parquet.
- **mmap / partitioned arrow**: future views-frames work (a hardening issue for
  `io.arrow` — ordering validation on load, plus mmap — should be filed at
  execution); not a contract dependency.
- **Concrete S_wire / dtype values**: parameters (§2.1) with a governance gate
  (§2.3).
- **Deferred intent (recorded, not adopted):** consolidate the §2 header vocabulary
  into `views_frames.FrameMetadata` via a MINOR extension once the fixture-pinned
  header has stabilized; extract a shared sharded-run reader into views-frames only
  after both hand-rolled consumers exist (WET-before-DRY).

---

## §9 Corrections to prior claims

views-models#143 claimed the samples work needed "no new aggregation mode **or
pipeline-core change**". That claim is **falsified for the publish leg**: at the
time of writing, no code path existed by which any sampled forecast reached the
prediction store — the pipeline's store-upload switch was accepted and logged but
never acted on, the Arrow upload path raised `NotImplementedError`, and the parquet
fallback was disabled for these models. pipeline-core#269 is the fix. The specific
code locations proving each part of this, at verified commits, are in Appendix B.

---

## §10 Golden fixture (the executable spec)

One canonical **small-S fixture** — a real Track-A shard archive, its Hop-B arrow
shard, the geography sidecar, and both manifests, generated at S=4 with synthetic
values — is committed alongside this ADR and **versioned with `contract_version`**.
All three implementing repos' test suites consume the *same bytes*: the producer
proves it emits them, the anti-corruption layer proves it translates them, the
consumer proves it ingests them. The fixture **pins the header JSON byte-for-byte**
— that is what makes two independently hand-written header writers safe without a
shared constructor. **A change to the fixture is a change to the contract.**

**§10.1 Distribution.** The fixture bytes live in **this repo** (beside the ADR).
The other two repos **vendor a copy** (commit their own copy of the files) and carry
a **pinned content-hash equality test**: the hash, recorded next to the fixture, is
the cross-repo contract; a mismatch fails loud with "re-vendor the fixture from
views-postprocessing@\<ref\>". No CI network dependency; no silent drift.

**§10.2 Injectable provenance.** Byte-for-byte parity requires producers to accept
**injected `run_id` and `generated_at`** in test mode (a keyword argument or
clock/id seam — not global state), so fixture regeneration is deterministic.
pipeline-core#269 plans its header writer accordingly.

---

## §11 Sequencing & verification vehicle

**§11.1 Small-S first.** Because `sample_count` is header data rather than schema, a
low-S placeholder ensemble is contract-conformant — the *walking skeleton*
(views-models#230; the smallest end-to-end version of the whole path) runs **at S=8
with synthetic constituents** as the contract's verification vehicle. It proves the
plumbing; only the *scale* proof waits on views-models#143/#146 tuning.

**§11.2 Run-0 checklist.** The first skeleton run carries three manual duties:

- **(a)** The Hop-B run manifest is adopted in text but its implementation may lag;
  for run 0 only, verify manually that the shard set is complete and consistent.
- **(b) Live-Appwrite ground-truth:** before run 0, enumerate what actually exists
  in `unfao_bucket` — document names, `type` values, categories — and record what
  the deployed faoapi resolves today (possibly nothing, per §4.1a's recorded
  inconsistency). This is the empirical baseline the §11.4 transition rule is judged
  against. *(Post-adoption: substantially pre-executed — see the Post-adoption
  record, 2026-07-15.)*
- **(c)** After run 0: confirm the new artifacts resolve as intended for the new
  consumer path and remain invisible (or harmlessly visible) to any still-deployed
  legacy selector, per §11.4.

**§11.3 Parallelism.** The only serial prerequisite (target naming) is decided
(§7a). views-postprocessing's legs (`draws.py`, source adapter, sink adapter,
sidecar, manifests), pipeline-core's publish leg (#269), and faoapi's ingest work
(#100, re-scoped as an epic: skeleton-ingest → assembly + sidecar join → cache
re-key → transition guard → dual-format window, with the §4.5 asserts) can all
proceed in parallel.

**§11.4 Transition rule — BOTH hops.** A contract artifact is identified by its
embedded header — never by filename. Once a manifested run exists in a store, legacy
artifacts there are ignored. **Sequencing constraint:** at **each** store, the
type-aware consumer — or at minimum a one-line `type` guard in the deployed legacy
reader — must be **live before the first contract artifact is uploaded there**.
Why, per hop:

- **Hop B:** deployed faoapi selects the newest `category="forecast"` document with
  no `type` awareness — and since it name-filters on the pinned consumer name, the
  contract wave's `name="un_fao"` documents become **visible to the legacy
  selector** precisely where the old ensemble-named forecasts were not. Without the
  guard, the first Hop-B upload would be grabbed as "the forecast" by deployed code.
  The constraint is *more* acute under the contract, not less.
- **Hop A:** the legacy views-postprocessing reader has the same selection shape
  (newest `category="forecast"`, no `type` filter). Its existing identity assertion
  makes the failure **loud, not silent** — an outage, not corruption — but the
  constraint stands: the type-aware source adapter, or a one-line `type` filter in
  the legacy reader, lands **before pipeline-core#269's first live upload.**

**Minimal-guard note (verified, both hops):** every legacy document in both stores
carries the legacy `type` vocabulary — Hop-B legacy uploads stamp `type="model"`;
Hop-A legacy uploads stamp `type` ∈ {`"model"`, `"ensemble"`} — **fully disjoint
from the contract's `sampled_forecast_*` values**. So the minimal legacy guard is
literally one line at each deployed selector: pin the legacy type(s) into its
filters. It needs zero knowledge of the new types and can ship immediately,
independent of the full consumer legs. (Code locations: Appendix B.)

Skeleton ordering therefore is: **consumer guards → producer legs → run 0.**

---

## Post-adoption record

Dated events after adoption. Errata correct errors in this document; other entries
record execution progress against it.

- **2026-07-15 — §4.1a's recorded inconsistency CONFIRMED live.** During the Hop-B
  legacy-guard work (faoapi PR #200), a read-only audit of the live `unfao_bucket`
  found **six `orange_ensemble`-named forecast documents** stranded by the `name`
  filter — the inconsistency has been firing all along and is the actual reason
  forecast serving is empty. Recorded as an addendum to the F1 ratification (faoapi
  repo). Consequence: §11.2(b) is substantially pre-executed; the remaining run-0
  check is §11.2(c).
- **2026-07-15 — both §11.4 legacy guards merged on `development`:** Hop A
  (views-postprocessing PR #99, `type="ensemble"` pin) and Hop B (faoapi PR #200,
  `type="model"` pin, live-ground-truthed). **Standing constraint (faoapi C-161):**
  the Hop-B guard must reach *production* before views-postprocessing's first
  contract upload to `unfao_bucket`.
- **2026-07-15 — Erratum E1 (MINOR clarification, §2.1; contract_version stays
  1.5):** §3.2/§5.2 originally required the Hop-A manifest to pin the sidecar hash —
  impossible, since the sidecar is produced downstream by views-postprocessing.
  Corrected in place (dated markers in §3.2/§5.2): the sidecar hash is a
  Hop-B-run-manifest field only; `sidecar_sha256` at Hop A is absent/null. Caught by
  the pipeline-core seat implementing #269 (their PR #276 ships it as null — already
  conformant).
- **2026-07-15 — Hop-A publish leg SHIPPED:** pipeline-core #269 closed via their PR
  #276 (`66328be`, 12 tests): Track A archives + manifest-last + torn-run abort +
  §3.4 emission assert + §3.3 golden-string names + §7a wire mapping (fail-loud on
  unmapped targets) + §10.2 injectable provenance. The wire now exists end-to-end in
  code from PFE to the store.
- **2026-07-15 — §10 golden fixture PUBLISHED (canonical source):**
  `tests/fixtures/wire_contract/` in this repo — 1 run × 1 target × 1 month × 6
  cells × S=4; Track-A shard + Hop-A manifest (E1: null sidecar hash) + arrow shard
  + sidecar (NaN row pinned) + Hop-B run manifest. Root hash (SHA-256 of
  `SHA256SUMS`):
  `b1f3878df9ef74b25dce53a070e1711db39dfdf1c6ca3e1f5a716875ceb32f44`. Deterministic
  generator: `scripts/build_wire_fixture.py` (pyarrow 23.0.1 / views_frames 1.0.0
  pinned in the fixture README). Consumers vendor + pinned-hash test per §10.1.
- **2026-07-16 — C-161 resolution route DECIDED (maintainer): proper deploy only, no
  hotfix.** The Hop-B guard reaches production exclusively via faoapi's deployment
  epic (#184: service account + tag-based deploy gate), bringing production up to
  date with development as one planned, verified release. Cherry-picks / manual
  placement rejected on principle. No clock pressure: nothing may upload to
  `unfao_bucket` before the guard is live (§11.4), and the upload leg
  (views-postprocessing #91) is not yet built — the constraint orders the finish, it
  does not stall the work. Run 0 follows the proper deploy.
- **2026-07-16 — Erratum E2 (provenance correction; no contract-content change):**
  the claim that "ADR-046 does not exist — never a document" was **false as
  literally written**. A maintainer re-check found
  `views-pipeline-core/documentation/ADRs/046_appwrite_storage_integration.md`
  ("Appwrite as Secondary Cloud Storage for views-faoapi", 2026-04-08, on
  `development`): infrastructure/failure-semantics only — env-var validation,
  graceful-degradation uploads, SHA-256 dedup, auto-bucket creation — **zero format
  content**. The faoapi roadmap's "amend ADR-046" therefore pointed at a real
  document it proposed to extend, not at nothing; the investigation flattened
  "exists but contains no format decision" into "never existed", and the reviews
  repeated it. (A third, unrelated ADR-046 — views-hydranet "Symmetric Feature
  Lifecycle" — overloads the number further.) **The substantive conclusion is
  unchanged:** no wire-format authority existed anywhere; this ADR is it, and a
  dedicated contract remains the right home over amending a storage-plumbing ADR.
  §0.1 and the Supersedes line carry the corrected wording.
- **2026-07-19 — human-readability rewrite (maintainer instruction; ZERO normative
  change).** This document rewritten in plain prose as the primary text; §
  numbering unchanged; version changelogs and file:line verification evidence moved
  to Appendices A/B. Every MUST, pinned value, and obligation preserved in meaning;
  the normative-drift checklist was reviewed at commit.

---

## Appendix A — Version history (review archaeology; non-normative)

The contract was drafted and reviewed as `reports/wire_contract_DRAFT.md` in this
repo, one commit per iteration (v1.1 → v1.5), with independent reviews from the
producer seat (views-pipeline-core) and consumer seat (views-faoapi) and a
cross-seat reconciliation. The full review artifacts live in those repos'
`reports/` trees; the tables below are the per-version change summaries, verbatim
from the adopted v1.5 text.

### v1.4 → v1.5 (F1 owner-ratification — status only, no contract-content change)

| # | Change | Source finding |
|---|--------|----------------|
| 1 | **§0.2 precondition CLEARED: F1 ratified by the owning seat.** views-faoapi verified both claims on `origin/main` (`fab4694`): the `name` injection (`prediction.py:167-168`; forecast fetch `api.py:488-489`; always-resolving `APIPathManager("un_fao")`, `model.py:250`) and the latent invisibility of `rusty_bucket`-named forecasts. The "never served end-to-end" inference is **corroborated, not proven** (their 2026-06-29 operational record: 11 bucket files, all historical; forecast endpoints empty) — the definitive by-name bucket listing remains a §11.2(b) run-0 duty. Ratification report: `views-faoapi/reports/expert_reviews/2026-07-14_wire_contract_F1_ratification.md`. Bonus: the Hop-B half of v1.4's type-disjointness row independently corroborated (`type="model"` on legacy uploads). | faoapi seat ratification (2026-07-14) |
| 2 | **Citation-integrity duty recorded (§0.2):** several seat artifacts this contract cites by path are uncommitted or unpushed in their home repos (faoapi's v1 review / v1.1 response / v1.3 confirmation + the F1 ratification; the producer seat's v1.3 review has **no artifact at all**). All cited artifacts must be committed and pushed in their home repos **before adoption** — this contract exists because of a dangling citation (ADR-046) and must not adopt with dangling citations of its own. | author + faoapi seat housekeeping note (2026-07-14) |

### v1.3 → v1.4 (producer seat's v1.3 review)

| # | Change | Source finding |
|---|--------|----------------|
| 1 | **Run-0 ground-truthing promoted to the checklist (§11.2)** — the live-Appwrite audit (which documents exist in `unfao_bucket`, under which names/types, what deployed faoapi actually resolves) was buried in §4.1a prose; it is now an explicit run-0 item so it cannot be skipped. | producer v1.3 review, delta 1 |
| 2 | **Minimal legacy guard made concrete — legacy/contract `type` vocabularies verified DISJOINT on both hops (§11.4)** — Hop-B legacy uploads stamp `type="model"` (`unfao.py:303/:314`); Hop-A legacy uploads stamp `type=<model_path.target>` ∈ {`"model"`, `"ensemble"`} (pipeline-core `managers/prediction/io.py:138`; `DatastoreModule` default `"model"`). The one-line legacy guard is therefore: pin the legacy type(s) in each deployed selector's filters — zero knowledge of the new types required. | producer v1.3 review, delta 2 (Hop-B verified at review; Hop-A verified at v1.4 drafting) |
| 3 | **F1 ratification is an explicit sign-off precondition (§0.2)** — F1 makes claims about faoapi's deployed `main`; symmetric with R1's treatment, the owning seat (views-faoapi) ratifies them before sign-off, so every cross-repo claim in the contract is confirmed by the seat that owns it. (The producer seat has already verified both F1 claims independently — ratification is the owning seat's confirmation, not a re-litigation.) | producer v1.3 review, delta 4 |
| 4 | **Housekeeping** — drifting version-stamped labels neutralized (§4.1 "unchanged in v1.2" → unchanged; §8 heading de-versioned; footer no longer names the next version number); `contract_version` example → `"1.4"`. Birth-stamps ("new in v1.2/v1.3") are kept — they are accurate forever and preserve traceability. | producer v1.3 review, delta 3 |

### v1.2 → v1.3 (author's post-reconciliation verification — finding F1)

| # | Change | Source finding |
|---|--------|----------------|
| 1 | **§4.1a gains the explicit producer obligation the name-pinning implied but never stated:** views-postprocessing **currently uploads the forecast document as `name=<ensemble name>`** (`unfao.py:314` — `rusty_bucket` today; only the historical complies, `:303`). Under the pinned schema, **all** Hop-B contract documents upload as the pinned consumer name — an explicit views-postprocessing change, owned by the #91 sink-adapter leg. | **F1** — author's verification of v1.2 against this repo's code (2026-07-13) |
| 2 | **§4.1a also records the discovered latent inconsistency in the CURRENT wire:** faoapi's `name` injection exists on **deployed `main` too** (`origin/main prediction.py:167-168`; the forecast fetch composes `{"category": ...}` then the search injects `name` — verified), so `rusty_bucket`-named forecast documents are latently **invisible** to faoapi *today*. Cannot be resolved from code alone (it may mean no forecast has ever been served via this path); **ground-truth against live Appwrite at run 0**. | F1 (verified on faoapi `origin/main` + `development`; independently re-verified by the producer seat, 2026-07-14) |
| 3 | **§11.4 Hop-B rationale strengthened:** pinning `name="un_fao"` makes contract artifacts *visible* to the deployed legacy selector where legacy `rusty_bucket`-named forecasts were not — the D3 sequencing constraint (consumer guard before first upload) is therefore **more** acute under the contract, not less. | F1 |

### v1.1 → v1.2 (every change traceable to a named review finding)

| # | Change | Source finding |
|---|--------|----------------|
| 1 | **Manifest cardinality split (§3.2, §4.2, §4.2a, §4.3)** — Hop A keeps **one manifest per (run, target)**; Hop B gets **one manifest per run, spanning all (target, month) shards**. Closes the torn-run hole *across the target axis* ("newest manifested run" was ill-defined with three commit markers per run). The **expected-target-set knowledge is owned by views-postprocessing configuration** (§4.2a) — it awaits all Hop-A manifests for a run before translating. | producer Δ1 ≡ consumer D1 — **independent convergence** (reconciliation §2.1); unanimous priority #1 |
| 2 | **Hop-B store-document schema pinned, incl. the literal `name` (§4.1a)** — faoapi's metadata query **unconditionally injects a `name` filter** in production, so documents with the wrong `name` are *invisible*, not degraded. All five required upload fields tabled; `sampled_forecast_sidecar` added to the `type` enum. | consumer D2 + consumer §3.1 (verified: name injection unconditional) |
| 3 | **Transition sequencing at BOTH hops (§11.4)** — the type-aware consumer leg (or a minimal type-guard in the legacy reader) must be deployed **before the first contract artifact is uploaded at each store**. Verified at Hop A during reconciliation: the legacy views-postprocessing reader selects newest-`category="forecast"` with no `type` filter (`unfao.py:110`); its identity assertion (`unfao.py:123`) makes the failure loud, not silent — but it is still an outage if sequencing is wrong. Skeleton ordering becomes: consumer guards → producer legs → run 0. | consumer D3 + reconciliation **R1** (verified 2026-07-13) |
| 4 | **Golden-fixture distribution mechanism + injectable provenance (§10.1, §10.2)** — the fixture lives in this repo (beside the ADR); the other two repos **vendor a copy plus a pinned content-hash equality test** (the hash, not the bytes, is the cross-repo contract; mismatch fails loud with "re-vendor"). Producers MUST accept injected `run_id`/`generated_at` in test mode for byte-parity. | producer Δ2 |
| 5 | **Hash verification assigned (§3.2, §4.5c)** — views-postprocessing verifies Hop-A shard hashes on read (it owns the integrity invariants); faoapi SHOULD verify Hop-B hashes at ingest, once per cache fill. | consumer D4 |
| 6 | **Manifest = the run's operational control point (§4.4)** — quarantining (C-71 blocklist) or deleting the single run manifest atomically rolls the consumer back to the previous manifested run; operators act on manifests, never on shards. | producer Δ3-2 ≡ consumer §3.2 — independent convergence (reconciliation §2.2) |
| 7 | **Emission-assert mechanics pinned (§3.4)** — the runtime assert inspects the **staged files pre-zip**; the zip step itself is covered by the CI round-trip identity test (pipeline-core#269 acceptance). | producer Δ3-1 |
| 8 | **Intentional redundancy marked (§6)** — the policy gate re-validates payload S == header `sample_count` even though §4.5(a) checks it at ingest; deliberate (the policy gate vouches for its own input) and MUST NOT be "simplified" away. | producer Δ3-3 |
| 9 | Housekeeping: `contract_version` example bumped; §2.1 gains version semantics (MINOR = clarifying/additive, MAJOR = breaking); file renamed version-neutral (`wire_contract_DRAFT.md`) so the commit-per-iteration convention survives. | both seats' convention notes |

### Draft-era closing note (historical)

The v1.5 draft closed with: *"Both seats are on record sign-off-ready; v1.4 folds
the producer seat's v1.3 review (F1 independently verified). Outstanding before the
§0.2 adoption act: the faoapi seat's F1 ratification."* That ratification landed
2026-07-14 and adoption followed 2026-07-15.

---

## Appendix B — Verification evidence (file:line, at verified HEADs; non-normative)

The code locations backing the claims marked "verified" in the main text. Line
numbers were checked at the commits current when each finding was made; they
describe evidence, not obligations.

**§2 header mechanism (arrow metadata dict):** `views_frames/io/arrow.py:69` —
the open `metadata` dict written into the arrow schema metadata; readable via
`load(...)` → `state["metadata"]`.

**§3.4 emission-assert attach point (pipeline-core):**
`prediction_frame_ensemble.py:593` (current HEAD at verification) — feasible with
zero new imports; `agg_pf.sample_count`/`.values`/`.n_rows`/`.identifiers` all
public; float32 already construction-enforced.

**§4.1a / F1 (faoapi name filter, both branches):** `prediction.py:167-168`
(`origin/main`); forecast fetch `api.py:488-489`; always-resolving
`APIPathManager("un_fao")` at `model.py:250`. views-postprocessing's current upload
names: forecast `name=<ensemble name>` at `unfao.py:314` (only the historical
artifact complies, `unfao.py:303`).

**§4.5(b) ordering rationale (views-frames):** `arrow.save` writes the `sample`
column as exactly `np.tile(np.arange(S, dtype=np.int32), N)` at `io/arrow.py:47`;
`arrow.load` never reads it and reconstructs `(N, S)` positionally at
`io/arrow.py:79-98`.

**§9 falsification of views-models#143 (pipeline-core, verified HEAD):**
`use_prediction_store` accepted (`prediction_frame_ensemble.py:143`), stored
(`:154`), only ever logged (`:812`); no `DatastoreModule` constructed, no upload
occurs; forecast output local-only (`save_pf`, `:593`);
`PredictionIOManager._upload_to_prediction_store` raises `NotImplementedError` for
Arrow tables (`managers/prediction/io.py:111+`); Track B parquet disabled for PF
models. pipeline-core#269's inline line refs (written 2026-07-02) were stale and
were corrected to the above when amended.

**§11.4 legacy selection shapes and type vocabulary:** views-postprocessing legacy
reader: `unfao.py:110` (`get_latest_file_id(filters={"category": "forecast"})`),
identity assertion `unfao.py:123` (loud, not silent). Legacy upload types: Hop B
`type="model"` (`unfao.py:303/:314`); Hop A `type=<model_path.target>` ∈
{`"model"`, `"ensemble"`} (pipeline-core `managers/prediction/io.py:138`;
`DatastoreModule` default `"model"`).
