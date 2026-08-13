
# ADR README and Governance Map

This repository uses Architectural Decision Records (ADRs) to govern
structural, semantic, and operational behavior.

> **On the `Deciders` field (2026-08-10).** ADRs 000–015 originally recorded
> *"Project maintainers (PRIO MD&D Team)"*. That team no longer exists, and a decider
> field naming a body that cannot be asked anything is worse than useless to a future
> reader. All of them now name the sole decider, Simon Polichinel von der Maase.
> ADR-013's line keeps its original sign-off reference alongside the name.

ADRs are divided into two categories:

1. **Constitutional ADRs (000–009)**  
   Foundational architectural rules that apply across the system.

2. **Project-Specific ADRs (010+)**  
   Domain, implementation, or feature-level decisions.

---

## Constitutional ADRs

These ADRs define system philosophy and governance:

- **ADR-000** — Use of Architecture Decision Records  
  Establishes the ADR practice itself.

- **ADR-001** — Ontology of views-postprocessing  
  ⚠️ **Superseded by ADR-012** (the original shapefile/spatial-engine ontology; kept as the
  historical record).

- **ADR-002** — Topology and Dependency Rules  
  Defines structural dependency direction. **Amended 2026-06-27** with the cross-repo
  topology + current internal layering.

- **ADR-003** — Authority of Declarations Over Inference  
  Defines where semantic authority lives.

- **ADR-004** — Rules for Evolution and Stability (Deferred)

- **ADR-005** — Testing as Mandatory Critical Infrastructure  
  Defines red / beige / green test doctrine.

- **ADR-006** — Intent Contracts for Non-Trivial Classes  
  Requires declared class-level purpose.

- **ADR-007** — Silicon-Based Agents as Untrusted Contributors  
  Governs automated modification.

- **ADR-008** — Observability and Explicit Failure  
  Defines fail-loud + log requirements.

- **ADR-009** — Boundary Contracts and Configuration Validation  
  Defines explicit interface contracts and configuration validation.

These ADRs form the architectural constitution of the repository.

---

## Project-Specific ADRs

- **ADR-010** — Technical Risk Register  
  Formalizes the risk register as a first-class governance artifact.

- **ADR-011** — Replace Runtime Mapper with Precomputed Lookup Table  
  Replaces the 3,122-line runtime spatial mapper with a ~65K-row precomputed Parquet lookup table. Area-majority assignment confirmed as FAO contractual requirement.

- **ADR-012** — Revised Ontology (post-lookup migration)  
  Supersedes ADR-001. Restates the ontology to the current reality: a post-forecast delivery
  + input-integrity layer (delivery invariants, the representation seam, the lookup
  enrichment, the manager) — no runtime spatial engine.

- **ADR-013** — The Sampled-Forecast Wire Contract (v1.5)  
  The adopted cross-repo contract for sampled (N,S) forecasts: two hops (Track-A archive →
  prediction store; per-month arrow → unfao_bucket), manifests as commit markers, the GAUL
  sidecar, and the no-collapse boundary (delivery/draws.py). Supersedes the phantom
  "platform ADR-046". Adopted 2026-07-15 via views-models#149.

- **ADR-014** — Claims, and the Guards That Carry Them
  ADR-003 applied to the repository's own statements: a guarantee is attached to a check,
  a guard is mutation-proven or it is decoration, a false negative beats a false alarm, a
  deferral names a trigger and an owner, and a change that names a record disposes of that
  record in the same change. Arises from epic #181, which found seven places where this
  repo said one thing and did another.

- **ADR-015** — Why This Repository Imports Another Project's Appwrite Client
  The partner managers import `views_pipeline_core.modules.{appwrite,datastore}` and run
  another project's client under this repo's identity. Kept knowingly: a hand-written
  client here would be the platform's *third* copy, and the upstream seam to depend on
  instead does not exist yet. Records what bounds it (an importer allowlist, the
  `_ContractStorePort` DIP port, a framework-contract test), and the two-part condition —
  demand and supply — under which it is revisited. Arises from #146 and the þing-02
  ratification, which asked that the reasoning live here rather than in an issue.

