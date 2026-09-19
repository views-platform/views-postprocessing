
# ADR-004: Rules for Evolution and Stability

**Status:** Deferred  
**Date:** 2026-06-02  
**Deciders:** —  
**Informed:** All contributors  

---

## Context

The preceding ADRs establish:

- **ADR-001:** the ontology of the repository (what exists)
- **ADR-002:** the topology of the repository (how components may relate)
- **ADR-003:** semantic authority (who owns meaning and how it is declared)

Together, these decisions define the system's structure and semantics at a point in time.

What they do **not** yet define is how the system is allowed to **change over time**:
- which components are expected to be stable
- which components may evolve freely
- what constitutes a breaking change
- when compatibility guarantees apply
- when a new ADR is required

These questions are architectural, cross-cutting, and costly to reverse once external users or downstream dependencies exist.

---

## Decision

No decision is made at this time.

Rules governing stability, evolution, and backwards compatibility are **explicitly deferred**.

This ADR exists to:
- acknowledge the importance of this dimension
- reserve a place for a future, explicit decision
- prevent ad-hoc or implicit policies from emerging unnoticed

---

## Rationale for Deferral

At the time of writing:

- Core abstractions are still being exercised and refined
- The boundary between experimental and stable components may shift
- Premature guarantees would either be ignored or constrain necessary exploration

Deferring this decision preserves design freedom while maintaining architectural honesty.

---

## Trigger Conditions for Reconsideration

This ADR should be revisited when one or more of the following become true:

- External users or downstream systems depend on this repository
- Reproducibility across time becomes a contractual requirement
- Breaking changes begin to incur real coordination or migration costs
- Multiple versions of the same concept must be supported concurrently
- Contributors express uncertainty about what is safe to change

At that point, a new ADR should supersede this one.

> **Audit note, 2026-08-26: at least three of those conditions are now true, and nothing
> noticed.** Recorded here rather than acted on, because writing the successor is an
> architectural decision and this was a documentation audit.
>
> - *"External users or downstream systems depend on this repository"* — views-models pins
>   it in two launchers, views-faoapi and views-crafdapi consume its artifacts, and it has
>   been published on PyPI since 1.0.0.
> - *"Breaking changes begin to incur real coordination or migration costs"* — the 1.1.0 →
>   1.1.1 pin move took eight days and a direct request (views-models#403); 1.2.0's is open
>   as views-models#439. Register **C-111** and **C-112** exist for the two halves of that
>   gap: consumers are told nothing but a version number, and nothing here can see what
>   production actually runs.
> - *"Reproducibility across time becomes a contractual requirement"* — ADR-013 §10 pins
>   delivery bytes against a golden fixture, and C-72 records what a toolchain bump costs.
>
> The deferral itself was sound and remains honest; what has changed is the world it was
> deferring against. **Whoever picks this up should write the successor rather than amend
> this document** — that is what its own last line asks for. The owner field above is still
> `—`, which is the part ADR-014 §4 would actually object to.

---

## Non-Decisions (Explicitly Out of Scope for Now)

This ADR does **not** define:
- Versioning schemes
- Release processes
- Migration tooling
- Deprecation mechanics
- API stability guarantees

Those topics are intentionally postponed.

---

## Consequences

### Positive
- Avoids premature or brittle guarantees
- Preserves flexibility during early evolution
- Makes the absence of rules explicit rather than accidental

### Negative
- Contributors must exercise judgment when making breaking changes
- Some uncertainty remains about long-term guarantees

These consequences are accepted intentionally.

---

## Notes

This ADR is a placeholder by design.

Its purpose is to ensure that when rules for evolution and stability are introduced, they are:
- explicit
- deliberate
- consistent with ADR-001 through ADR-003

Until then, change is governed by those ADRs and by careful review.
