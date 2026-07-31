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

| Category | Purpose | Authority | Stability |
|----------|---------|-----------|-----------|
| **Delivery Invariants** | Representation-free rules over primitives that a delivery must satisfy (coverage, no-collapse, gid parity, observed-range, provenance). Live in `views_postprocessing/delivery/`. *Forecast identity was one of these until 2026-07-31 — see the amendment below.* | Authoritative — they define what a valid delivery is | Stable — changes are governance decisions |
| **Representation Seam** | The single pandas-aware module (`unfao/extraction.py`) that turns the delivery's external representation into the primitives the invariants consume. | Derived — isolates the representation so invariants stay representation-free | Evolving — the one place a representation change (e.g. pandas → frames, C-40) lands |
| **Enrichment Asset + Engine** | The precomputed GAUL lookup (`data/gaul_lookup.parquet`) and the merge that joins it (`GaulLookupEnricher`). | Authoritative for geographic metadata | Stable — the lookup is rebuilt only when the producer (datafactory) releases new GAUL data |
| **Pipeline Manager** | The thin `UNFAOPostProcessorManager` — a concrete pipeline-core postprocessor (Template-Method subclass) that *orchestrates* read/transform/validate/save and **calls** the invariants (never inherits them). | Derived — implements delivery using the categories above | Evolving — changes as partner requirements change |
| **Producer Data-Facts** | Data-related facts sourced straight from the producer (datafactory) — e.g. `last_valid_month_id` — isolated in `unfao/source_metadata.py`. | Authoritative (the producer is the source of truth, D-07) | Evolving |
| **External Service Configurations** | Appwrite connection configs / env vars / bucket references. | Operational | Evolving |
| **Derived Outputs** | Enriched parquet files produced per run and delivered to the partner store. | Ephemeral | Ephemeral |

### Explicitly *not* in this repository's ontology

- **Spatial intersection / shapefiles / a runtime mapping engine** — removed (ADR-011/C-39);
  geography is precomputed upstream and consumed as a lookup.
- **Statistical post-processing** — draw-collapse (MAP/HDI) is downstream in views-faoapi
  (`views_frames_summarize`); reconciliation is in `views_frames_reconcile`. This repo
  *preserves* forecast values and delivers them; it does not transform them.

---

## Rationale

- **Screaming architecture:** the categories now match the package layout — `delivery/`
  (invariants), `unfao/extraction.py` (seam), `unfao/enrichment.py` + `data/` (enrichment),
  `unfao/managers/` (orchestration). A reader can infer responsibilities from the structure.
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

