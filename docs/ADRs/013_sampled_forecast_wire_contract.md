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
to every downstream consumer **without ever being collapsed back to a single number**
along the way. The FAO delivery is the *first* consumer and the scoping case for this
contract (§8): the header's `spatial_level` field exists precisely so later stores
and levels inherit the same pattern rather than negotiating a new one.

That journey crosses four repositories — views-models and views-pipeline-core on the
producing side, views-postprocessing in the middle, views-faoapi at the serving end
(all but views-models implement a wire leg, hence "three implementing repos" in §10)
— and two storage transfers, and before this document no written agreement governed
it: the "ADR-046" everyone cited contained no
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
- **Hop** — one of the two storage transfers **the forecast** makes in this
  contract's delivery (later stores repeat the same two-hop shape — §8): **Hop A** =
  pipeline → the Appwrite `production_forecasts` store (internal warehouse); **Hop B**
  = views-postprocessing → the Appwrite `unfao_bucket` store (what views-faoapi serves
  FAO from). *Appwrite* is the cloud storage service both live on. The *historical*
  (observed actuals) artifact takes neither hop: it goes directly from
  views-postprocessing to `unfao_bucket` and is explicitly out of this contract's
  scope (§4.1, §8).
- **PFE** — the *PredictionFrameEnsemble*, pipeline-core's ensemble manager: the
  producer whose output this contract packages.
