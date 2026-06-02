# Instantiation Checklist

Use this checklist when bootstrapping a new project from base_docs templates.

---

## Before You Start

- [x] Decide which adoption phase you're targeting (see `ADRs/README.md` — Recommended Adoption Order)
- [x] Identify your project's ontological categories (data types, models, configs, artifacts, etc.)

---

## ADR Adaptation

### All adopted ADRs
- [x] Update Status from `--template--` to `Proposed` or `Accepted`
- [x] Fill in Date, Deciders, Consulted, Informed fields

### Per-ADR adaptation notes
- [x] **ADR-000:** Updated the `ADRs/` path reference to `docs/ADRs/`
- [x] **ADR-001:** Defined ontological categories: Geographic Data Assets, Spatial Mapping Engine, Pipeline Managers, External Service Configurations, Derived Outputs
- [x] **ADR-002:** Defined layering: Pipeline Managers → Spatial Mapping Engine → Geographic Data Assets
- [x] **ADR-003:** Adapted forbidden behavior examples to spatial/geographic domain
- [x] **ADR-005:** Adapted test taxonomy with spatial-specific examples (border cells, ocean cells, high-latitude distortion)
- [x] **ADR-006:** No domain adaptation needed (criteria are universal)
- [x] **ADR-007:** Verified contributor protocol paths match project structure
- [x] **ADR-009:** Adapted boundary examples to Appwrite, DataFrame schemas, and spatial mapping interfaces

---

## CICs

- [x] Replace placeholder active contracts list in `CICs/README.md` with project-specific notes
- [x] Create intent contracts for `PriogridCountryMapper` and `UNFAOPostProcessorManager`

---

## Contributor Protocols

- [x] Review and adapt `contributor_protocols/silicon_based_agents.md` for project tooling
- [x] Review and adapt `contributor_protocols/carbon_based_agents.md` for project team
- [x] Adapt `contributor_protocols/hardened_protocol.md` for spatial computation domain

---

## Standards

- [x] Review `standards/logging_and_observability_standard.md` — adapted scope expectations to spatial/pipeline domain
- [ ] Physical architecture standard skipped (small library, not 1-class-1-file convention)

---

## Risk Register

- [x] Created `reports/technical_risk_register.md` with 9 initial concerns from repo-assimilation
- [x] Created governing ADR (ADR-010) referencing the register

---

## Final Verification

- [x] No files still have Status `--template--` (except ADR-004 which is Deferred)
- [x] No phantom references to non-existent files
- [x] All cross-ADR references resolve correctly
- [x] Run `validate_docs.sh` to check internal consistency
