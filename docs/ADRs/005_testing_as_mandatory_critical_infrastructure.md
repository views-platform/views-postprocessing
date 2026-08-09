
# ADR-005: Testing as Mandatory Critical Infrastructure

**Status:** Accepted  
**Date:** 2026-06-02  
**Decider:** Simon Polichinel von der Maase  

---

## Context

This repository supports a system whose outputs directly inform UN FAO operational decisions regarding food security in conflict-affected regions. The spatial mapping and data enrichment performed here is consumed by external partners without further verification.

In such systems, failure is not limited to crashes or exceptions.
Failures may also include:
- silent semantic drift (wrong country assigned to a grid cell),
- misuse by well-intentioned users,
- over-trust or under-trust in outputs,
- brittle behavior under realistic conditions (border cells, ocean cells).

Given this, testing is not a convenience or a quality signal.
It is **critical infrastructure**.

The absence of rigorous, multi-perspective testing constitutes unacceptable risk.

---

## Decision

This repository treats **testing as mandatory critical infrastructure**.

All non-trivial functionality **must be covered by tests**.

Testing is not limited to correctness under ideal conditions, but must explicitly address:
- adversarial behavior,
- realistic human use,
- and system robustness under expected operation.

To achieve this, tests are explicitly divided into **three complementary categories**:

- Red team tests (adversarial)
- Beige team tests (realistic, neutral misuse)
- Green team tests (supportive, resilience-oriented)

Each category serves a distinct purpose and **none may substitute for another**.

---

## Test Taxonomy

### Red Team Tests — Adversarial Testing

Red team tests deliberately attempt to **break, exploit, or misuse the system** by assuming hostile or worst-case behavior.

- **Goal:** expose failure modes, vulnerabilities, unsafe behaviors
- **Mindset:** *"How could this go wrong?"*
- **Typical focus:**
  - Invalid or non-existent PRIO-GRID IDs
  - Corrupted or missing shapefiles
  - Cells entirely over ocean with no country assignment
  - Extreme latitudes where planar area distortion is maximal
  - Appwrite configuration with None/missing values

Red team tests are expected to fail the system until weaknesses are addressed.

---

### Beige Team Tests — Realistic, Neutral Usage

Beige team tests focus on **boring, realistic, non-adversarial usage patterns** that are neither friendly nor hostile — but still dangerous if mishandled.

- **Goal:** catch failures caused by normal human behavior
- **Mindset:** *"What will regular users actually do?"*
- **Typical focus:**
  - Border cells spanning multiple countries
  - Processing large batches with mixed valid/invalid GIDs
  - Using the mapper with both disk and memory cache modes
  - Enriching DataFrames with unexpected column names

In data delivery systems, beige failures are often the most damaging.

---

### Green Team Tests — Supportive, Resilience-Oriented Testing

Green team tests focus on **ensuring the system works as intended** under expected conditions and degrades safely.

- **Goal:** ensure reliability, robustness, and trustworthiness
- **Mindset:** *"How do we make this solid?"*
- **Typical focus:**
  - Correct country assignment for unambiguous cells
  - Consistent results between cache modes
  - Schema compliance of enriched output DataFrames
  - Bijection consistency between forward and reverse mapping

Green team tests are expected to pass continuously and form the backbone of CI.

---

## Relationship to Other ADRs

This ADR reinforces and operationalizes:

- **ADR-001 (Ontology):** tests must respect declared concepts and stability expectations
- **ADR-002 (Topology):** tests must not bypass architectural boundaries
- **ADR-003 (Authority & Semantics):** tests must fail loudly on semantic ambiguity
- **ADR-004 (Deferred):** future evolution rules must account for test coverage obligations

Testing is a primary mechanism by which these ADRs are enforced.

---

## Enforcement Rules

- Code that meaningfully affects behavior **must not be merged without tests**
- Tests that only cover happy paths are insufficient
- Warning-only behavior in tests is unacceptable for decision-relevant semantics
- If a failure mode is known and untested, it is considered technical debt and must be tracked explicitly

The absence of appropriate tests is valid grounds for blocking a change.

---

## Consequences

### Positive
- Reduced risk of silent failure
- Earlier detection of misuse and misunderstanding
- Increased trustworthiness of outputs
- Clearer system boundaries and guarantees

### Negative
- Higher upfront development cost
- Slower iteration if tests are neglected
- Requires cultural discipline and reviewer enforcement

These costs are accepted intentionally.

---

## Notes

Testing in this repository is not merely about correctness.

It is about **preventing harm, misunderstanding, and overconfidence**  
in systems that operate under uncertainty and deliver data to external partners.