- **Run / target / month** — one production forecast generation (a *run*) predicts a
  configured set of *target* variables (currently state-based, non-state, and
  one-sided violence deaths — **the set is configuration, not contract**: §4.2a, and
  new targets join per §7a) for a horizon of future *months* (currently 36 — carried
  as data in the header's `sharding.count`, not fixed here), over the PGM cells the
  run covers (*PGM* = PRIO-GRID monthly: one row per 0.5°×0.5° land grid cell per
  month; a cell's id is its `priogrid_id`, a month's id is the VIEWS `month_id`
  integer; PGM is *this delivery's* level — the header's `spatial_level` field keeps
  the pattern level-neutral, §8). **The cell count is declared data, never
  assumed**: each shipment states
  its own count in its manifest and identifier arrays, so a regional run (e.g.
  Africa + Middle East) and a global run conform equally. The ~64,742 figure used in
  size estimates below is the *global land-cell reference*, an upper bound for
  capacity math only. ⚠ *Naming collision (historical):* elsewhere in the platform
  `run_type` means the data-partition regime — *calibration / validation /
  forecasting* (e.g. pipeline-core `model_path.py`). **In this contract "run" never
  means that**: it is one production forecast-generation execution, identified by
  its `run_id`, and is always of the *forecasting* regime — the partition
  vocabulary plays no role on this wire. (Someday rename of `run_type` →
  `partition` tracked as views-models#262.)
- **N and S** — a payload is a 2-D table of values with `N` rows (one per cell) and
  `S` columns (one per sample). Production aims at S≈1024.
- **Shard** — one piece of a run's data, cut per (target, month), stored as one
  file. ("Shard" is a general data-engineering term for splitting one logical
  dataset into pieces — it has no tie to any particular file format.) Sharding
  exists because a whole run (~9.5 GB per target at full S and the global reference
  parameters) is too big to move as one object.
- **Manifest** — a small JSON file listing every shard in its scope — one manifest
  per (run, target) at Hop A (§3.2), one per whole run at Hop B (§4.2) — with a
  SHA-256 *content hash* (a fingerprint of the exact bytes) per shard, plus what
  that scope is expected to contain. It is uploaded **last**, so its presence means "everything before me is
  complete" — we call that the *commit marker*. A run whose upload died halfway (a
  *torn run*) has no manifest and is therefore invisible to consumers.
- **Sidecar** — a separate small file carrying the static geography lookup (country,
  admin regions) per cell, shipped once per run instead of being copied into every
  row of every shard.
- **S_min** — the minimum sample count the delivery will pass on: the floor
  enforced by the §6 gate *before* upload (consumers may re-check it). It protects
  downstream consumers from accidentally-collapsed forecasts.
- **Anti-corruption layer** — the middleman role views-postprocessing plays,
  borrowed from software-design vocabulary. Despite the name, it is not about data
  damage: the "corruption" it prevents is one system's *internal format and
  assumptions* seeping into another system's code. Think of a customs-and-translation
  office: everything arriving from the producer is inspected and re-expressed before
  it travels on, so the producer never needs to know any partner's format, and no
  partner ever needs to know the producer's. The payoff is independence — either
  side can change its internals and only the translator must adapt.

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
this contract to be confirmed by the repo that owns it; all of those ratification
preconditions were met before adoption (the verification trail is in Appendix A).
One sign-off *duty* was nonetheless missed despite that: the §3.5 retention owner
was never named — see role 5 below; the two statements are not in conflict, one is
about claim ratification, the other an unmet naming duty.

**§0.2a Execution status (as of 2026-07-19 — the dated Post-adoption record at the
end of this document is the running log).** Adopted does not mean built. Built and
merged: the Hop-A publish leg (pipeline-core PR #276), the Hop-A source adapter
(this repo, PR #101), the golden fixture, and both legacy guards. Not yet built:
the Hop-B sink leg (this repo, #91). Merged but not yet deployed: the Hop-B legacy
guard awaits faoapi's production release (C-161; their deploy epic #184). And the
plain operational truth: FAO forecast serving is currently **empty** — no forecast
has ever been servable end-to-end on the legacy path (wrong document name; see the
Post-adoption record, 2026-07-15). Nothing may upload to `unfao_bucket` before the
guard is live (§11.4).

**§0.3 Ownership.** Five responsibilities, told in the order the data flows. (The
short version, peer-to-peer: *pipeline-core ships, views-postprocessing checks and
repacks, the partner's API serves; our configuration defines what "complete"
means, and cleanup of the internal store has no owner yet.*)

1. **Putting forecasts on the internal shelf — views-pipeline-core.** Its publish
   leg (#269) uploads every run's archives to `production_forecasts`. This happens
   once per run and is **shared**: every partner delivery, present and future,
   draws from this same shelf. Adding a partner never touches the producer.
   Uploads become visible only when whole: the last object uploaded is the packing
   list (the manifest — the *commit marker*, §3.2/§4.2), so a run whose upload
   died halfway has no marker and is structurally invisible to every consumer.

2. **Everything in the middle — views-postprocessing.** Take the run off the
   internal shelf, verify it (hashes, headers), run the **§6 no-collapse gate**
   (refuse to ship a forecast whose ~1000 samples per cell have been squashed
   back toward a single number), repack it in the partner's format, and place it
   in the partner's bucket. This middleman role is what the Vocabulary calls the
   *anti-corruption layer* — the customs-and-translation office between producer
   and partners. The leg is **per partner**: FAO's is the one being built (its
   sink half is open as #91; what runs in production is the legacy point-estimate
   delivery this replaces — see §0.2a); a UN CRAFD or UN OCHA delivery would each
   get their own copy. One exception rides no hop: the *historical* (observed
   actuals) artifact goes straight from views-postprocessing to the partner
   bucket (Vocabulary; §4.1).

3. **Defining "complete" — views-postprocessing configuration.** A maintained
   *setting* (not code) lists which targets a finished run must contain; the
   middle leg refuses to ship until everything on that list has arrived (§4.2a).
   The list is declared by a human decision and never inferred from what happens
   to show up. **Per partner.** Do not confuse this *delivery definition* with
   views-models' *delivery pointer* (table row 1): the pointer says **which
   source supplies which partner** (the supplier contract, repointed when
   modeling strategy changes); the definition says **what that partner's
   shipment must contain to ship at all** (the order specification, tightened
   when the partner relationship changes). Either can change without touching
   the other.

4. **Serving the partner — the partner's API repo.** For FAO: views-faoapi (#100)
   reads `unfao_bucket` and answers FAO's requests, computing point estimates and
   uncertainty intervals at serving time. Each partner has its own consumer.

5. **Cleaning the internal shelf — OPEN.** Old runs (~29 GB each at reference
   parameters) accumulate in `production_forecasts` with no deletion mechanism.
   The maintainer has directed the shape of the fix — a configurable retention
   period with automatic deletion — but the owner and the period are unassigned
   (gap surfaced 2026-07-19; must close before the first full-S production run;
   see the Post-adoption record). **Shared.**

*Where is views-models?* It owns no stretch of the pipe itself — it is the
**driver, not a pipe segment** — but it owns four things the pipe depends on:
it defines the ensembles and launches the runs that enter the wire (using
pipeline-core's machinery); it owns the **delivery pointer** — the declaration of
*which source ships to which partner* (as of adoption, the `postprocessors/un_fao`
launch config naming the ensemble; their ADR-017 proposes making it first-class — see
§4.2a for how the pointer meets this contract); it owns the run-0 end-to-end
verification (views-models#230, §11.1–§11.2); and it hosts the platform's decision
record (this contract was ratified on views-models#149).

The same responsibilities in reference form — six rows: the five above, plus
views-models' **delivery pointer** as the first row, since that declaration
precedes the data flow. How to read the columns: **Role** = the job
itself, named so it exists for any partner delivery; **Scope** = whether one
instance of that job serves all partners (*shared*) or each partner gets its own
(*per partner*); **FAO instance** = what that job concretely is for the FAO
delivery as of 2026-07-19; **Owner** = who must act (build, fix, or decide) when
that job changes — a repo's code, a maintained configuration, or (if OPEN) nobody
yet. The FAO-instance column uses PFE (the pipeline's forecast-producing ensemble
component) and the row names use the two hops — Hop A and Hop B, the storage transfers defined in the Vocabulary and drawn in §1.

| Role                            | Scope       | FAO instance                     | Owner                    |
|---------------------------------|-------------|----------------------------------|--------------------------|
| Delivery pointer (source → partner) | per partner | `postprocessors/un_fao` config (names the ensemble) | views-models (ADR-017) |
| Hop A producer                  | shared      | PFE → internal store             | views-pipeline-core #269 |
| Anti-corruption layer + §6 gate | per partner | internal store → `unfao_bucket`  | **views-postprocessing** |
| Delivery definition (§4.2a)     | per partner | FAO delivery config              | **views-postprocessing config** |
| Hop B consumer                  | per partner | `unfao_bucket` → serving         | views-faoapi #100        |
| Internal-store retention (§3.5) | shared      | `production_forecasts`           | **OPEN**                 |

---

## §1 Topology — two hops, one interior representation

```
PFE  (producer, in views-pipeline-core)
  writes per target: y_pred.npy (N,S) float32
  + identifiers.npz, on local disk
      |
      |  HOP A — Track A archive (zip),
      |  one per (run, target, month);
      |  per-(run, target) manifest
      |  uploaded LAST = commit marker
      v
Appwrite `production_forecasts`
  (internal store, shared by all partners)
      |
      v
views-postprocessing  (anti-corruption layer)
  interior: per-target 2-D PredictionFrame
  via from_arrays; owns the §6 no-collapse
  gate; awaits ALL targets (§4.2a)
      |
      |  HOP B — one views_frames.io.arrow
      |  file per (target, month) + geo
      |  sidecar + ONE run manifest spanning
      |  all targets, LAST = commit marker
      v
Appwrite `unfao_bucket`  (FAO-facing store)
      |
      v
views-faoapi  (serves FAO; MAP/HDI
  computed at the edge)
```

In words: the pipeline zips exactly the files it already writes to local disk and
uploads them to the **shared internal store** — `production_forecasts`, the shared
shelf every partner delivery draws from (§0.3 role 1) — that upload is Hop A.
views-postprocessing downloads and
verifies them, holds them internally as views-frames `PredictionFrame` objects (the
platform's native N×S array type), runs the no-collapse gate (§6), and re-emits them
in the views-frames arrow format to the FAO-facing store (Hop B). views-faoapi reads
those and computes point summaries (MAP) and uncertainty intervals (HDI) at serving
time — the *edge* — so samples are never collapsed in transit.

To be explicit about what is stored where: **both stores hold full samples; MAP/HDI
are never stored anywhere.** faoapi's only source is `unfao_bucket` — it never
touches the internal store — and it computes summaries per request, when FAO's
systems call its API (FAO fetches; nothing is pushed to them). The collapse to a
summary is thus a *presentation* choice made at the last possible moment: summary
types and interval widths can change tomorrow without re-shipping any data.

views-postprocessing is the anti-corruption layer: neither end format leaks past it.
Hop A deliberately wraps what PFE already writes — zero new serialization code in
pipeline-core, compatible with their #207 on-disk-format deferral and orthogonal to
their #139 Track-B retirement (as characterized at adoption). Hop B is the format views-postprocessing#91 and
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

Field by field — what each key is, and who sets it:

| Key | Type | Meaning / format |
|---|---|---|
| `contract_version` | string | `"MAJOR.MINOR"` of this contract — rule 2 below |
| `frame_type` | string | `"prediction"` is the only value on this wire (the historical artifact is out of scope, §4.1); new frame types would be MINOR additions |
| `representation` | string | `"samples"` is the only value defined — even an S=1 run declares `"samples"` |
| `sample_count` | int ≥ 1 | S, the number of samples per cell — a parameter, rule 3 below |
| `dtype` | string | numpy dtype name of the payload values; `"float32"` on this wire (§3.1); changing it is governed by §2.3 |
| `spatial_level` | string | `"pgm"` for this delivery; other levels inherit later (§8) |
| `target` | string | a name from the pinned §7a wire vocabulary — never an internal model name |
| `time_id` | int | the VIEWS month-id; per-month sharding makes this **the shard's month** — every identifier row's time value equals it |
| `run_id` | string | minted once by the producer at run start, unique per production run platform-wide; every artifact of that run, on both hops, carries the same value |
| `generated_at` | string | ISO-8601 UTC instant (e.g. `"2026-07-15T00:00:00Z"`); injectable in test mode (§10.2) |
| `id_semantics` | object (closed) | what the identifier arrays mean — §2.2 |
| `provenance` | object (closed) | exactly the three keys shown — §2.2 |
| `sharding` | object (closed) | `scheme`: only `"per_month"` is defined in v1; `index`: zero-based position of this shard among the (run, target)'s months in ascending month order; `count`: total shards for that (run, target) |

Two notes that bind the table:

- **Key order.** Writers emit keys in exactly the order shown above (readers MUST
  NOT depend on it): the order exists only so that §10's golden fixture can pin the
  header byte-for-byte — two independent hand-written header writers can only
  byte-match if order is fixed.
- **The executable spec.** The §10 golden fixture pins this header byte-for-byte;
  where prose and fixture bytes could ever be read differently, **the fixture
  governs** (and changing it is changing the contract, §10).

**§2.1 Clauses.** Three rules govern the header:

1. **Unknown fields are skipped; known fields are sacred.** A reader that meets a
   header key it does not recognize MUST ignore it — that is what lets fields be
   added later without breaking anyone. The keys defined here, however, keep their
   meaning forever: the header is open to *additions*, closed to
   *reinterpretation*. **This openness applies to top-level keys only** *(clarified
   2026-07-19, MINOR)*: the `id_semantics`, `provenance`, and `sharding`
   sub-objects are **closed** — adding a key inside one of them is a contract
   amendment, not a free addition.
2. **Version numbers work like software versions.** A **MINOR** bump of
   `contract_version` (1.1 → 1.2) marks a clarifying or purely additive change — a
   reader built for 1.1 still accepts a 1.2 artifact. A **MAJOR** bump (1.x → 2.0)
   marks a breaking change — consumers MUST reject the artifact rather than guess.
3. **The sample count and number format are settings on the label, not part of the
   format.** `sample_count` and `dtype` are **parameters, not schema**: a run with
   S=8 is exactly as contract-conformant as one with S=1024, and changing them
   renegotiates nothing. The only refusal rule is §6's floor — reject when
   `sample_count < S_min`.

**§2.2 Identity and provenance.** `id_semantics` states explicitly what the
identifier arrays mean (`time` is the VIEWS month-id; `unit` is the `priogrid_id`) —
this platform has already paid once for leaving id vocabulary implicit (the gid/id
epic: a past platform-wide cleanup needed just to disambiguate what its integer
identifier columns meant). `provenance` is exactly the three keys shown (strings/bool). **Caveat:**
`pipeline_core_version` is self-reported and will be unreliable until pipeline-core's
release train (their #261) cuts real releases (status at adoption, 2026-07-15: none
yet) — consumers must not treat it as authoritative before then. The lift of this
caveat is tracked as a reminder in pipeline-core: their issue #279 (filed
2026-07-19) fires when the first real release ships.

**§2.3 Governance hook.** Changing `sample_count` (wire thinning) or `dtype` on the
**FAO delivery** changes the published HDI/MAP numbers, and is therefore a
**re-baseline event**: it requires sign-off under views-faoapi **ADR-023
("Governance Gate for Re-baselining Published Forecasts", Accepted 2026-06-24)**
before production use. The wire stays flexible; the product stays governed.

---

## §3 Hop A: the Track A archive (views-pipeline-core, #269)

**§3.1 Shard.** One stored object per **(run, target, month)**: a zip containing
exactly what PFE already writes — `y_pred.npy` of shape `(N, S)` float32, plus
`identifiers.npz` (a zip of exactly two members, `time.npy` and `unit.npy`: int64
arrays row-aligned with `y_pred`) — plus `metadata.json` (the §2 header). Its store document carries
`type="sampled_forecast_shard"`, `category="forecast"`, `loa`,
`targets=[<target>]`, and `name` per §3.3. Size ≈ 265 MB per shard per target at
S=1024 over 64,742 cells.

**§3.2 Manifest — one per (run, target).** A JSON document — the target's packing
list. Its fields, exactly as the §10 fixture pins them:

| Key | Type | Meaning |
|---|---|---|
| `contract_version` | string | per §2 |
| `run_id`, `target` | string | which (run, target) this manifest commits |
| `shards` | array | one entry per month shard: `name` (the §3.3 locator string) and `sha256` (SHA-256 hex digest of the complete shard zip bytes — the hash views-postprocessing verifies on read) |
| `expected_months` | array of int | every month-id this target's leg must cover, ascending |
| `expected_cell_count` | int | the number of cells in **each shard** — one month's N. Uniform across the run's months by construction: a ragged run (months with differing cell counts) is malformed and MUST NOT be published. *(Scope ruling 2026-07-19 — both shipped implementations verified convergent on this reading.)* |
| `sidecar_sha256` | null | always null at Hop A (Erratum E1 below) |

Shards are identified by `name` plus content hash — **not** by store file-id
*(corrected 2026-07-19: an earlier draft promised store file-id references; the
canonical bytes never carried them — names are locators per §3.3, hashes are
identity)*. The manifest's own store document carries the same field set as the
shard's: `type="sampled_forecast_manifest"`, `category="forecast"`, `loa`,
`targets=[<target>]`, `name` per §3.3 (verified against the shipped publisher).

The manifest is **uploaded last and is the commit marker for that target's leg**:
consumers MUST ignore shards no manifest lists, so a producer that dies mid-run
leaves nothing visible. *(Erratum E1, 2026-07-15: the sidecar hash is NOT a Hop-A manifest field —
the sidecar is produced downstream by views-postprocessing, so the producer has
nothing to hash; `sidecar_sha256` at Hop A is absent/null. The sidecar hash lives in
the Hop-B run manifest only, per §5.2.)* Hop A deliberately keeps **per-target**
manifests (unlike Hop B's one-per-run, §4.2): the producer's targets complete
independently, and the Hop-A consumer — views-postprocessing, unlike faoapi — can
trivially wait for all targets before acting (§4.2a). **Hash verification:**
views-postprocessing verifies each shard's content hash against this manifest on
read; it owns the integrity invariants.

**§3.3 Naming.** Shard name: `{run_id}__{target}__m{time_id:06d}.tap.zip` (the
`tap` extension stands for **Track A Package**); manifest
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
the no-collapse *policy* lives only at §6.

**§3.5 Retention.** At the reference parameters (3 targets × 36 months × ~265 MB —
a figure that *grows* with new targets and wider coverage) a full-S run ≈ 28.6 GB
lands in `production_forecasts` and accumulates with every run. Verified at adoption
(2026-07-15): no retention/TTL/quota mechanism existed anywhere in the store code.
**A retention owner and policy (quota, TTL, or cleanup cadence) must be named at
sign-off, before the first full-S production run.** *(Gap surfaced 2026-07-19: no
owner was in fact named at sign-off — this duty is OPEN; see the Post-adoption
record.)*

---

## §4 Hop B: arrow delivery (views-postprocessing → `unfao_bucket` → views-faoapi)

**§4.1 Shard.** One `views_frames.io.arrow` file per **(target, month)**, with the
§2 header embedded. The **historical actuals+geography artifact is out of scope and
unchanged** (pandas parquet; it takes neither hop — noted here only to prevent
confusion, §8).

**§4.1b Naming (Hop B).** Shard file name:
`{run_id}__{target}__m{time_id:06d}.arrow.parquet`; run manifest:
`{run_id}__manifest.json`; sidecar: `{run_id}__sidecar.parquet`. The templates live
as shared constants with golden-string tests in this repo's #91 sink leg, mirroring
§3.3 — file names are locators only, never identity. **Two different "names" exist
at this hop** *(clarified 2026-07-19)*: the store-*document* `name` field (§4.1a
below — always the pinned consumer name, it is what routes faoapi's queries) and
the artifact's *file* name (these templates). They are unrelated and never
interchange.

**§4.1a Store-document schema (pinned).** faoapi's metadata schema makes all five
fields **required at upload**, and its production query layer **unconditionally adds
a `name` filter** to every search (its model path always carries a model name;
verified 2026-07-13/14, evidence in Appendix B) — so
a document uploaded under the wrong `name` is *invisible to the consumer*, not
merely degraded. Therefore every Hop-B contract document uploads with:

| Field | Value (Hop-B documents) |
|---|---|
| `category` | `"forecast"` |
| `type` | `"sampled_forecast_shard"` \| `"sampled_forecast_manifest"` \| `"sampled_forecast_sidecar"` |
| `name` | **the literal faoapi model name — `un_fao` today.** Config-owned by views-faoapi; changing it is a contract amendment, not a deploy detail. |
| `loa` | `"pgm"` |
| `targets` | shard: `[<target>]`; manifest/sidecar: the run's full target list |

*(Corrected 2026-07-19 — a phantom obligation removed.)* Earlier text required
upload metadata to carry "approval fields" for faoapi's C-71 quarantine/approval
filtering. Ground-truthing against faoapi's code shows C-71 is **consumer-side and
file-id-keyed**: an operator-set quarantine blocklist
(`APPWRITE_UNFAO_QUARANTINED_FILE_IDS`) and approval allowlist
(`APPWRITE_UNFAO_APPROVED_FILE_IDS`) — comma-separated bucket file-ids read from
faoapi's environment (`prediction.py:17-38`). **No upload-metadata approval fields
exist, and the uploader has no C-71 duty.** The mechanism composes with §4.4:
operators quarantine or approve the run manifest's file-id.

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
emits **a single manifest per run** to `unfao_bucket` — the run's packing list.
Its fields, exactly as the §10 fixture pins them:

| Key | Type | Meaning |
|---|---|---|
| `contract_version` | string | per §2 |
| `run_id` | string | the run this manifest commits |
| `targets` | array of string | the run's resolved target list (§4.2a) |
| `shards` | array | one entry per (target, month) shard: `name` (file name per §4.1b), `target`, `time_id`, and `sha256` (SHA-256 hex digest of the complete file bytes) |
| `expected_months` | array of int | every month-id each target must cover, ascending |
| `expected_cell_count` | int | per-shard N — each month's cell count; §3.2's scope ruling applies verbatim (uniform across the run, ragged run malformed) |
| `sidecar` | object | `name` and `sha256` of the §5 sidecar file — the Erratum-E1 home of the sidecar hash |

`type="sampled_forecast_manifest"`, **uploaded last — after every target's shards
and the sidecar** *(ordering clarified 2026-07-19: the sidecar is inside the
commit — the manifest may only be uploaded once everything it references, sidecar
included, is present)* — **as the run's single commit marker.** This closes the torn-run hole across the
*target* axis: with per-target manifests, a consumer refreshing between targets
could assemble a run with one target present and the others missing; with one run
manifest that state is structurally invisible.

**§4.2a Run completeness.** The **expected target set is views-postprocessing
configuration** (as the anti-corruption layer it owns the FAO product definition).
Which forecasts a partner receives is decided the same way: the delivery is
*launched with* a declared product (which ensemble, which targets, which level),
takes the newest fully-manifested run on the shared shelf matching that
declaration, and verifies the fetched artifacts' identity against it — a mismatch
fails loud, never falls back. Future partners (e.g. UN CRAFD, UN OCHA) each get
their own such declaration; nothing is routed or inferred. *Where the launch-side
declaration lives is views-models' domain: as of adoption it is the
`postprocessors/un_fao` launch config's `"ensemble"` field; views-models ADR-017 (Proposed,
2026-07-02) would make it a first-class delivery declaration — source → consumer —
with "deployed" derived from it. This contract requires only that such a
declaration exists and is verified at fetch; the split is deliberate: views-models
owns the pointer (changes with modeling strategy), this repo owns the partner
product definition (changes with the partner relationship). The ensemble the
pointer names is a snapshot, not a constant: `rusty_bucket` as of 2026-07-19.*
views-postprocessing translates a run only when **all configured targets' Hop-A
manifests** are present, and emits the §4.2 run manifest only after all targets'
Hop-B shards are uploaded. The run manifest carries the resolved target list, so
faoapi needs no target-set knowledge of its own. *(Home of this configuration —
recommended 2026-07-19 on the maintainer's Common-Closure question, to be settled
at #91 implementation: a small declared config file committed in this repo beside
the delivery code. Rationale: the list changes only when the delivery product
changes — this repo's own reason to change — at a slow, decision-driven cadence
that a reviewed, git-historied, explicitly declared file matches; never runtime
state, never inferred from arrivals, never owned by the launcher.)*

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
touching the run's full shard set (100+ objects at current parameters). Operators
act on manifests, never on shards. (A
runbook line to land with faoapi#100.)

**§4.5 Ingest asserts (consumer-side mechanism guards, defense-in-depth).** At
ingest the consumer asserts:

- **(a)** loaded S equals the manifest/header `sample_count`;
- **(b) ordering** — the arrow file's `sample` column equals
  `np.tile(np.arange(S, dtype=np.int32), N)` *before* that column is discarded.
  Rationale: the arrow writer emits that exact column, but the loader never reads it
  — it reconstructs the (N, S) array purely by position — so a reordered or
  truncated table would yield plausible floats in the wrong sample slots, invisible
  downstream (code locations: Appendix B). Operationally: since `arrow.load`
  discards the column, this check reads the raw parquet table separately (e.g.
  `pyarrow.parquet.read_table`) before trusting the load;
- **(c) hashes** — faoapi SHOULD verify shard content hashes against the run
  manifest at ingest (cheap; once per cache fill).

These are mechanism guards; the §6 policy is not duplicated here.

**§4.6 Capacity and the intended consumer model.** At the reference parameters a
fully assembled run is ≈ 28.6 GB in memory — larger than the current serving host's
RAM (as of adoption). **Before
a production S is chosen, the capacity inequality
`assembled-run size × safety factor ≤ consumer serving RAM` must be owned** —
either by choosing wire parameters that satisfy it, or (the intended direction) by
**lazy per-month consumption**: the per-(target, month) sharding exists precisely so
the consumer can load shards on demand with a month-keyed cache, which dissolves the
memory wall without memory-mapping. Documented caveat: `arrow.load` reads a whole
file into RAM (no mmap as of adoption; ~1.6 GB transient per full-S shard); per-month
sharding is the mitigation, and mmap/partitioned arrow remains future views-frames
work, not a contract dependency.

---

## §5 GAUL geography sidecar

(*GAUL* is FAO's Global Administrative Unit Layers — the standard country/admin
region coding the delivery labels cells with.)

**§5.1 Schema.** One sidecar per run — one row per covered cell; the count is
declared data and must equal the forecast's cell set (§5.2), ~64,742 rows at the
global reference — `type="sampled_forecast_sidecar"` (store-document fields per
§4.1a). It is a **10-column parquet file**: `priogrid_id` (int64) is itself the
**first column** — a real column, not a file index — followed by exactly these 9:
`pg_xcoord` (float64), `pg_ycoord` (float64), `country_iso_a3` (string),
`admin1_gaul1_code`, `admin1_gaul1_name`, `admin1_gaul0_code`, `admin1_gaul0_name`,
`admin2_gaul2_code`, `admin2_gaul2_name` — the `*_name` and `country_iso_a3` columns
as **plain strings** (not categorical; verified the consumer applies no categorical
coercion), the `*_code` columns **always float64** *(dtype ruling 2026-07-19,
MINOR — matches the canonical fixture bytes; the earlier "int64 when complete"
wording made the schema depend on the data, so identical content could ship two
ways; one stable schema wins)*. **Column order as listed (`priogrid_id` first) and
rows ascending by `priogrid_id` are normative — the §10 fixture pins both.**
**Rows with missing GAUL codes are PRESERVED, never pre-dropped** — missing
geography is null (None) in the string columns and NaN in the float columns — and
the consumer drops such rows at aggregation under its own legacy-parity rule (its
C-146 machinery — faoapi's register rule that aggregation drops missing-geography
cells with legacy parity; verified). Pre-dropping here would silently mislabel
geography. **Source:** the sidecar is built from this repo's ADR-011 GAUL lookup
(`views_postprocessing/data/gaul_lookup.parquet`, area-majority cell→region mapping
sourced from views-datafactory); the #91 sink leg attaches it per run.

**§5.2 Consistency.** The sidecar's cell-id set must equal the forecast's cell-id
set (views-postprocessing's existing coverage/identity invariants, to be extended
to the sidecar in the #91 leg — not yet built as of 2026-07-19). The sidecar hash is pinned in **the Hop-B run manifest
(§4.2)** *(Erratum E1: formerly "both manifests" — impossible at Hop A, where the
sidecar does not yet exist)*. Delivered once per run, not per shard — the whole
point is not replicating static strings ×S×months.

---

## §6 The no-collapse boundary — owner: **views-postprocessing** `delivery/draws.py`

The single place where the platform *decides* a forecast still carries genuine
uncertainty. A representation-free invariant module,
`views_postprocessing/delivery/draws.py` (sibling of the existing
coverage/identity/observed-range/provenance invariants), raises
`DrawsCollapseError` unless all of:

1. values are 2-D `(N, S)`;
2. payload S equals the header's `sample_count`;
3. `sample_count >= S_min` (config: 2 for the walking skeleton; "region-pinned" for
   production — *the precise production pinning mechanism is ambiguous as written;
   flagged for maintainer definition 2026-07-19, see the Post-adoption record*);
4. **globally**, at least one row has more than one distinct sample value.
   *Explicit non-rule: a single row with zero variance is legal — zero-conflict
   cells dominate PGM, so many rows are legitimately all-zeros; the degeneracy check
   is global-across-rows, never per-row.*

**NaN note** *(added 2026-07-19; the module always documented it — the contract now
does too)*: a NaN draw compares unequal to everything, so a NaN-carrying row counts
as **non-degenerate** here — deliberately. Garbage/null screening is the delivery
null gates' job, not this invariant's; this gate detects *collapse*, nothing else.

It runs before every consumer-facing forecast upload (in this contract's scope: the
FAO delivery) — the module is merged and tested (PR #98), and the wiring into the
upload path lands with the #91 sink leg (not yet built as of 2026-07-19). This is
the single **policy** gate;
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
  cited by the golden fixture. **Adding a new target (Amendment A1, maintainer,
  2026-07-19 — MINOR per §2.1):** a new target joins the wire by (1) the maintainer
  deciding its canonical wire name, (2) adding that name to the shared mapping
  constant, and (3) adding it to views-postprocessing's expected-target-set
  configuration (§4.2a). No other contract change is required — the target list
  travels as data in manifests and headers. The current three-name list is the
  *current vocabulary*, not a closed set.
- **(b)** The `APPWRITE_PROD_FORECASTS_*` environment fix (views-models#230-A) —
  the documented `forecasts_metadata` collection does not exist in live Appwrite.
  *Status re-verified 2026-07-19 by the views-models seat: the four
  `APPWRITE_PROD_FORECASTS_{BUCKET,COLLECTION}_{ID,NAME}` values are still absent
  from the runtime environment, and the correct values are now known (database
  `file_metadata`, collection `production_forecasts`). A views-models duty.*
- **(c) ADR numbering:** views-faoapi's consumer-side ADR is **ADR-031** (verified
  2026-07-06: 000–030 taken at that date). faoapi#100 retitled off "ADR-046" —
  **done** (verified 2026-07-19: its title now cites ADR-013).

---

## §8 Non-goals (with recorded deferred intents)

- **cm level and the second store** (views-postprocessing#97): inherited later via
  the header's `spatial_level`; reconciliation already runs upstream in PFE,
  samples-aware.
- **Historical artifact format**: unchanged pandas parquet.
- **mmap / partitioned arrow**: future views-frames work — the hardening issue for
  `io.arrow` (ordering validation on load, plus mmap) is **filed as
  views-frames#199** (2026-07-19); not a contract dependency.
- **Concrete S_wire / dtype values**: parameters (§2.1) with a governance gate
  (§2.3).
- **Deferred intent (recorded, not adopted):** consolidate the §2 header vocabulary
  into `views_frames.FrameMetadata` via a MINOR extension once the fixture-pinned
  header has stabilized; extract a shared sharded-run reader into views-frames only
  after both hand-rolled consumers exist (WET-before-DRY).
- **Deferred intents (maintainer direction, 2026-07-19 — sequenced strictly after
  Run 0 proves the wire as-is AND the §3.5 retention owner exists):**
  1. **Rename this repo** to a delivery-screaming name (e.g. `views-delivery`):
     the repo is already purely delivery code (reconciliation retired to
     `views_frames_reconcile`; #62 closed), so the name is the only mismatch.
     GitHub redirects soften the repo rename; the Python package rename
     (`views_postprocessing` in cross-repo imports/launchers) is the real churn
     and may trail the repo rename.
  2. **Move the internal `production_forecasts` store off Appwrite** to
     self-managed storage (e.g. Hetzner object storage): no external consumer
     reads it — partners always go through partner-facing stores. §3's payload
     format and manifest-last semantics are transport-agnostic; only the
     store-document addressing (§3.1/§3.2 metadata fields) needs a bounded
     amendment. Gated on infrastructure ownership existing (the same gap as
     retention).
  3. **Co-locate the delivery compute with the internal store** so Hop A is
     physically cheap (no ~29 GB upload-download round-trip) — while **keeping
     the logical hop**: complete-or-invisible commit marker, hash verification,
     producer/delivery schedule independence, multi-partner fan-out. Fusing
     producer and delivery into one machine reading each other's disks is
     explicitly rejected (it would rebuild the coupling this contract dissolved).

---

## §9 Corrections to prior claims

views-models#143 claimed the samples work needed "no new aggregation mode **or
pipeline-core change**". That claim is **falsified for the publish leg**: at the
time of writing, no code path existed by which any sampled forecast reached the
prediction store — the pipeline's store-upload switch was accepted and logged but
never acted on, the Arrow upload path raised `NotImplementedError`, and the parquet
fallback was disabled for these models. pipeline-core#269 is the fix *(since
shipped — see the Post-adoption record, 2026-07-15)*. The specific
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

**§10.1 Distribution.** The fixture bytes live in **this repo** at
`tests/fixtures/wire_contract/`. Integrity mechanism *(spelled out 2026-07-19)*:
`SHA256SUMS` in that directory lists each fixture file's SHA-256; the **root hash**
— the SHA-256 of `SHA256SUMS` itself — is the single cross-repo pin, recorded in
the fixture README (and this document's Post-adoption record). The other two repos
**vendor a copy** (commit their own copy of the files) and carry a **pinned
root-hash equality test**; a mismatch fails loud with "re-vendor the fixture from
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
plumbing; only the *scale* proof waits on views-models#143/#146 tuning. (Distinct
from the §10 fixture's S=4 — two different vehicles: the fixture pins canonical
bytes for test suites; the skeleton proves the live path end to end.)

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

- **Hop B (deployed state as verified 2026-07-13; the guard has since merged and
  awaits production deploy — C-161, Post-adoption record):** deployed faoapi selects
  the newest `category="forecast"` document with
  no `type` awareness — and since it name-filters on the pinned consumer name, the
  contract wave's `name="un_fao"` documents become **visible to the legacy
  selector** precisely where the old ensemble-named forecasts were not. Without the
  guard, the first Hop-B upload would be grabbed as "the forecast" by deployed code.
  The constraint is *more* acute under the contract, not less.
- **Hop A (verified 2026-07-13; the guard has since merged — Post-adoption
  record):** the legacy views-postprocessing reader has the same selection shape
  (newest `category="forecast"`, no `type` filter). Its existing identity assertion
  makes the failure **loud, not silent** — an outage, not corruption — but the
  constraint stands: the type-aware source adapter, or a one-line `type` filter in
  the legacy reader, lands **before pipeline-core#269's first live upload.**

**Minimal-guard note (verified, both hops):** every legacy document in both stores
carries the legacy `type` vocabulary — Hop-B legacy uploads stamp `type="model"`;
Hop-A legacy uploads stamp `type` ∈ {`"model"`, `"ensemble"`} — **fully disjoint
from the contract's `sampled_forecast_*` values**. So the minimal legacy guard is
literally one line at each deployed selector: pin the legacy type(s) into its
filters. It needs zero knowledge of the new types and could ship immediately,
independent of the full consumer legs — **and did: both guards merged 2026-07-15**
(Post-adoption record; the Hop-B guard's *production* deploy rides C-161).
(Code locations: Appendix B.)

Skeleton ordering therefore is: **consumer guards → producer legs → run 0.**

**Upload interlock (design commitment, 2026-07-19 — proceed-safety audit):** the
C-161 constraint above is prose until code enforces it, so the #91 sink adapter
**ships upload-disabled by default** — sending bytes to `unfao_bucket` requires an
explicit, declared enable (config/flag, never a default), and its first enablement
is gated on the C-161 closure notice from the faoapi seat. Tests and development
runs can therefore never touch the live bucket by accident.

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
- **2026-07-19 — maintainer read-through: four clarifications + Amendment A1
  (MINOR, additive; `contract_version` stays 1.5 — no wire bytes change).**
  Prompted by the maintainer's own reading of the rewritten text: (1) Context now
  states FAO is the *first* consumer and scoping case, not the only one (§8 already
  said so); (2) the Vocabulary now states the two hops describe the forecast path
  only — the historical artifact goes directly to `unfao_bucket` and is out of
  scope; (3) the Vocabulary no longer presents the target count, month horizon, or
  cell count as constants — target set is configuration (§4.2a), months and cell
  counts are declared data, ~64,742 is the global reference for capacity math only;
  (4) "shard" clarified as a format-agnostic term. **Amendment A1 (§7a)** makes
  explicit what adding a new target requires: maintainer names it, the shared
  mapping constant and the §4.2a configuration gain one entry each — nothing else
  changes. Producer and consumer seats to be notified with a one-line notice.
- **2026-07-19 — adversarial fresh-eyes sweep (21 findings; prose and dating fixes;
  TWO OPEN maintainer items surfaced).** After the maintainer's own read caught
  FAO-centrality slips, an independent reviewer swept the full text for
  instance-facts presented as intrinsic, internal contradictions, and undated
  snapshots of other repos' state. All findings fixed in place, except two surfaced
  as genuinely open:
  **(1) Retention owner (§0.3/§3.5): the contract required an owner to be named at
  sign-off; none ever was.** The ownership-table cell silently read as resolved.
  Now marked OPEN; must close before the first full-S production run.
  **(2) §6 "region-pinned" production S_min: the term was never defined** —
  carried verbatim from the draft; the maintainer will define the production
  pinning mechanism.
  Dominant fixed residue: the capacity arithmetic (28.6 GB, 9.5 GB, 100+ shards,
  ×36, the 64,742-row sidecar) still presented current parameters as constants
  after the Vocabulary had disclaimed them; all figures are now labelled reference
  parameters. Undated present-tense claims about other repos' deployed state
  (§2.2, §3.5, §4.1a, §4.6, §7c, §11.4) are now dated.
- **2026-07-19 — §10.1's mechanism has already earned its keep.** The fixture's
  three binary artifacts were once silently excluded by a blanket
  `*.zip`/`*.parquet` gitignore rule (they existed on one machine only); the
  repository's own conformance tests — which can only pass with the true bytes
  present — caught it, and PR #102 (`7f1914c`) committed the bytes with a scoped
  un-ignore guard. Strongest live evidence to date for the §10.1
  pinned-bytes-vendoring design. (Noted independently by the views-models seat
  review, 2026-07-19.)
- **2026-07-19 — external verification: views-models seat review.** A
  maintainer-commissioned review from the views-models seat verified this ADR's
  claims against all four repos with receipts (fixture root hash reproduced
  byte-for-byte; both guards confirmed merged; §4.1a invisibility mechanism
  confirmed in current code). Verdict: "substantially correct and unusually
  honest." Its material corrections landed on the *reviewing* seat's own
  world-model, not on this document — most notably: the FAO forecast product has
  **never been servable end-to-end** (files landed in storage, but never under a
  name the consumer's filter resolves — a stronger statement than "stalled").
  Review artifact:
  `views-models/reports/expert_reviews/2026-07-19_adr013_wire_contract_review_views_models_seat.md`.
- **2026-07-19 — §0 and §2 readability falsification audits (maintainer-commissioned);
  all findings fixed same day; one MINOR clarification adopted.** Two audits of the
  claims "§0 / §2 alone suffice and are unambiguous": both FALSIFIED (§0: 2 hard /
  5 soft — no execution status, commit-marker semantics absent, jargon unanchored;
  §2: 2 hard / 3 soft — field formats underdefined, key-order rule missing,
  open-vs-closed sub-object conflict). All fixed in place: §0.2a execution-status
  block; §2 field table + key-order and fixture-governs notes. **Clarification
  adopted (MINOR, §2.1; no wire bytes change): rule 1's openness applies to
  top-level keys only — the `id_semantics`/`provenance`/`sharding` sub-objects are
  closed.** Enforcement: `tests/test_falsify_adr013_s0.py` and `_s2.py` (audit
  stubs converted to permanent guards). Register: C-48, C-49.
- **2026-07-19 — §3 falsification audit (2 hard, 4 soft); all fixed same day; one
  scope ruling pinned; one prose error corrected.** Hard: §3.2 promised "store
  file-ids" the canonical manifest never carried (corrected in place — name +
  hash, no file-id); `expected_cell_count` scope was undecidable (per shard vs
  per-target total). **Ruling: per-shard N, uniform across the run's months —
  ragged runs are malformed.** Verified convergent before pinning: pipeline-core's
  shipped publisher (`sampled_forecast_publisher.py:261-268`, enforces equal
  cells per month) and this repo's `track_a_source` adapter had independently
  chosen the same reading. Also pinned: `identifiers.npz` members
  (`time.npy`/`unit.npy`, int64), SHA-256-of-whole-zip hash coverage, the
  manifest's store-document fields, `.tap` = Track A Package. Guards:
  `tests/test_falsify_adr013_s3.py`. Register: C-50.
- **2026-07-19 — §4 falsification audit (4 hard, 2 soft); all fixed same day; one
  phantom obligation removed; one protocol clarification adopted.** Hard: the
  run-manifest fields were unpinned and the prose understated the canonical bytes
  (now a field table, §4.2); Hop-B file-name templates were absent and the
  document-`name`-vs-file-name duality unexplained (now §4.1b); **the sidecar sat
  outside the commit-marker ordering — clarified (MINOR): the manifest uploads
  only after every shard AND the sidecar**, restoring §4.2's structurally-invisible
  guarantee for torn runs; **the "C-71 approval fields" upload obligation was
  ground-truthed as nonexistent and removed** — faoapi's C-71 is consumer-side,
  file-id-keyed env lists (`prediction.py:17-38`), composing with §4.4's
  manifest-as-control-point. Soft fixed: §3.2's cell-count ruling inherited
  explicitly; §4.5(b) mechanics note (separate raw-table read). §4.3 selection and
  §4.6 capacity math survived the audit. Guards: `tests/test_falsify_adr013_s4.py`.
  Register: C-51.
- **2026-07-19 — §5 falsification audit (2 hard, 4 soft); all fixed same day; one
  dtype ruling adopted.** Hard: the canonical sidecar is a **10-column** file with
  `priogrid_id` as the first column, while prose said "9 columns, keyed by" —
  corrected; the code-column dtype rule was data-dependent ("int64 when complete")
  — **ruling (MINOR): `*_code` columns are always float64**, one stable schema,
  matching the canonical bytes. Soft fixed: data source named (ADR-011
  `gaul_lookup.parquet`, datafactory area-majority); null-vs-NaN precision
  (strings carry null, floats NaN); C-146 glossed; §5.2's sidecar extension
  re-tensed as future #91 work; column and row order declared normative (§10 pins
  both). Guards: `tests/test_falsify_adr013_s5.py`. Register: C-52.
- **2026-07-19 — §6 falsification audit: CONTESTED (0 hard, 2 soft) — the series'
  first section with no hard finding.** The four rules, the redundancy note, and
  the per-row-zero-variance non-rule all match `delivery/draws.py` exactly (the
  code was the ground truth and held). Soft fixed: the NaN semantics the module
  always documented (NaN rows count as non-degenerate; null screening is the null
  gates' job) now stated in the contract; the gate's wiring status honestly dated
  (module merged/tested PR #98; upload-path wiring lands with #91). Guards:
  `tests/test_falsify_adr013_s6.py`. Register: C-53.
- **2026-07-19 — §1/§7/§8/§9 batched falsification audit: §1 and §9 SURVIVED (the
  series' first clean sections); §7 and §8 CONTESTED (3 soft total); all fixed
  same day.** §7(b) re-dated with the views-models seat's 2026-07-19 forensics
  (four env values still absent; correct values now known); §7(c) marked done
  (faoapi#100's title verified to cite ADR-013); §8's dangling mmap/ordering
  hardening intent is now **filed as views-frames#199**; §9 gains the
  since-shipped marker on #269. Guards: `tests/test_falsify_adr013_s789.py`.
  Register: C-54.
- **2026-07-19 — §10/§11 falsification audits: both CONTESTED (0 hard, 2 soft
  each); all fixed same day — SERIES COMPLETE.** §10.1 now defines its own
  integrity mechanism (path `tests/fixtures/wire_contract/`; per-file `SHA256SUMS`;
  root hash = SHA-256 of `SHA256SUMS`) instead of leaning on the README; §11.1
  distinguishes the two verification vehicles (fixture S=4 pins bytes; skeleton
  S=8 proves the live path); §11.4's minimal-guard note re-tensed — both guards
  merged 2026-07-15, Hop-B production deploy rides C-161. Guards:
  `tests/test_falsify_adr013_s10_11.py`. Register: C-55. **Every section of this
  ADR (§0–§11) has now been independently falsification-audited; every finding
  fixed same-day; 40 permanent guards enforce the fixes
  (`tests/test_falsify_adr013_*.py`).**
- **2026-07-20 — §10 fixture RE-BASELINED to the production toolchain (maintainer
  decision, Option A; a §10 contract-change event).** The fixture's Hop-B byte
  artifacts had been generated under pyarrow 23.0.1 (an unlocked dev
  environment); the delivery repo's actual locked toolchain is **pyarrow 16.1.0**
  and cannot be newer — `views-pipeline-core → viewser → views-storage` hard-pins
  `pyarrow <17`. The three Hop-B artifacts (arrow shard, sidecar, run manifest)
  + `SHA256SUMS` were regenerated under 16.1.0; **Track-A bytes are unchanged**
  (verified byte-identical — producer-side conformance unaffected). New root
  hash: `9658a6484cc9d975412e52624d52f328985f14cf58e3fc9fbdf3e64ab5a0564b`.
  pyarrow is now an explicit first-class pin in this repo's pyproject
  (`>=16.1.0,<17`). Vendors notified to re-vendor (their §10.1 pinned-hash tests
  catch it regardless — the mechanism's second live save). **Platform debt noted
  (maintainer: "fix this through the pipeline"): lifting the `<17` ceiling at its
  source is filed as pipeline-core#280; when it lifts, the fixture gets one
  planned re-baseline, coordinated, never a drive-by.**
- **2026-07-27 — run-0 attempt OOM-killed; both memory legs rebuilt (fix
  campaign complete same-day; expert-review-governed).** The first live delivery
  attempt was killed at 23.8 GB (31 GB host). Two stacked causes, both fixed:
  **(A) the delivery now STREAMS one target at a time** — `resolve_run` pins
  shard file_ids cheaply (race-free fetch-by-id), `TargetLease.load()`
  fetches → verifies → curates → coverage-checks per target, the sink releases
  each frame after its shards; measured on the real published run:
  **4.73 GB peak, 108 shards, 5 min, zero store calls** (interlock held).
  **(B) the historical path is pandas-free** (#126): actuals fetched as a
  `views_frames.FeatureFrame` (the frame path's FIRST production consumer —
  C-40's gate lifted), artifact built by `unfao/historical.py` via pyarrow —
  reader-level parity with a legacy characterization golden proven through
  faoapi's own reader semantics. Two ghosts found in the legacy artifact and
  deliberately exorcised (faoapi reader verified safe on both): junk `row`/`col`
  columns that would have served as bogus targets, and C-40's single-element
  list-in-cell values (now scalars; their reader normalizes both identically).
  Also closed: contract-mode `_save` had shipped no historical at all (S7 gap) —
  actuals now ride beside the wire behind the same interlock. Upstream during
  the same incident: the store's SDK JSON re-serialization surfaced
  (pipeline-core #310 / C-217) — manifests are never hash-verified, rule now
  pinned in docstrings. vpp PRs #127–#129; the third run-0 attempt is expected
  at ~5 GB total.
- **2026-07-24 — run-0 pre-flight: declared-region curation added at the
  anti-corruption layer.** The real run-0 payload carries the full model grid
  (64,818 cells) including exactly the 76 declared GAUL-uncovered exclusions
  (C-30); the producer is right not to know partner curation, so the delivery now
  applies `coverage.excluded_for(region)` — the explicit pinned frozenset, never
  inference — to the assembled frames before the gate (contract-mode read).
  Proven by a full dry run on the real run-0 data: curated 64,742 cells, gate
  passed at 128 draws, sidecar + manifest staged, zero store calls.
- **2026-07-20 — HOP-B SINK LEG SHIPPED (epic #105 complete; upload-disabled).**
  The contract's missing middle exists in fixture-proven code:
  `unfao/wire/` (naming, header, shard, sidecar, run_manifest, source_selection,
  sink) + `unfao/product.py` + `delivery/parity.py`, wired into the manager
  behind an explicit declared `wire_contract` launch key. Settled by shipping:
  **§4.2a's configuration home is `unfao/product.py`**; **§5.2's parity
  invariant is `delivery/parity.py`**; the §11.4 upload interlock is live in
  code (`product.UPLOAD_ENABLED=False`; the default configuration provably makes
  zero store calls — golden-tested). The e2e capstone proves the anti-corruption
  role end to end: fixture Track-A artifacts in → **byte-identical** fixture
  Hop-B artifacts out, §6 gate first, manifest uploaded last, every document
  under the pinned `un_fao` name (the F1 fix, in code). First live enablement
  remains gated on C-161 closure (faoapi #184 release). Stories: vpp #106–#113;
  PRs #115–#121.
- **2026-07-19 — retention direction given (maintainer): a configurable retention
  period with automatic deletion** (e.g. 12 or 36 months — the value to be decided
  with the owner). This settles the *shape* of the §3.5 policy; the owner
  assignment and the concrete period remain OPEN and are deliberately deferred —
  they must close before the first full-S production run, not before.

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

*Refresh note (2026-07-19, prompted by the views-models seat review):* this repo's
manager module has since moved to `unfao/managers/unfao.py` and its cited lines
shifted — the legacy selection + identity assertion now sit at `:121`/`:124`
(behind the PR #99 guard constant, `:33`), the historical upload name at `:314`,
the forecast upload name at `:325`. The findings themselves are unchanged.

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
