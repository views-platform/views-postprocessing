# Sampled-Forecast Wire Contract — v1.1 DRAFT

| | |
|---|---|
| **Status** | **DRAFT — for multi-agent + maintainer review. NOT posted, NOT adopted.** Iterations (v1.2, v1.3 …) expected; each is a new commit to this file so review deltas are git-diffable. |
| **Supersedes** | the v1 proposal comment on views-models#149 (2026-07-02; demoted to pending-review 2026-07-06) |
| **Inputs folded in** | the two seat reviews: `views-pipeline-core/reports/expert_review_views_models_149_fao_no_collapse.md` (2026-07-05) and `views-faoapi/reports/expert_reviews/2026-07-06_wire_contract_v1_consumer_review.md` (2026-07-06) — plus a verification pass (2026-07-06) that re-checked every load-bearing review claim against code |
| **Adoption mechanics** | explicit maintainer sign-off on views-models#149, **enacted by landing the durable ADR** in views-postprocessing (§0.2). No adoption-by-silence. |

---

## Changelog v1 → v1.1 (every change traceable to a named review finding)

| # | Change | Source finding |
|---|--------|----------------|
| 1 | **Hop-B manifest + selection semantics added (§4.2–§4.4)** — the manifest is re-emitted to `unfao_bucket`; consumers serve only the latest *manifested* run; manifest file-id is the cache key; shard enumeration comes from manifest content. Fixes v1's internal incoherence (§5 pinned the sidecar hash "in the manifest" at a hop that had no manifest). | faoapi review C-x1; GoF/Nygard/Hickey convergence; D-x1 resolution (text now, run-0 may precede implementation) |
| 2 | **Per-hop emission asserts, single policy gate (§3.4, §4.5, §6)** — each producing hop asserts its own emission matches its input frame; the S_min *policy* stays solely at the §6 boundary. | pipeline-core review D-A synthesis + C-a |
| 3 | **Ordering-validating ingest assert (§4.5)** — `views_frames.io.arrow.load` reconstructs `(N,S)` positionally and never reads the `sample` column (verified `io/arrow.py:79-98`); consumers must validate `sample == np.tile(np.arange(S, dtype=np.int32), N)` before reshape/discard. | faoapi review C-x5 (verified) |
| 4 | **Sidecar schema pinned (§5.1)** — the 9 exact columns, wire dtypes, and the **NaN-rows-preserved** rule. | faoapi review C-x4 / their C-146 (verified) |
| 5 | **Governance hook (§2.3)** — S_wire/dtype changes on the FAO delivery are re-baseline events requiring sign-off under views-faoapi **ADR-023 "Governance Gate for Re-baselining Published Forecasts"** before production use. | faoapi review C-x3; Kleppmann/D-x3 resolution (parameters on the wire, governance at the consumer) |
| 6 | **Golden fixture clause (§10)** — one canonical small-S shard + sidecar + manifest as the executable spec, consumed by all three implementing repos' test suites; pins the header JSON byte-for-byte. | both reviews (Feathers/Beck + Kleppmann/GoF); also the v1.1 substitute for the FrameMetadata-constructor ask (see §8 deferred) |
| 7 | **Capacity + lazy-loading clause (§4.6)** — the capacity inequality must be owned before production S is chosen; lazy per-month consumption named as the intended consumer direction at scale. | faoapi review C-x2 + Ousterhout |
| 8 | **Retention/quota owner clause (§3.5)** — ~28.6 GB/run accumulates in `production_forecasts`; a retention owner must be named before the first full-S production run. Verified: no retention/TTL/quota concept exists anywhere in pipeline-core's store code (only client cache TTL). | pipeline-core review C-d (store-side sibling of their C-207) |
| 9 | **Identity & naming hygiene (§2.2, §3.3)** — `id_semantics` added to the header; provenance sub-schema + the pre-release version-stamp caveat; shard/manifest name templates as shared constants with golden-string tests; **manifest content, never filenames, is identity**. | pipeline-core review C-c + Kleppmann (their C-59/C-94/C-203 precedents) |
| 10 | **Hygiene** — every "vpp" spelled out as **views-postprocessing** (a reviewer read "vpp" as pipeline-core — proof of ambiguity); durable ADR = the adoption act; faoapi's planned ADR renumbered **031** (024 collides with their accepted `024_raw_count_serving_contract.md`); faoapi#100 to be retitled off the phantom "ADR-046"; views-models#149's body to be updated to match this contract; pipeline-core line refs corrected to current HEAD (`save_pf` at `prediction_frame_ensemble.py:593`, not `:580`). | both reviews; verification pass (zero drift from reviewed `3adc859`) |
| — | **Recorded but NOT adopted for v1.1:** generating the header from `views_frames.FrameMetadata` (right destination, wrong gate — needs a views-frames MINOR and a shared library to be truly shared; the golden fixture pins the bytes instead); a shared sharded-reader in views-frames (WET-before-DRY: hand-roll both consumers, extract on proven duplication). Both listed in §8 as deferred intents. | pipeline-core D-C; faoapi D-x2 / Ousterhout |

