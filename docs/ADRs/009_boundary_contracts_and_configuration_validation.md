# ADR-009: Boundary Contracts and Configuration Validation

**Status:** Accepted  
**Date:** 2026-06-02  
**Decider:** Simon Polichinel von der Maase  

---

## Context

Complex systems fail most often at boundaries:

- between the spatial mapping engine and pipeline managers,
- between configuration (environment variables) and runtime behavior,
- between data producers (ViewsER, Appwrite) and the postprocessor,
- between the postprocessor and external partner delivery (UN FAO bucket).

In views-postprocessing, ambiguous configuration, hidden defaults, and implicit contracts
introduce silent semantic drift and runtime fragility. Environment variables that arrive as `None` from `os.getenv()` are a concrete example of boundary failure.

To preserve architectural integrity and fail-loud guarantees (ADR-003),
all external and internal boundaries must be explicit and validated.

---

## Decision

This repository adopts the following invariants:

> All architectural boundaries must declare explicit contracts.  
> All configuration must be validated at entry.  
> No semantic defaults may exist silently.

---

## 1. Boundary Contracts

Every boundary between components must define:

- Explicit input schema
- Explicit output schema
- Declared invariants
- Failure semantics

Boundaries in views-postprocessing include:

- Environment variables → Appwrite configuration
- Appwrite download → DataFrame ingestion
- DataFrame → Spatial mapping engine (column name contract)
- Spatial mapping engine → enriched DataFrame (output schema contract)
- Enriched DataFrame → validation → Appwrite upload

Implicit contracts are prohibited.

If a boundary assumption cannot be declared clearly,
the boundary is ill-defined and must be redesigned.

---

## 2. Configuration as First-Class Artifact

Configuration is not a convenience layer.
It is an architectural artifact.

Configuration must:

- Be explicit
- Be versionable
- Be externally inspectable
- Be validated before execution
- Not rely on hidden defaults

Changing configuration must not silently alter system meaning.

---

## 3. Validation at Entry (Handshake Principle)

All configuration and external inputs must be validated at the system boundary.

Validation must occur:

- Before state mutation
- Before execution begins
- Before orchestration proceeds

The system must fail early if:

- Required environment variables are missing or None
- DataFrame schemas do not match expected columns
- Appwrite bucket/collection IDs are empty
- Shapefile paths do not resolve to valid files

Borrowed or assumed state is prohibited.

---

## 4. Separation of Configuration Domains

Configuration domains must be separated conceptually:

- **Operational parameters** (Appwrite endpoints, bucket IDs — affect data routing)
- **Behavioral parameters** (cache mode, batch size — affect processing behavior)
- **Reference data** (shapefile paths — affect spatial accuracy)

Cross-domain coupling must be explicit.

Configuration that affects behavior must not be disguised as documentation.

---

## 5. Redundancy and Consistency Checks

Where ambiguity risk is high, explicit redundancy is preferred.

Examples in views-postprocessing:

- Declaring both bucket ID and bucket name for Appwrite
- Declaring both shapefile path and expected CRS
- Validating column presence AND null counts (not just column existence)

Redundant declarations must be validated for consistency.

Silent derivation is discouraged where semantic meaning is involved.

---

## 6. Failure Semantics

Configuration validation failures must:

- Be logged (ADR-008)
- Be raised explicitly (ADR-008)
- Halt execution

Warnings are insufficient for structural configuration errors.

---

## Consequences

### Positive

- Eliminates hidden configuration drift
- Reduces boundary fragility
- Strengthens fail-loud guarantees
- Improves reproducibility and traceability

### Negative

- Requires explicit schemas
- Adds validation boilerplate
- Increases up-front configuration clarity requirements

These costs are accepted.

---

## Notes

This ADR does not prescribe:

- Specific file layouts
- Specific configuration libraries
- Specific schema frameworks

Operational configuration structures may vary,
provided they comply with the invariants defined here.
