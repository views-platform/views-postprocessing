
# ADR-003: Authority of Declarations Over Inference

**Status:** Accepted  
**Date:** 2026-06-02  
**Decider:** Simon Polichinel von der Maase  

---

## Context

In views-postprocessing, the same spatial concept often appears in multiple representations:
- A PRIO-GRID cell has a geometry, a centroid, and an assigned country
- Administrative boundaries exist at multiple levels with potentially conflicting assignments
- Configuration for external services exists in environment variables, dotenv files, and code constants

When these representations diverge, systems often attempt to **infer intent** after the fact.

Such inference leads to:
- silent errors,
- irreproducible results,
- post-hoc rationalization,
- and ambiguity about what the system actually believes.

A clear rule is required to define **where semantic authority lives**, and how ambiguity is resolved.

---

## Decision

In this repository:

> **All meaningful semantics must be explicitly declared.  
> Inference of semantics across component boundaries is forbidden.**

When multiple representations of the same concept exist, **a single source of truth must be designated**.

If required semantics are missing, ambiguous, or contradictory, the system **must not guess**.

---

## Global Invariant: Fail Loud on Semantic Ambiguity

In this repository, **silent failure is considered a bug**.

Whenever required semantics are:
- missing,
- ambiguous,
- contradictory,
- or inconsistent across representations,

the system **must fail loudly and immediately**.

This includes, but is not limited to:
- raising explicit runtime errors,
- failing validation or consistency checks,
- refusing to proceed without explicit declaration.

Warning-only behavior, implicit fallbacks, or "best-effort" inference are **forbidden**
for any decision-relevant semantics.

This rule applies regardless of environment:
development, experimentation, evaluation, or production.

---

## Rules of Semantic Authority

The following rules apply throughout the repository:

- Semantics must be **declared**, not inferred.
- Transformations are owned by the component that performs them.
- Metadata overrides naming conventions.
- Evaluation consumes **declared semantics only**.
- No component may guess another component's intent.

Inference is permitted **only within a component's internal logic**, never across component boundaries.

---

## Examples of Forbidden Behavior

- Inferring country assignment from column name prefixes (e.g., assuming `country_iso_a3` was produced by the mapper without verification)
- Inferring PRIO-GRID cell coordinates from the GID number rather than from the shapefile
- Inferring Appwrite bucket configuration from the postprocessor name
- Proceeding with upload when required environment variables are `None`
- Guessing admin level from the number of digits in a GAUL code

If behavior matters, it must be declared.

---

## Consequences

### Positive
- Eliminates silent semantic drift
- Improves reproducibility and debuggability
- Makes disagreements explicit and resolvable
- Enables principled failure under uncertainty

### Negative
- Requires more explicit configuration and metadata
- Some convenience patterns are disallowed
- Errors may surface earlier and more frequently

These costs are accepted intentionally.

---

## Notes

This ADR does not define:
- what concepts exist (ADR-001),
- or how components depend on each other (ADR-002).

It defines **who is allowed to say what something means**,  
and mandates **loud failure over silent misinterpretation**.
