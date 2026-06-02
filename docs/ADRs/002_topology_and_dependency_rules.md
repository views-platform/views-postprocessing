# ADR-002: Topology and Dependency Rules

**Status:** Accepted  
**Date:** 2026-06-02  
**Deciders:** Project maintainers (PRIO MD&D Team)  

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