---

## §0 Status and provenance

**§0.1** The "platform ADR-046" cited across issues as declaring the FAO handoff format **does not exist** — a grep of every platform repo finds only dangling references, never a document. This contract replaces the phantom. Until adoption, the contract of record is *nothing*; on adoption it is the durable views-postprocessing ADR (§0.2) plus the ratifying comment on views-models#149.

**§0.2 Adoption mechanics.** Adoption = the maintainer's explicit sign-off on views-models#149, **enacted by landing the durable ADR in views-postprocessing** in the same motion. The ADR is not a follow-up; it is the adoption act. Implementation in any repo before that is out of contract. (views-pipeline-core#269 should state this precondition visibly.)

**§0.3 Ownership table.**

| Leg | Owner |
|---|---|
| Hop A producer (PFE → prediction store) | views-pipeline-core (#269) |
| Hop A consumer + Hop B producer + **the no-collapse policy boundary (§6)** | **views-postprocessing** |
| Hop B consumer (`unfao_bucket` → serving) | views-faoapi (#100) |
| `production_forecasts` retention (§3.5) | named at sign-off (infrastructure owner) |

---

## §1 Topology — two hops, one interior representation

```
PFE (per-target y_pred.npy (N,S) float32 + identifiers.npz, local disk)
  ── Hop A: Track A archive (zip), one per (run, target, month);
            manifest object uploaded LAST = commit marker ──►  Appwrite `production_forecasts`
views-postprocessing
  (interior: per-target 2-D PredictionFrame via from_arrays; the anti-corruption layer;
   owns the §6 no-collapse policy boundary)
  ── Hop B: one views_frames.io.arrow file per (target, month) + geo sidecar +
            re-emitted manifest (LAST = commit marker) ──►  Appwrite `unfao_bucket`
views-faoapi (serve; MAP/HDI at the edge)
```

views-postprocessing is the anti-corruption layer: neither end format leaks past it. Hop A wraps exactly what PFE already writes (zero new serialization in pipeline-core; compatible with their #207 on-disk deferral and orthogonal to #139 Track-B retirement). Hop B is the format views-postprocessing#91 and views-faoapi#100 already ratified.

---

## §2 Shared contract header (both hops)

Carried as `metadata.json` inside the Hop-A archive, and inside the arrow file's `views_frames` schema-metadata JSON header (its open `metadata` dict — mechanism verified at `views_frames/io/arrow.py:69`; readable on the consumer side as `load(...)` → `state["metadata"]`).

```json
{
  "contract_version": "1.1",
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

**§2.1 Clauses.** Unknown keys MUST be ignored (open header, closed semantics for known keys). `contract_version` gates breaking changes. `sample_count` and `dtype` are **parameters, not schema** — a small-S run is contract-conformant by construction; consumers reject `sample_count < S_min` (§6) rather than renegotiating the contract.

**§2.2 Identity & provenance.** `id_semantics` pins what the identifier arrays mean (`time` = VIEWS month-id; `unit` = `priogrid_id`) — this platform has already paid for leaving id vocabulary implicit (the gid/id epic). The `provenance` sub-schema is the three keys above, all strings/bool; **caveat:** version fields self-report and will be wrong until pipeline-core's release train (their #261) cuts real releases — provenance consumers must not treat `pipeline_core_version` as authoritative before then.

**§2.3 Governance hook.** Changes to `sample_count` (wire thinning, S_wire) or `dtype` on the **FAO delivery** alter the published HDI/MAP numbers and are therefore **re-baseline events**: they require sign-off under views-faoapi **ADR-023 ("Governance Gate for Re-baselining Published Forecasts", Accepted 2026-06-24)** before production use. The wire stays flexible; the product stays governed.

---

## §3 Hop A: the Track A archive (views-pipeline-core, #269)

**§3.1 Shard.** One object per **(run, target, month)**: a zip of exactly what PFE already writes — `y_pred.npy` shape `(N, S)` float32 + `identifiers.npz` (time/unit aligned to axis 0) — plus `metadata.json` (§2). Store document: `type="sampled_forecast_shard"`, `category="forecast"`, `loa`, `targets=[<target>]`, `name` per §3.3. ~265 MB/shard/target at S=1024 (64,742 cells).

**§3.2 Manifest.** One per **(run, target)**, `type="sampled_forecast_manifest"`: the shard list (store file-ids + content hashes), expected month set, expected cell count, and the sidecar hash (§5). **Uploaded last = the commit marker.** Consumers MUST ignore unmanifested shards; a killed producer leaves no manifest and therefore no visible run.

**§3.3 Naming.** Shard `name`: `{run_id}__{target}__m{time_id:06d}.tap.zip`; manifest `name`: `{run_id}__{target}__manifest.json`. Both templates live as **shared constants with golden-string tests** in the producing repo. **The name is a locator only — identity is the manifest content + the embedded header.** Consumers MUST NOT parse identity out of filenames (the C-59/C-94 lesson).

**§3.4 Emission assertion (producer-side mechanism guard).** Before upload, the publish leg asserts its emission matches the frame it was handed: archive `S == agg_pf.sample_count`; `dtype == float32`; `N == agg_pf.n_rows`; identifier arrays equal `agg_pf.identifiers`. Verified feasible at the attach point (`prediction_frame_ensemble.py:593`, current HEAD, zero new imports). This is a *mechanism* assert (each hop vouches for its own emission) — the FAO *policy* lives only at §6.

**§3.5 Retention.** A full-S run ≈ 28.6 GB (3 targets × 36 months × ~265 MB) into `production_forecasts`, accumulating per run. Verified: no retention/TTL/quota mechanism exists anywhere in the store code today. **A retention owner and policy (quota / TTL / cleanup cadence) must be named at sign-off, before the first full-S production run.**

---

## §4 Hop B: arrow delivery (views-postprocessing → `unfao_bucket` → views-faoapi)

**§4.1 Shard.** One `views_frames.io.arrow` file per **(target, month)**, §2 header embedded. The **historical actuals+geo artifact is explicitly unchanged** (pandas parquet) in v1.1.

**§4.2 Manifest (new in v1.1).** views-postprocessing **re-emits the run manifest to `unfao_bucket`** — same content model as §3.2 (its Hop-B shard list + hashes, expected months/cells, sidecar hash), `type="sampled_forecast_manifest"`, **uploaded last = the commit marker**. This closes the torn-run hole (a cache refresh mid-upload can no longer assemble a partial horizon), restores the sidecar-hash integrity chain end-to-end, and gives the consumer its selection rule and cache key.

**§4.3 Selection semantics.** The consumer serves only the **latest manifested run**: resolve the newest manifest (`get_latest_file_id(filters={"category": "forecast", "type": "sampled_forecast_manifest"})` — verified to fit faoapi's existing machinery unchanged: filters map to `Query.equal` on any metadata attribute; `type` is already a required upload field; newest-wins on `$createdAt`), download it, then fetch exactly the shards it lists. **Caveat (verified):** faoapi's query layer auto-injects a `name` filter when its model_path carries one, and applies C-71 quarantine/approval filtering — manifest upload metadata must carry compatible `name`/approval fields.

**§4.4 Cache identity.** The manifest's `file_id` is the run's cache key (fits faoapi's existing single-`file_id` `check_file_id` validation). A new manifest ⇒ a new run ⇒ cache invalidation; no per-shard cache bookkeeping.

**§4.5 Ingest asserts (consumer-side mechanism guards, defense-in-depth).** At ingest the consumer asserts: (a) loaded S == manifest/header `sample_count`; (b) **ordering** — the arrow `sample` column equals `np.tile(np.arange(S, dtype=np.int32), N)` *before* it is discarded. Rationale (verified): `arrow.save` writes that exact column (`io/arrow.py:47`) but `arrow.load` never reads it and reconstructs `(N,S)` positionally (`:79-98`) — a reordered or truncated table would produce plausible floats in wrong draw-slots, invisible downstream. These are mechanism guards; the §6 policy is not duplicated here.

**§4.6 Capacity & the intended consumer model.** At the reference parameters a fully-assembled run ≈ 28.6 GB resident — larger than the serving host. **Before a production S is chosen, the capacity inequality `assembled-run size × safety factor ≤ consumer serving RAM` must be owned** — either by choosing wire parameters that satisfy it, or (the intended direction) by **lazy per-month consumption**: the per-(target, month) sharding exists precisely so the consumer can load shards on demand with a month-keyed cache, which dissolves the memory wall without mmap. Documented caveat stands: `arrow.load` is read-all-to-RAM per file (no mmap today; ~1.6 GB transient per full-S shard); per-month sharding is the mitigation, and mmap/partitioned arrow remains future views-frames work, not a contract dependency.

---

## §5 GAUL geography sidecar

**§5.1 Schema (pinned in v1.1).** One gid-keyed sidecar artifact per run (~64,742 rows), `type="sampled_forecast_sidecar"`, keyed by `priogrid_id`, with **exactly these 9 columns**: `pg_xcoord` (float64), `pg_ycoord` (float64), `country_iso_a3` (string), `admin1_gaul1_code`, `admin1_gaul1_name`, `admin1_gaul0_code`, `admin1_gaul0_name`, `admin2_gaul2_code`, `admin2_gaul2_name` — `*_name`/`country_iso_a3` as **plain strings** (not categorical; verified the consumer does no categorical coercion), `*_code` numeric (int64 when complete; float64 where NaN is present). **Rows with missing GAUL codes are PRESERVED with NaN, never pre-dropped** — the consumer drops them at aggregation under its own legacy-parity rule (their C-146 machinery, verified). Silent pre-dropping would silently mislabel geography.

**§5.2 Consistency.** Sidecar gid-set == forecast gid-set (enforced by views-postprocessing's existing coverage/identity invariants, extended to the sidecar); the sidecar hash is pinned in **both** manifests (§3.2, §4.2). Delivered once per run, not per shard — the whole point is not replicating static strings ×S×36.

---

## §6 The no-collapse boundary — owner: **views-postprocessing** `delivery/draws.py`

*(v1 said "vpp owns it"; a reviewer read "vpp" as pipeline-core. For the record: the owner is **views-postprocessing**.)*

A new representation-free invariant `views_postprocessing/delivery/draws.py` (sibling of the existing coverage/identity/observed-range/provenance invariants) raises `DrawsCollapseError` unless:

1. values are 2-D `(N, S)`;
2. payload S == header `sample_count`;
3. `sample_count >= S_min` (config: 2 for the walking skeleton; region-pinned for production);
4. **globally** ≥1 row with >1 distinct draw value. *Explicit non-rule: per-row zero variance is legal — zero-conflict cells dominate PGM; the check is global-across-rows, never per-row.*

Runs before every FAO-facing forecast upload. This is the single **policy** gate; the §3.4/§4.5 emission/ingest asserts are per-hop **mechanism** guards that localize faults without duplicating the policy (the D-A synthesis: bulkheads plus one gate).

---

## §7 Prerequisites

- **(a) Target naming — DECIDED (maintainer, 2026-07-02):** canonical wire vocabulary `lr_ged_sb` / `lr_ged_ns` / `lr_ged_os`; producers rename at publish (no `_best` on a draws wire). The internal→wire mapping lives in **one shared constant** in the producing repo, cited by the golden fixture.
- **(b)** The `APPWRITE_PROD_FORECASTS_COLLECTION_ID` config fix (views-models#230-A) — the documented `forecasts_metadata` does not exist in live Appwrite.
- **(c) ADR numbering:** views-faoapi's consumer-side ADR is **ADR-031** (verified: 000–030 taken; their review's earlier "new ADR-024" collides with the accepted `024_raw_count_serving_contract.md`). faoapi#100 to be retitled off "ADR-046" (title verified still carrying it).

---

## §8 Non-goals v1.1 (with recorded deferred intents)

- **cm level & the second store** (views-postprocessing#97): inherit later via `spatial_level`; reconciliation already runs upstream in PFE, draws-aware.
- **Historical artifact format**: unchanged pandas parquet.
- **mmap / partitioned arrow**: future views-frames work (a hardening issue for `io.arrow` — ordering validation on load + mmap — should be filed at execution; not a contract dependency).
- **Concrete S_wire / dtype values**: parameters (§2.1) with a governance gate (§2.3).
- **Deferred intent (recorded, not adopted):** consolidate the §2 header vocabulary into `views_frames.FrameMetadata` via a MINOR extension once the fixture-pinned header has stabilized; extract a shared sharded-run reader into views-frames only after both hand-rolled consumers exist (WET-before-DRY).

---

## §9 Corrections to prior claims (line refs at current HEAD, verified zero-drift)

views-models#143's "no new aggregation mode **or pipeline-core change** is required" is **falsified for the publish leg**: PFE's `use_prediction_store` is accepted (`prediction_frame_ensemble.py:143`), stored (`:154`), and only ever logged (`:812`) — no `DatastoreModule` is constructed and no upload occurs; forecast output is local-only (`save_pf`, `:593`); `PredictionIOManager._upload_to_prediction_store` raises `NotImplementedError` for Arrow tables (`managers/prediction/io.py:111+`); Track B parquet is disabled for PF models. **No code path exists by which any sampled forecast reaches the prediction store.** pipeline-core#269 is the fix; its inline line refs (written 2026-07-02) are stale and should be corrected to the above when amended.

---

## §10 Golden fixture (the executable spec — new in v1.1)

One canonical **small-S fixture** — a Track-A shard archive + its Hop-B arrow shard + the geo sidecar + both manifests, generated at S=4 with synthetic values — is committed alongside the durable ADR and **versioned with `contract_version`**. All three implementing repos' test suites consume the same fixture bytes: the producer proves it emits them, the anti-corruption layer proves it translates them, the consumer proves it ingests them. The fixture **pins the header JSON byte-for-byte** (this is what makes two hand-written header writers safe without a shared constructor). A change to the fixture is a change to the contract.

---

## §11 Sequencing & verification vehicle

- Small-S first: because `sample_count` is header data, a placeholder low-S ensemble is contract-conformant — the walking skeleton (views-models#230) runs end-to-end **at S=8 with synthetic constituents** as the contract's verification vehicle (the plumbing proof; only the *scale* proof waits on views-models#143/#146 tuning).
- The Hop-B manifest is adopted **in text now**; run-0 of the skeleton may precede its implementation (manual verification for run 0 only) — the D-x1 resolution.
- The only serial edge (naming) is decided (§7a). views-postprocessing's legs (`draws.py`, source adapter, sink adapter, sidecar, manifests) ∥ pipeline-core's publish leg (#269) ∥ faoapi's ingest (#100, recommended re-scoped as an epic: skeleton-ingest → assembly + sidecar join → cache re-key → dual-format window, with the §4.5 ordering assert).
- **Format-detection & transition rule:** a contract artifact is identified by the `views_frames` KV header (Hop B) / `metadata.json` (Hop A) — never by filename. Once a manifested run exists in `unfao_bucket`, legacy nested-parquet forecast artifacts are ignored.

---

*Draft ends. Review deltas → v1.2, v1.3 as new commits to this file.*
