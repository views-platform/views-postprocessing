
# ADR README and Governance Map

This repository uses Architectural Decision Records (ADRs) to govern
structural, semantic, and operational behavior.

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
  enrichment, the thin manager) — no runtime spatial engine.

- **ADR-013** — The Sampled-Forecast Wire Contract (v1.5)  
  The adopted cross-repo contract for sampled (N,S) forecasts: two hops (Track-A archive →
  prediction store; per-month arrow → unfao_bucket), manifests as commit markers, the GAUL
  sidecar, and the no-collapse boundary (delivery/draws.py). Supersedes the phantom
  "platform ADR-046". Adopted 2026-07-15 via views-models#149.

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
