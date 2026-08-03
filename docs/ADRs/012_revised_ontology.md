# ADR-012: Revised ontology of views-postprocessing (post-lookup migration)

**Status:** Accepted  
**Date:** 2026-06-27  
**Deciders:** Project maintainers (PRIO MD&D Team)  
**Supersedes:** [ADR-001](001_ontology_of_views_postprocessing.md)

---

## Context

[ADR-001](001_ontology_of_views_postprocessing.md) defined the repository's ontology around
a **runtime spatial-mapping engine** and **bundled shapefiles** as the authoritative,
stable core. That architecture no longer exists:

- [ADR-011](011_replace_runtime_mapper_with_precomputed_lookup.md) replaced the runtime
  geopandas mapper with a **precomputed GAUL lookup table** (`GaulLookupEnricher`).
- The mapper, shapefiles, and caching machinery were deleted (C-39 / PR #42).
- Input-integrity invariants and structured delivery were added (epic #51).

So ADR-001's core categories ("Geographic Data Assets", "Spatial Mapping Engine") describe
deleted code. This ADR restates the ontology to match what the repository **actually is**:
a **post-forecast delivery + input-integrity layer**, not a spatial-mapping library and not
a statistical post-processor. (For the wider narrative — role vs the sibling repos and the
internal seams — see [`docs/architecture/role_and_seams.md`](../architecture/role_and_seams.md).)

---

## Decision

The repository defines a **closed set of conceptual categories**. Anything that does not
clearly belong to one is out of scope and must be redesigned or rejected.

### Core ontological categories (current)

**The package layout IS the ontology** (restated 2026-08-01, epic #148). Three top-level
packages answer three different questions, and every category below names the one it lives in:

```
delivery/    what makes a delivery VALID   — representation-free invariants
contract/    how a delivery is BUILT       — partner-neutral machinery
unfao/       who a delivery is FOR         — one partner's product and manager
```

| Category | Purpose | Authority | Stability |
|----------|---------|-----------|-----------|
| **Delivery Invariants** | Representation-free rules over primitives that a delivery must satisfy: coverage, no-collapse, gid parity, observed-range, provenance. Live in `delivery/` — **nothing there imports pandas or views_frames**. *Forecast identity was one of these until 2026-07-31 — see the amendment below.* | Authoritative — they define what a valid delivery is | Stable — changes are governance decisions |
| **Representation Seam** | `contract/frame_extraction.py` — turns a `views_frames` frame into the primitives the invariants consume. **One seam.** Its pandas sibling `unfao/extraction.py` was deleted in #151 once the pandas delivery was retired; the two ran as deliberate WET siblings through the migration. | Derived — isolates the representation so invariants stay representation-free | Evolving |
| **Wire Mechanism** | `contract/wire/` — the ADR-013 contract: header, shard, sidecar, run manifest, sink, source selection. Partner-neutral: it takes its consumer name and collapse floor as **arguments** (#153). | Authoritative — the contract with the consumer | Stable — changes are contract amendments |
| **Enrichment Asset** | The precomputed GAUL lookup (`data/gaul_lookup.parquet`), its identity in `contract/gaul_lookup.py`, its schema in `contract/gaul_schema.py`, and the keyed gather that joins it (`contract/enrichment.py`, the build/verification path — numpy/pyarrow since #89; see register **C-75** on whether that class should survive at all). | Authoritative for geographic metadata | Stable — rebuilt only when the producer releases new GAUL data |
| **Artifact Builders** | `contract/historical.py` — turns a frame plus the lookup into the partner-facing artifact. | Derived | Evolving |
| **External Facts** | Facts read from systems this repo does not own: the producer's (`contract/source_metadata.py` — `last_valid_month_id`, D-07) and the store's (`contract/store_metadata.py`). | Authoritative (the owning system is the source of truth) | Evolving |
| **Launch Declarations** | `contract/launch_config.py` — the delivery mode the launcher must declare. Omitting a key is **refused by name**, never inferred (ADR-003, register C-63). | Authoritative | Stable |
| **Partner Product** | `unfao/product.py` (targets, consumer document name, collapse floor, upload interlock) and `unfao/appwrite_env.py` (the store coordinates). **This is what a clone replaces.** | Authoritative — one reason to change: the partner relationship | Evolving |
| **Pipeline Manager** | `unfao/managers/unfao.py` — a concrete pipeline-core postprocessor (Template-Method subclass) that *orchestrates* read/transform/validate/save and **calls** the invariants, never inherits them. **It is the only module in the repository that imports `views_pipeline_core`** — the coupling C-40 describes is one file wide. It is not yet *thin*: 406 lines, down from 636 (#149). | Derived | Evolving |
| **Derived Outputs** | Arrow shards, the GAUL sidecar, the run manifest and the historical parquet, produced per run and delivered to the partner store. | Ephemeral | Ephemeral |

**Two claims this ADR made until 2026-08-01, both now corrected rather than quietly dropped**
(register C-67). It called the manager *"the **thin** `UNFAOPostProcessorManager`"* when it was
636 lines holding two of everything, and it called `unfao/extraction.py` *"the **single**
pandas-aware module"* when pandas lived in three. Both drifted the same way: the ADR described
the intended end state of a migration that then stopped one step short. Both are now true —
pandas has **zero runtime importers** (#89 made `contract/enrichment.py`'s a type-only import under `if TYPE_CHECKING` — pandas is in that class's interface, not its implementation) — and the load-bearing ones are
**mechanically checked** by `tests/test_doc_accuracy.py`, so the next drift fails CI instead of
waiting for an audit.

### Explicitly *not* in this repository's ontology

- **Spatial intersection / shapefiles / a runtime mapping engine** — removed (ADR-011/C-39);
  geography is precomputed upstream and consumed as a lookup.
- **Statistical post-processing** — draw-collapse (MAP/HDI) is downstream in views-faoapi
  (`views_frames_summarize`); reconciliation is in `views_frames_reconcile`. This repo
  *preserves* forecast values and delivers them; it does not transform them.

---

## Rationale

- **Screaming architecture:** the categories match the package layout — `delivery/`
  (invariants), `contract/` (the machinery: `wire/`, the `frame_extraction.py` seam, the
  GAUL asset, artifact builders, external-fact readers), `unfao/` (the partner's product and
  its manager). A reader can infer responsibilities from the structure, and the one-way
  dependency `unfao/ → contract/ → delivery/` is enforced by test, not convention.
- **DIP / OCP:** primitives are the abstraction the invariants depend on; the representation
  seam is the single point of change for a representation migration (C-40), so the invariants
  are closed against it.
- **Honest scope:** naming the repo a delivery + integrity layer (not a postprocessor that
  does statistics) prevents the recurring confusion about where collapse/reconciliation live.

---

## Consequences

**Positive:** the ontology is verifiable against the code; onboarding docs (README, the
role-&-seams doc) can derive from it; the C-40 representation migration has a named seam.

**Negative:** when the representation migrates (pandas → frames) this ADR's "Representation
Seam" wording will need a light touch (the seam stays; its internals change).

---

## Notes

- Stability is a design constraint, not a preference (inherited from ADR-001 §Stability Rules).
- Dependency direction and cross-repo topology are governed by [ADR-002](002_topology_and_dependency_rules.md).
- Class-level contracts are governed by ADR-006 (see `docs/CICs/`).

---

## Amendment 2026-07-31 — forecast identity re-homed to the wire layer (#150, epic #148)

**`views_postprocessing/delivery/identity.py` is retired.** The "Delivery Invariants" row
above listed *forecast identity* among the authoritative rules; that module no longer
exists, and this amendment records where the rule went so a reader of the row is not
looking for deleted code.

**The rule is not weaker — it is enforced from better evidence.** The retired
`assert_forecast_identity` compared one selected store document's `name`/`loa` against the
configured ensemble. Since the ADR-013 contract path became the only path (#149), the same
guarantee is enforced in `unfao/wire/source_selection.py:73-81`: `TargetLease.load()`
checks **every shard header's declared `provenance.ensemble`** against the launched
ensemble, and refuses the run on a mismatch. Identity now comes from the artifact's own
declared content rather than from a metadata field on a single document, and it is checked
per shard rather than once per run.

**Why it was retired rather than kept.** Its only caller was the legacy reader deleted in
#149. An invariant module that nothing calls is documentation shaped like code — and
`delivery/` is precisely the package the coming clones (views-crafdapi,
views-productionapi) will copy wholesale, so an unenforced rule there would be inherited as
if it were live. Register **C-64** existed to force this decision rather than let the
deletion happen silently as a side effect of #149.

**Consequence for register C-25** ("forecast input selected by category-only filter —
newest file wins regardless of producer"): its recorded mitigation *was* this function, so
on paper the entry loses its guard. In fact its hazard is now structurally impossible — the
contract path selects by **run manifest**, a commit marker with hash-verified contents, so
"newest upload wins" is not a thing the selection can do. C-25 is closed as **superseded by
mechanism**, not as *mitigated*.

**Coverage:** `tests/test_wire_source_selection.py::test_wrong_declared_ensemble_refuses_at_load`.

