# The Hardened Protocol: Contributor Governance for Spatial Computation

This document defines the mandatory engineering and spatial computation standards for the `views-postprocessing` repository. Adherence to this protocol is required for all contributions to guarantee geographic correctness and reproducibility of spatial assignments.

---

## 1. Core Principles

### A. The Authority of Declarations (ADR-003)
**"Never infer; only trust declarations."**
All meaningful spatial semantics (coordinate reference systems, assignment algorithms, overlap thresholds) must be explicitly declared.
- **Prohibited:** Inferring country from column name patterns, deriving coordinates from GID arithmetic, or guessing admin boundaries from naming conventions.
- **Requirement:** If a parameter affects spatial assignment correctness, it must be validated at the boundary (ADR-009).

### B. The Fail-Loud Mandate (ADR-008)
**"A crash is a successful defense of geographic integrity."**
Silent failures, implicit fallbacks, and "best-effort" spatial assignments are forbidden.
- **Requirement:** Missing shapefiles, invalid geometries, or unresolvable spatial lookups must raise explicit errors immediately.
- **Prohibited:** Returning `None` silently for cells that should have assignments, or falling back to centroid-based methods without declaration.

### C. The Spatial Integrity Gate
All spatial operations must preserve geographic correctness:
- **Requirement:** All shapefiles must be validated for CRS consistency (EPSG:4326) at load time.
- **Requirement:** Overlap ratio calculations must be documented with their geometric assumptions (planar vs geodesic).
- **Requirement:** Assignment results must be deterministic — the same GID must always map to the same country/admin region given the same input data.

### D. The Reproducibility Contract
Spatial mapping results must be reproducible across sessions:
- **Requirement:** Cache mode (disk vs memory) must not affect mapping results — only performance.
- **Requirement:** Forward and reverse lookups must be bijectively consistent (if GID X maps to country A, then country A's GID list must include X).
- **Requirement:** Changes to the assignment algorithm require a new ADR and full regression testing.

---

## 2. Contributor Requirements

### Adding a New Spatial Mapping Method
1. **Declare the Algorithm:** Document the assignment rule explicitly (largest overlap, centroid containment, etc.)
2. **Validate Consistency:** Verify bijection between forward and reverse lookups.
3. **Test Border Cases:** Include tests for cells spanning multiple boundaries.
4. **Document Limitations:** State geometric assumptions (planar area, high-latitude behavior).

### Adding a New Partner Delivery Format
1. **Define the Schema:** Declare required output columns and their sources.
2. **Validate at Boundary:** Validate both column presence AND null counts.
3. **Test End-to-End:** Include integration tests from raw data through delivery.

---

## 3. Mandatory Testing Taxonomy (ADR-005)

Every Pull Request must include tests covering the following three perspectives:

### Green Team (Stability & Correctness)
* **Goal:** Ensure spatial assignments are correct and reproducible.
* **Examples:** Known-good GID-to-country mappings, schema compliance of enriched outputs, cache mode equivalence.

### Beige Team (Configuration & Human Error)
* **Goal:** Catch failures caused by common configuration mistakes or incomplete data.
* **Examples:** Missing environment variables, None-valued Appwrite configs, DataFrames with unexpected column names.

### Red Team (Adversarial)
* **Goal:** Expose failure modes by deliberately testing edge cases.
* **Examples:** Ocean-only cells, cells at extreme latitudes, cells spanning 3+ countries, corrupted shapefile geometries.

---

## 4. Operational Invariants

- **Geographic Determinism:** The same input shapefile + GID must always produce the same country/admin assignment.
- **Cache Transparency:** Switching between disk and memory cache modes must not change results.
- **Boundary Validation:** All environment variables must be validated as non-None before Appwrite operations proceed.
- **Schema Completeness:** Null value checks must be active (not commented out) for all required metadata columns before partner delivery.

---

**"In this repository, we value geographic correctness over convenient execution."**
