
# ADR-001: Ontology of views-postprocessing

**Status:** Accepted  
**Date:** 2026-06-02  
**Deciders:** Project maintainers (PRIO MD&D Team)  

---

## Context

The views-postprocessing repository bridges conflict prediction outputs from the VIEWS platform to external partner consumption formats. It operates at the intersection of spatial data, pipeline orchestration, and cloud delivery.

Without an explicit ontology, systems tend to accumulate:
- implicit concepts
- overloaded abstractions
- objects that mix responsibilities
- semantics that exist only in developers' heads

This leads to ambiguity, fragile refactors, and silent divergence between intent and implementation.

An explicit ontology is required to define **what kinds of things are allowed to exist** in this repository, and which kinds of things are explicitly disallowed.

---

## Decision

This repository defines a **closed set of conceptual categories** ("entities") that are allowed to exist.

Each category has:
- a clear semantic role
- an expected stability level
- explicit boundaries

Anything that does not clearly belong to one of these categories is considered **out of scope** and must be re-designed or rejected.

---

## Core Ontological Categories

| Category | Purpose | Authority | Stability |
|----------|---------|-----------|-----------|
| **Geographic Data Assets** | Bundled shapefiles providing spatial reference data (Natural Earth countries, PRIO-GRID cells, GAUL admin boundaries) | Authoritative — these are the ground truth for spatial operations | Stable — updated only when upstream sources release new versions |
| **Spatial Mapping Engine** | Core domain logic for mapping PRIO-GRID cells to administrative boundaries via spatial intersection and largest-overlap assignment | Authoritative — defines the assignment algorithm | Stable — changes require explicit justification and testing |
| **Pipeline Managers** | Orchestration components that read, transform, validate, and deliver prediction data to partner organizations | Derived — implements delivery logic using the mapping engine | Evolving — may change as partner requirements change |
| **External Service Configurations** | Appwrite connection configs, environment variables, bucket/collection references | Operational — enables integration with external storage | Evolving — changes as infrastructure changes |
| **Derived Outputs** | Enriched DataFrames and parquet files produced by the pipeline and delivered to partners | Ephemeral — produced on each run, not persisted in the repository | Ephemeral — recreated each execution cycle |

---

## Stability Rules

- **Geographic Data Assets** are expected to be stable across the lifetime of the project. Changes require updating shapefiles from upstream sources and verifying spatial consistency.
- **Spatial Mapping Engine** is expected to be stable. Changes to assignment logic (e.g., the largest-overlap rule) constitute architectural decisions requiring a new ADR.
- **Pipeline Managers** are explicitly allowed to evolve as partner requirements change.
- **External Service Configurations** are operational and may change independently of code logic.
- **Derived Outputs** have no stability expectation — they are recreated each pipeline run.

Stability is a design constraint, not a preference.

---

## Explicit Non-Entities

The following are **not allowed** as first-class concepts:

- Implicit or inferred semantics (e.g., guessing country from grid position without explicit spatial intersection)
- Objects that mix multiple ontological roles (e.g., a class that is both a mapper and a pipeline manager)
- "Convenience" abstractions that hide meaning (e.g., magic defaults for Appwrite configuration)
- Concepts that exist only via naming conventions (e.g., inferring admin level from column name prefixes)

If a concept matters, it must be explicit.

---

## Consequences

### Positive
- Shared vocabulary across contributors
- Reduced conceptual drift
- Clear review criteria for new abstractions

### Negative
- Requires upfront discipline
- Some refactors may be blocked until concepts are clarified

These trade-offs are accepted.

---

## Notes

This ADR defines *what exists*, not *how components depend on each other*.  
Dependency rules are defined separately in ADR-002.
