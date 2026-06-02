# ADR-010: Technical Risk Register as First-Class Governance Artifact

**Status:** Accepted  
**Date:** 2026-06-02  
**Deciders:** Project maintainers (PRIO MD&D Team)  

---

## Context

The views-postprocessing package is a critical component in the VIEWS pipeline delivering conflict prediction data to partner organizations (UN FAO). It handles spatial mapping of PRIO-GRID cells to administrative boundaries and enriches prediction data with geographic metadata.

The package has structural risks identified during repository assimilation that require formal tracking. Without a formal mechanism to track and triage these risks, they are likely to be forgotten or deprioritized until they cause production incidents.

---

## Decision

We adopt a Technical Risk Register (`reports/technical_risk_register.md`) as a first-class governance artifact for this repository.

The register:
- Uses a 4-tier severity system (Critical, High, Medium, Low)
- Requires actionable triggers for each concern
- Tracks provenance (which audit/review produced the finding)
- Supports deduplication and cross-referencing between related concerns
- Is maintained alongside code changes that affect registered risks

---

## Concern Format

Each concern entry includes:
- **ID:** `C-xx` for concerns, `D-xx` for disagreements
- **Tier:** 1-4 with explicit rationale
- **Source:** Skill or audit that produced the finding
- **Trigger:** Specific future action that makes the concern acute
- **Location:** File path(s) with line numbers
- **Narrative:** Grounded description of the risk

---

## Tier Definitions

| Tier | Severity | Criteria |
|------|----------|----------|
| 1 | Critical | Silent data corruption or model output incorrectness. No error signal. |
| 2 | High | Structural fragility that will cause failures under realistic change scenarios. |
| 3 | Medium | Maintainability or coupling issues that increase cost of change. |
| 4 | Low | Code quality observations. No correctness or reliability impact. |

---

## Process

- Concerns are registered via the `register-risk` skill
- The register is curated and prioritized via the `review-rr` skill
- Concerns are resolved by fixing the underlying issue and moving the entry to "Resolved Concerns"

---

## Consequences

### Positive
- Formal tracking prevents risks from being forgotten
- Tiered severity enables principled prioritization
- Trigger-based format connects risks to specific development scenarios

### Negative
- Requires maintenance discipline
- Register may accumulate stale entries if not regularly reviewed

These costs are accepted intentionally.

---

## References

- `reports/technical_risk_register.md` — the active register
- ADR-005 (Testing) — risks related to test coverage are tracked in the register
- ADR-003 (Authority of Declarations) — the register is an explicit declaration of known risks