- **ADR-016** — Which Sibling Repositories CI Downloads
  A handful of tests here verify claims this repo makes about *other* repos — chiefly that the
  coordinate-registry edition we pinned is the one that exists. They need the sibling on disk,
  so they skipped in CI and ran only on a laptop. Each sibling is now declared with its
  visibility, the date that was checked, and whether CI fetches it; a test fails when the
  workflow and the declaration disagree either way. Written after the workflow's comment
  asserted a repository was private for two days after it went public — which is the argument
  for a dated declaration rather than prose. The credential for the one genuinely private
  sibling is deferred with a named trigger.

- **[vpp_017](017_facts_across_a_private_boundary.md)** — Facts Shared With a Repository We Cannot Read
  The delivery label this repository writes is owned by the consuming API and mirrored here;
  if the two drift the upload succeeds, the file is stored, and the consumer's endpoint is
  empty with no error anywhere. Verifying the mirror used to mean reading the consumer's
  source, which is impossible in CI when that consumer is private — and private consumer APIs
  are a standing category, not a one-off. *(That reading is gone: #248 deleted both source
  reads on 2026-08-12 after two consumers broke them in a day by improving their own code.)* Decides that such a fact is declared in the public
  coordinate registry and each side verifies itself against it, so neither reads the other's
  source. No credential, for any number of private APIs. States plainly the half it does not
  cover: the consumer's own code against its own declaration.

### Why one of these carries a `vpp_` prefix

Three repositories each numbered an ADR **017**, and a bare "ADR-017" in a cross-repo
sentence resolves to the wrong document for a reader sitting in either of the other two:

| Repo | Prefix | ADR-017 |
|---|---|---|
| views-models | `vmo_` | *Forecast Sources, Composition, and Delivery* |
| **views-postprocessing** | **`vpp_`** | ***Facts shared with a repository we cannot read*** |
| views-crafdapi | `vcr_` | *Reference Data in Repository* |

**The prefix is additive.** The number does not change and no existing citation breaks.

**The usage rule** (adopted from views-models, which landed this first in its #393):
intra-repo prose may stay bare; write `vpp_017` wherever the sentence is read from, or
could be read from, another repository.

This is not yet a platform-wide convention — these three issues are its first application,
driven by an active collision rather than a sweep. views-postprocessing#264,
views-models#393 (landed), views-crafdapi#58.

*Audited when adopting: this repository has **no wrong referents** — no sentence here is
about the wrong decision, which is the defect the collision causes elsewhere. It has **one
bare foreign citation**: ADR-013 §7(d) writes "their ADR-017" of views-models', qualified
only by an antecedent two sentences earlier. Now `vmo_017`. Every other reference to
views-models' 017 already named it, and every bare `ADR-017` here means this document. The
prefix is for readers arriving from another repo.*


ADRs numbered 010 and above define:

- Domain-specific decisions
- Implementation details
- Infrastructure decisions
- Feature-level trade-offs

These must comply with the constitutional ADRs above.

---

## Governance Structure (Conceptual Map)

- **Ontology (001)** defines what exists.
- **Topology (002)** defines structural direction.
- **Authority (003)** defines who owns meaning.
- **Boundary Contracts (009)** define interaction rules.
- **Observability (008)** enforces failure semantics.
- **Testing (005)** verifies system integrity.
- **Intent Contracts (006)** bind class-level behavior.
- **Automation Governance (007)** constrains silicon-based agents.

Together, these define the invariant layer of the system.

---

## Recommended Adoption Order

Constitutional ADRs are designed to be adopted incrementally:

### Phase 1 — Foundation
- **ADR-000** (Use of ADRs) — establishes the practice
- **ADR-003** (Authority of Declarations) — the fail-loud invariant
- **ADR-008** (Observability and Explicit Failure) — failure handling

These three are load-bearing. Start here.

### Phase 2 — Structure
- **ADR-001** (Ontology) — define what exists
- **ADR-002** (Topology) — define dependency direction

### Phase 3 — Testing & Intent
- **ADR-005** (Testing Doctrine) — red/beige/green framework
- **ADR-006** (Intent Contracts) — class-level purpose declarations

### Phase 4 — Boundaries & Automation
- **ADR-007** (Silicon-Based Agents) — AI governance
- **ADR-009** (Boundary Contracts) — configuration validation

ADR-004 (Evolution & Stability) is intentionally deferred and should be
revisited when external consumers or reproducibility requirements emerge.
