# ADR-002: Topology and Dependency Rules

**Status:** Accepted — amended 2026-06-27 (see [Amendment](#amendment-2026-06-27))  
**Date:** 2026-06-02  
**Deciders:** Project maintainers (PRIO MD&D Team)  

---

> **Note (2026-06-27):** the *decision* below — dependencies must be acyclic and flow
> downward — still holds. Its **illustrative internal layering** (Pipeline Managers →
> Spatial Mapping Engine → Geographic Data Assets) is stale: the Spatial Mapping Engine and
> Geographic Data Assets layers were removed (ADR-011 / C-39). The current internal structure
> and the cross-repo topology this ADR originally omitted are in the
> [Amendment](#amendment-2026-06-27) at the bottom. Original text preserved as the record.

---

## Context

In complex systems, architectural fragility often emerges not from incorrect
logic, but from uncontrolled dependencies between components.

In views-postprocessing, the relationship between geographic data assets, the spatial mapping engine, pipeline managers, and external services must remain well-defined. Without explicit topology rules:

- high-level orchestration begins depending on low-level spatial implementation details,
- circular dependencies emerge,
- and system evolution becomes constrained by accidental coupling.

A clear rule is required to define **who may depend on whom**.

---

## Decision

This repository enforces a strict, directional dependency structure.

> Dependencies must follow declared architectural direction.
> No component may depend on a layer above it.

Dependency direction is part of the system's structural integrity.

Violations are architectural defects.

---

## Layering Principle

The dependency direction for views-postprocessing is:

```
Pipeline Managers (orchestration)
       ↓
Spatial Mapping Engine (domain logic)
       ↓
Geographic Data Assets (reference data)
```

- Pipeline Managers may depend on the Spatial Mapping Engine.
- The Spatial Mapping Engine may depend on Geographic Data Assets.
- Geographic Data Assets must not depend on anything above them.
- External Service Configurations are consumed by Pipeline Managers only.

Dependency direction must remain acyclic.

---

## Architectural Boundaries

Each component must:

- Declare its responsibility zone (see ADR-001),
- Respect dependency direction (this ADR),
- Avoid implicit cross-layer coupling.

This ADR governs **structural dependency direction only**.

> The definition and validation of boundary contracts (schemas, configuration validation, handshake rules) are governed separately by ADR-009.

Topology defines *who may depend on whom*.  
ADR-009 defines *what must be true at the boundary*.

---

## Forbidden Patterns

Examples of architectural violations:

- Spatial Mapping Engine importing Pipeline Manager code
- Geographic Data Assets depending on runtime caching configuration
- Pipeline Managers bypassing the Mapping Engine to perform raw spatial operations directly
- External service configuration logic embedded within the Spatial Mapping Engine

If a dependency feels "convenient but wrong," it probably is.

---

## Consequences

### Positive

- Improved modularity
- Easier reasoning about change impact
- Safer refactoring
- Reduced architectural entropy

### Negative

- May require additional abstraction layers
- Can introduce short-term friction during refactoring

These costs are accepted intentionally.

---

## Notes

This ADR defines structural direction of dependencies.

It does not define:

- boundary contract validation (ADR-009),
- semantic authority (ADR-003),
- or testing obligations (ADR-005).

Topology governs structure.  
Contracts govern interaction.

---

## Amendment (2026-06-27)

This amendment updates the *illustration* of the dependency rule to current reality and adds
the **cross-repo topology** the original ADR omitted. The rule itself (acyclic, downward) is
unchanged.

### Cross-repo topology

views-postprocessing is one stage in a one-way platform pipeline. Dependencies flow **down**:

```
views-datafactory      (produces data)
        ↓
views-pipeline-core    (the framework: lifecycle, data loader, dataset, datastore tools)
        ↓
views-postprocessing   (THIS REPO — post-forecast delivery + input-integrity)
        ↓
views-faoapi           (serves the delivered data; collapses draws)
```

- This repo **depends on** views-pipeline-core (it subclasses its postprocessor base —
  Template Method) and views-frames (the frame contract). It **does not** depend on faoapi.
- **views-pipeline-core does not depend on this repo** (verified: zero imports). The
  dependency is strictly one-way; a cycle here would be an architectural defect per the rule
  above.
- **views-models** is the runner/composition root — it constructs this repo's manager and
  calls `.execute()`; it is not a dependency *of* this repo.

### Current internal layering (replaces the stale illustration)

```
unfao/            THE PARTNER — product.py, appwrite_env.py, managers/unfao.py
   │              (the manager is the ONLY importer of views_pipeline_core)
   │ calls
   ▼
contract/         THE MACHINERY — wire/ (ADR-013), frames, frame_extraction,
   │              gaul_lookup/gaul_schema/enrichment, historical,
   │              source_metadata, store_metadata, launch_config
   │ feeds primitives to
   ▼
delivery/         THE RULES — coverage, draws, parity, observed_range, provenance
                  (representation-free; imports neither pandas nor views_frames)
```

**Dependencies point one way only** (SDP): `unfao/` → `contract/` → `delivery/`. Nothing in
`contract/` may import `unfao/` — that is what makes the machinery reusable by a clone, and it
is enforced mechanically by `tests/test_clone_readiness.py`, not by convention (#153/#155).

- The manager **calls** the delivery invariants; it never inherits them. Invariants depend
  only on primitives (DIP), so a representation change lands in the seam alone (OCP / C-40).
- Geography is a precomputed asset consumed by the enricher — there is no runtime spatial
  engine layer anymore.

### See also

- The narrative version of this topology and the internal seams:
  [`docs/architecture/role_and_seams.md`](../architecture/role_and_seams.md).
- The revised ontology these categories come from: [ADR-012](012_revised_ontology.md).
