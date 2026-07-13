# Sampled-Forecast Wire Contract — v1.3 DRAFT

| | |
|---|---|
| **Status** | **DRAFT v1.3 — for maintainer sign-off. NOT posted, NOT adopted.** Both seat reviews are on record as sign-off-ready at v1.1; v1.2 folded their deltas; v1.3 folds the author's post-reconciliation verification finding (F1). Iterations are commits to this file so review deltas stay git-diffable. |
| **Supersedes** | v1.2 (previous commit of this file, `7e207ee`), v1.1 (`d5bc71f`), and the v1 proposal comment on views-models#149 (2026-07-02; demoted to pending-review 2026-07-06) |
| **Inputs folded in** | Producer seat: `views-pipeline-core/reports/wire_contract_v1.1_producer_seat_response.md` (2026-07-13). Consumer seat: `views-faoapi/reports/expert_reviews/2026-07-13_wire_contract_v1.1_consumer_response.md` (2026-07-13). Cross-seat: `views-postprocessing/reports/wire_contract_v1.1_seat_reconciliation.md` (2026-07-13, incl. the verified R1 finding). v1.3: the author's F1 verification (2026-07-13, both repos + faoapi `origin/main`). |
| **Adoption mechanics** | explicit maintainer sign-off on views-models#149, **enacted by landing the durable ADR** in views-postprocessing (§0.2). No adoption-by-silence. |

---

## Changelog v1.2 → v1.3 (author's post-reconciliation verification — finding F1)

| # | Change | Source finding |
|---|--------|----------------|
| 1 | **§4.1a gains the explicit producer obligation the name-pinning implied but never stated:** views-postprocessing **currently uploads the forecast document as `name=<ensemble name>`** (`unfao.py:314` — `rusty_bucket` today; only the historical complies, `:303`). Under the pinned schema, **all** Hop-B contract documents upload as the pinned consumer name — an explicit views-postprocessing change, owned by the #91 sink-adapter leg. | **F1** — author's verification of v1.2 against this repo's code (2026-07-13) |
| 2 | **§4.1a also records the discovered latent inconsistency in the CURRENT wire:** faoapi's `name` injection exists on **deployed `main` too** (`origin/main prediction.py:167-168`; the forecast fetch composes `{"category": ...}` then the search injects `name` — verified), so `rusty_bucket`-named forecast documents are latently **invisible** to faoapi *today*. Cannot be resolved from code alone (it may mean no forecast has ever been served via this path); **ground-truth against live Appwrite at run 0**. | F1 (verified on faoapi `origin/main` + `development`) |
| 3 | **§11.4 Hop-B rationale strengthened:** pinning `name="un_fao"` makes contract artifacts *visible* to the deployed legacy selector where legacy `rusty_bucket`-named forecasts were not — the D3 sequencing constraint (consumer guard before first upload) is therefore **more** acute under the contract, not less. | F1 |

## Changelog v1.1 → v1.2 (every change traceable to a named review finding)

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
| 9 | Housekeeping: `contract_version` example → `"1.2"`; §2.1 gains version semantics (MINOR = clarifying/additive, MAJOR = breaking); file renamed version-neutral (`wire_contract_DRAFT.md`) so the commit-per-iteration convention survives. | both seats' convention notes |

---

## §0 Status and provenance

**§0.1** The "platform ADR-046" cited across issues as declaring the FAO handoff format **does not exist** — a grep of every platform repo finds only dangling references, never a document. This contract replaces the phantom. Until adoption, the contract of record is *nothing*; on adoption it is the durable views-postprocessing ADR (§0.2) plus the ratifying comment on views-models#149.

**§0.2 Adoption mechanics.** Adoption = the maintainer's explicit sign-off on views-models#149, **enacted by landing the durable ADR in views-postprocessing** in the same motion. The ADR is not a follow-up; it is the adoption act. Implementation in any repo before that is out of contract. (views-pipeline-core#269 should state this precondition visibly.)

**§0.3 Ownership table.**

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

views-postprocessing is the anti-corruption layer: neither end format leaks past it. Hop A wraps exactly what PFE already writes (zero new serialization in pipeline-core; compatible with their #207 on-disk deferral and orthogonal to #139 Track-B retirement). Hop B is the format views-postprocessing#91 and views-faoapi#100 already ratified.

---

## §2 Shared contract header (both hops)

Carried as `metadata.json` inside the Hop-A archive, and inside the arrow file's `views_frames` schema-metadata JSON header (its open `metadata` dict — mechanism verified at `views_frames/io/arrow.py:69`; readable on the consumer side as `load(...)` → `state["metadata"]`).

```json
{
  "contract_version": "1.3",
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

**§2.1 Clauses.** Unknown keys MUST be ignored (open header, closed semantics for known keys). `contract_version` semantics: **MINOR bumps are clarifying/additive** (a 1.1 reader accepts a 1.2 artifact); **MAJOR bumps are breaking** and gate consumer rejection. `sample_count` and `dtype` are **parameters, not schema** — a small-S run is contract-conformant by construction; consumers reject `sample_count < S_min` (§6) rather than renegotiating the contract.

**§2.2 Identity & provenance.** `id_semantics` pins what the identifier arrays mean (`time` = VIEWS month-id; `unit` = `priogrid_id`) — this platform has already paid for leaving id vocabulary implicit (the gid/id epic). The `provenance` sub-schema is the three keys above, all strings/bool; **caveat:** version fields self-report and will be wrong until pipeline-core's release train (their #261) cuts real releases — provenance consumers must not treat `pipeline_core_version` as authoritative before then.

**§2.3 Governance hook.** Changes to `sample_count` (wire thinning, S_wire) or `dtype` on the **FAO delivery** alter the published HDI/MAP numbers and are therefore **re-baseline events**: they require sign-off under views-faoapi **ADR-023 ("Governance Gate for Re-baselining Published Forecasts", Accepted 2026-06-24)** before production use. The wire stays flexible; the product stays governed.

---

## §3 Hop A: the Track A archive (views-pipeline-core, #269)

**§3.1 Shard.** One object per **(run, target, month)**: a zip of exactly what PFE already writes — `y_pred.npy` shape `(N, S)` float32 + `identifiers.npz` (time/unit aligned to axis 0) — plus `metadata.json` (§2). Store document: `type="sampled_forecast_shard"`, `category="forecast"`, `loa`, `targets=[<target>]`, `name` per §3.3. ~265 MB/shard/target at S=1024 (64,742 cells).

**§3.2 Manifest — cardinality: one per (run, target).** `type="sampled_forecast_manifest"`: the shard list (store file-ids + content hashes), expected month set, expected cell count, and the sidecar hash (§5). **Uploaded last = the commit marker for that target's leg.** Consumers MUST ignore unmanifested shards; a killed producer leaves no manifest and therefore no visible (run, target). *Hop A deliberately keeps per-target cardinality:* the producer's targets complete independently, and the Hop-A consumer (views-postprocessing) — unlike faoapi — can trivially await all targets before acting (§4.2a). **Hash verification:** views-postprocessing verifies the shard content hashes against this manifest on read (it owns the integrity invariants).

**§3.3 Naming.** Shard `name`: `{run_id}__{target}__m{time_id:06d}.tap.zip`; manifest `name`: `{run_id}__{target}__manifest.json`. Both templates live as **shared constants with golden-string tests** in the producing repo. **The name is a locator only — identity is the manifest content + the embedded header.** Consumers MUST NOT parse identity out of filenames (the C-59/C-94 lesson).

**§3.4 Emission assertion (producer-side mechanism guard).** Before upload, the publish leg asserts its emission matches the frame it was handed — **against the staged files, pre-zip**: staged `y_pred` has `S == agg_pf.sample_count`, `dtype == float32`, `N == agg_pf.n_rows`; staged identifier arrays equal `agg_pf.identifiers`. The zip step itself is covered by the CI round-trip identity test (archive → unzip → `load_pf` reconstructs the identical frame; pipeline-core#269 acceptance) — the runtime assert stays cheap and runs on every publish. Verified feasible at the attach point (`prediction_frame_ensemble.py:593`, current HEAD, zero new imports). This is a *mechanism* assert (each hop vouches for its own emission) — the FAO *policy* lives only at §6.

**§3.5 Retention.** A full-S run ≈ 28.6 GB (3 targets × 36 months × ~265 MB) into `production_forecasts`, accumulating per run. Verified: no retention/TTL/quota mechanism exists anywhere in the store code today. **A retention owner and policy (quota / TTL / cleanup cadence) must be named at sign-off, before the first full-S production run.**

---

## §4 Hop B: arrow delivery (views-postprocessing → `unfao_bucket` → views-faoapi)

**§4.1 Shard.** One `views_frames.io.arrow` file per **(target, month)**, §2 header embedded. The **historical actuals+geo artifact is explicitly unchanged** (pandas parquet) in v1.2.

**§4.1a Store-document schema (pinned in v1.2).** faoapi's metadata schema makes all five fields **required at upload**, and its production query layer **unconditionally injects a `name` filter** (its model path always carries a model name) — a document with the wrong `name` is *invisible to the consumer*, not degraded. Therefore:

| Field | Value (Hop-B documents) |
|---|---|
| `category` | `"forecast"` |
| `type` | `"sampled_forecast_shard"` \| `"sampled_forecast_manifest"` \| `"sampled_forecast_sidecar"` |
| `name` | **the literal faoapi model name — `un_fao` today.** Config-owned by views-faoapi; changing it is a contract amendment, not a deploy detail. |
| `loa` | `"pgm"` |
| `targets` | shard: `[<target>]`; manifest/sidecar: the run's full target list |

Upload metadata must also remain compatible with faoapi's C-71 quarantine/approval filtering (approval fields present).

**Explicit producer obligation (new in v1.3).** views-postprocessing **currently uploads the forecast document as `name=<ensemble name>`** (`unfao.py:314` — `rusty_bucket` today); only the historical artifact already complies (`unfao.py:303`). Under this schema, **all Hop-B contract documents upload under the pinned consumer name** — this rename is an explicit views-postprocessing change, owned by its **#91 sink-adapter leg**.

**Discovered latent inconsistency in the CURRENT wire (recorded in v1.3, verified 2026-07-13).** faoapi's `name` injection is not new: it exists on deployed **`main`** as well (`prediction.py:167-168` there; the forecast fetch composes `{"category": ...}` and the search layer injects `name`). Consequently today's `rusty_bucket`-named forecast documents are latently **invisible** to faoapi on both branches. This cannot be resolved from code alone — it may mean no forecast has ever been served end-to-end via this path — and MUST be ground-truthed against live Appwrite at run 0 (which documents exist in `unfao_bucket`, under which names, and what deployed faoapi actually resolves).

**§4.2 Run manifest — cardinality: ONE per run, spanning all targets (changed in v1.2).** views-postprocessing emits **a single manifest per run** to `unfao_bucket`: the full Hop-B shard list **across all (target, month)** with content hashes, the expected month set, expected cell count, the run's target list, and the sidecar hash. `type="sampled_forecast_manifest"`, **uploaded last — after every target's shards = the run's single commit marker.** This closes the torn-run hole across the target axis: with per-target manifests a consumer refreshing between targets could assemble a run with one target present and others missing; with one run manifest that state is structurally invisible.

**§4.2a Run completeness (new in v1.2).** The **expected target set is views-postprocessing configuration** (it is the anti-corruption layer and owns the FAO product definition). views-postprocessing translates a run only when **all configured targets' Hop-A manifests** are present, and emits the §4.2 run manifest only after all targets' Hop-B shards are uploaded. The wire itself carries the resolved target list in the run manifest, so faoapi needs no external target-set knowledge.

**§4.3 Selection semantics.** The consumer serves only the **latest manifested run**: resolve the newest manifest (`get_latest_file_id(filters={"category": "forecast", "type": "sampled_forecast_manifest"})` — plus the auto-injected `name`; verified to fit faoapi's existing machinery unchanged), download it, then fetch exactly the shards it lists. With §4.2's cardinality there is exactly **one commit marker per run**, so "newest manifest" is well-defined.

**§4.4 Cache identity & the operational control point.** The run manifest's `file_id` is the run's cache key (fits faoapi's existing single-`file_id` `check_file_id` validation). A new manifest ⇒ a new run ⇒ cache invalidation; no per-shard cache bookkeeping. **The manifest is also the run's operational control point (new in v1.2):** quarantining the manifest's fileId (C-71 blocklist) — or deleting the manifest — atomically rolls the consumer back to the previous manifested run, without touching the 100+ shard objects. Operators act on manifests, never on shards. (Runbook line to land with faoapi#100.)

**§4.5 Ingest asserts (consumer-side mechanism guards, defense-in-depth).** At ingest the consumer asserts: **(a)** loaded S == manifest/header `sample_count`; **(b) ordering** — the arrow `sample` column equals `np.tile(np.arange(S, dtype=np.int32), N)` *before* it is discarded (rationale, verified: `arrow.save` writes that exact column at `io/arrow.py:47` but `arrow.load` never reads it and reconstructs `(N,S)` positionally at `:79-98` — a reordered or truncated table would produce plausible floats in wrong draw-slots, invisible downstream); **(c) hashes (new in v1.2)** — faoapi SHOULD verify shard content hashes against the run manifest at ingest (cheap; once per cache fill). These are mechanism guards; the §6 policy is not duplicated here.

**§4.6 Capacity & the intended consumer model.** At the reference parameters a fully-assembled run ≈ 28.6 GB resident — larger than the serving host. **Before a production S is chosen, the capacity inequality `assembled-run size × safety factor ≤ consumer serving RAM` must be owned** — either by choosing wire parameters that satisfy it, or (the intended direction) by **lazy per-month consumption**: the per-(target, month) sharding exists precisely so the consumer can load shards on demand with a month-keyed cache, which dissolves the memory wall without mmap. Documented caveat stands: `arrow.load` is read-all-to-RAM per file (no mmap today; ~1.6 GB transient per full-S shard); per-month sharding is the mitigation, and mmap/partitioned arrow remains future views-frames work, not a contract dependency.

---

## §5 GAUL geography sidecar

**§5.1 Schema.** One gid-keyed sidecar artifact per run (~64,742 rows), `type="sampled_forecast_sidecar"` (store-document fields per §4.1a), keyed by `priogrid_id`, with **exactly these 9 columns**: `pg_xcoord` (float64), `pg_ycoord` (float64), `country_iso_a3` (string), `admin1_gaul1_code`, `admin1_gaul1_name`, `admin1_gaul0_code`, `admin1_gaul0_name`, `admin2_gaul2_code`, `admin2_gaul2_name` — `*_name`/`country_iso_a3` as **plain strings** (not categorical; verified the consumer does no categorical coercion), `*_code` numeric (int64 when complete; float64 where NaN is present). **Rows with missing GAUL codes are PRESERVED with NaN, never pre-dropped** — the consumer drops them at aggregation under its own legacy-parity rule (their C-146 machinery, verified). Silent pre-dropping would silently mislabel geography.

**§5.2 Consistency.** Sidecar gid-set == forecast gid-set (enforced by views-postprocessing's existing coverage/identity invariants, extended to the sidecar); the sidecar hash is pinned in **each Hop-A (run, target) manifest (§3.2) and in the Hop-B run manifest (§4.2)**. Delivered once per run, not per shard — the whole point is not replicating static strings ×S×36.

---

## §6 The no-collapse boundary — owner: **views-postprocessing** `delivery/draws.py`

A new representation-free invariant `views_postprocessing/delivery/draws.py` (sibling of the existing coverage/identity/observed-range/provenance invariants) raises `DrawsCollapseError` unless:

1. values are 2-D `(N, S)`;
2. payload S == header `sample_count`;
3. `sample_count >= S_min` (config: 2 for the walking skeleton; region-pinned for production);
4. **globally** ≥1 row with >1 distinct draw value. *Explicit non-rule: per-row zero variance is legal — zero-conflict cells dominate PGM; the check is global-across-rows, never per-row.*

Runs before every FAO-facing forecast upload. This is the single **policy** gate; the §3.4/§4.5 emission/ingest asserts are per-hop **mechanism** guards that localize faults without duplicating the policy (the D-A synthesis: bulkheads plus one gate). **Note (v1.2):** check 2 deliberately re-validates what §4.5(a) already checked at ingest — the policy gate vouches for its own input. This redundancy is intentional and MUST NOT be removed as a "simplification."

---

## §7 Prerequisites

- **(a) Target naming — DECIDED (maintainer, 2026-07-02):** canonical wire vocabulary `lr_ged_sb` / `lr_ged_ns` / `lr_ged_os`; producers rename at publish (no `_best` on a draws wire). The internal→wire mapping lives in **one shared constant** in the producing repo, cited by the golden fixture.
- **(b)** The `APPWRITE_PROD_FORECASTS_COLLECTION_ID` config fix (views-models#230-A) — the documented `forecasts_metadata` does not exist in live Appwrite.
- **(c) ADR numbering:** views-faoapi's consumer-side ADR is **ADR-031** (verified: 000–030 taken). faoapi#100 to be retitled off "ADR-046".

---

## §8 Non-goals v1.2 (with recorded deferred intents)

- **cm level & the second store** (views-postprocessing#97): inherit later via `spatial_level`; reconciliation already runs upstream in PFE, draws-aware.
- **Historical artifact format**: unchanged pandas parquet.
- **mmap / partitioned arrow**: future views-frames work (a hardening issue for `io.arrow` — ordering validation on load + mmap — should be filed at execution; not a contract dependency).
- **Concrete S_wire / dtype values**: parameters (§2.1) with a governance gate (§2.3).
- **Deferred intent (recorded, not adopted):** consolidate the §2 header vocabulary into `views_frames.FrameMetadata` via a MINOR extension once the fixture-pinned header has stabilized; extract a shared sharded-run reader into views-frames only after both hand-rolled consumers exist (WET-before-DRY).

---

## §9 Corrections to prior claims (line refs at verified HEADs)

views-models#143's "no new aggregation mode **or pipeline-core change** is required" is **falsified for the publish leg**: PFE's `use_prediction_store` is accepted (`prediction_frame_ensemble.py:143`), stored (`:154`), and only ever logged (`:812`) — no `DatastoreModule` is constructed and no upload occurs; forecast output is local-only (`save_pf`, `:593`); `PredictionIOManager._upload_to_prediction_store` raises `NotImplementedError` for Arrow tables (`managers/prediction/io.py:111+`); Track B parquet is disabled for PF models. **No code path exists by which any sampled forecast reaches the prediction store.** pipeline-core#269 is the fix; its inline line refs (written 2026-07-02) are stale and should be corrected to the above when amended.

---

## §10 Golden fixture (the executable spec)

One canonical **small-S fixture** — a Track-A shard archive + its Hop-B arrow shard + the geo sidecar + both manifests (one Hop-A target manifest, one Hop-B run manifest), generated at S=4 with synthetic values — is committed alongside the durable ADR and **versioned with `contract_version`**. All three implementing repos' test suites consume the same fixture bytes: the producer proves it emits them, the anti-corruption layer proves it translates them, the consumer proves it ingests them. The fixture **pins the header JSON byte-for-byte** (this is what makes two hand-written header writers safe without a shared constructor). A change to the fixture is a change to the contract.

**§10.1 Distribution (new in v1.2).** The fixture bytes live in **this repo** (beside the ADR). The other two repos **vendor a copy** and carry a **pinned content-hash equality test**: the hash — recorded here next to the fixture — is the cross-repo contract; a mismatch fails loud with "re-vendor the fixture from views-postprocessing@\<ref\>". No CI network dependency; no silent drift through the back door.

**§10.2 Injectable provenance (new in v1.2).** Byte-for-byte header parity requires producers to accept **injected `run_id` and `generated_at`** in test mode (a keyword or clock/id seam — not global state). pipeline-core#269 should plan its header writer accordingly.

---

## §11 Sequencing & verification vehicle

**§11.1 Small-S first.** Because `sample_count` is header data, a placeholder low-S ensemble is contract-conformant — the walking skeleton (views-models#230) runs end-to-end **at S=8 with synthetic constituents** as the contract's verification vehicle (the plumbing proof; only the *scale* proof waits on views-models#143/#146 tuning).

**§11.2 Run-0 allowance.** The Hop-B run manifest is adopted **in text now**; run-0 of the skeleton may precede its implementation (manual verification for run 0 only) — the D-x1 resolution.

**§11.3 Parallelism.** The only serial edge (naming) is decided (§7a). views-postprocessing's legs (`draws.py`, source adapter, sink adapter, sidecar, manifests) ∥ pipeline-core's publish leg (#269) ∥ faoapi's ingest (#100, recommended re-scoped as an epic: skeleton-ingest → assembly + sidecar join → cache re-key → transition guard (§11.4) → dual-format window, with the §4.5 asserts).

**§11.4 Transition rule — BOTH hops (strengthened in v1.2).** A contract artifact is identified by the `views_frames` KV header (Hop B) / `metadata.json` (Hop A) — never by filename. Once a manifested run exists in a store, legacy artifacts there are ignored. **Sequencing constraint (consumer D3 + reconciliation R1):** at **each** store, the type-aware consumer — or at minimum a `type`-guard in the deployed legacy reader — must be **live before the first contract artifact is uploaded there**:

- **Hop B:** deployed faoapi selects newest-`category="forecast"` with no `type` awareness — and (v1.3) since it *name-filters* on the pinned consumer name, the contract wave's `name="un_fao"` documents become **visible to the legacy selector** precisely where legacy `rusty_bucket`-named forecasts were not. The first Hop-B upload would be grabbed as "the forecast" by the deployed code — the sequencing constraint is *more* acute under the contract, not less.
- **Hop A (verified 2026-07-13):** the legacy views-postprocessing reader has the same selection shape (`unfao.py:110`, `get_latest_file_id(filters={"category": "forecast"})`). Its identity assertion (`unfao.py:123`) makes the failure **loud, not silent** — an outage, not corruption — but the constraint stands: views-postprocessing's type-aware source adapter (its #85 S3+), or a one-line `type` filter in the legacy reader, lands **before pipeline-core#269's first live upload**.

Skeleton ordering therefore is: **consumer guards → producer legs → run 0.**

---

*Draft ends. Both seats are on record sign-off-ready (v1.1 responses + reconciliation); v1.2 folds all their deltas. Next step: the §0.2 adoption act. Review deltas → v1.3 as new commits to this file.*
