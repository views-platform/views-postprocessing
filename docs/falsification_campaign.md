# Falsification Campaign: Business Logic Verification

## Purpose

Before making any further changes to this repository, we must prove that we:
1. Understand the business logic
2. Can demonstrate the code works correctly
3. Have sufficient tests (unit, functional, regression, integration, end-to-end) to catch drift and breakage

This document defines a sequence of falsifiable claims. Each claim is audited via `/falsify`, findings are registered via `/register-risk`, and then we move to the next claim.

## CRITICAL CONSTRAINT: READ-ONLY CAMPAIGN

**This campaign does NOT modify source code.** Its purpose is to **catalogue what we know, what we don't know, and what is broken** — not to fix anything.

- **Do NOT modify** `mapping.py`, `unfao.py`, or any source file
- **Do NOT modify** existing tests to make them pass
- **Do** write NEW test stubs (falsification stubs are documentation of gaps, not fixes)
- **Do** update the risk register (that IS the catalogue)
- **Do** update CICs/ADRs if a finding reveals the documentation is wrong about the code's behavior — the documentation should describe what the code DOES, not what we wish it did
- **"Fix" means:** register the finding, write a failing test stub, update docs to match reality. That's it.
- **Source code fixes happen AFTER the campaign**, informed by the complete catalogue of findings

If a claim is FALSIFIED, we register the findings, note them in the progress tracker, and move to the next claim. We do NOT enter a fix-and-reaudit loop. The goal is a complete inventory, not incremental repair.

## Execution Protocol

For each claim:
1. Run `/falsify <claim text>`
2. Confirm the proposed probes
3. After the verdict, run `/register-risk` to capture any findings
4. Update the progress tracker with the verdict
5. Move to the next claim regardless of verdict (SURVIVED, CONTESTED, or FALSIFIED)

## Campaign Structure

The claims are organized in 4 layers. Each layer builds on the previous. A falsification in an earlier layer blocks later layers.

---

## Layer 1 — Do we understand the business logic?

### Claim 1.1
```
The PriogridCountryMapper CIC (sections 3, 4, 5, and 6) accurately describes
the mapper's actual behavior for all documented operations: the largest-overlap
algorithm, the make_valid preprocessing, the zero-area guards, the cache modes,
the spatial index usage, and the return types of find_country_for_gid,
find_admin1_for_gid, find_admin2_for_gid, and enrich_dataframe_with_pg_info.
```

### Claim 1.2
```
The UNFAOPostProcessorManager CIC accurately describes the pipeline's actual
behavior: the 4-stage sequence (read, transform, validate, save), the two data
sources (ViewsER for historical, Appwrite for forecast), the enrichment via
PriogridCountryMapper, the null validation with log-before-raise, and the
upload to the UN FAO Appwrite bucket with enrichment_description metadata.
```

### Claim 1.3
```
ADR-011's description of the area-majority algorithm, the sequential allocation
rule, the FAO-confirmed constraints, and the precomputed lookup table strategy
is consistent with what the code in mapping.py implements and what the FAO
release notes (Pre-release Note 02 Topic A, Release Note 01 Topic C, Release
Note 02 Topic A) specify. No contradiction exists between the three sources.
```

---

## Layer 2 — Does the code produce correct results?

### Claim 2.1
```
For PRIO-GRID cells that are entirely within a single country (no border
overlap), the mapper assigns them to that country with an overlap_ratio
very close to 1.0, and the method field reads "largest overlap".
```

### Claim 2.2
```
For PRIO-GRID cells that span two countries, the mapper assigns them to
the country with the larger area share. The overlap_ratio in the result
reflects the actual geometric proportion of the cell covered by the
assigned country. The cell is NOT assigned to the country containing
the centroid if a different country has more area overlap.
```

### Claim 2.3
```
The sequential allocation invariant holds in the current code: every cell's
Admin 1 and Admin 2 assignments are within the country assigned at Admin 0.
find_admin1_for_gid first calls find_country_for_gid, then filters admin
regions to that country before computing overlap. No cross-border subnational
assignment is possible.
```

### Claim 2.4
```
The enrichment output schema produced by enrich_dataframe_with_pg_info
(column names and types) matches exactly what _append_metadata in unfao.py
expects in its filter_cols list. The 3-step derivation (shapefile column
to dict key to prefixed DataFrame column) produces the correct names for
all 9 metadata columns.
```

---

## Layer 3 — Do we have sufficient tests?

### Claim 3.1
```
The unit tests in test_mapping.py cover all 7 CIC guarantees from
PriogridCountryMapper section 3 and all 6 CIC failure modes from section 6,
with at least one test per guarantee and one test per failure mode. No CIC
promise is untested.
```

### Claim 3.2
```
The validation tests in test_validation.py verify that the validation logic
rejects every category of invalid input (missing columns, null values in
each of the 9 required columns, NaN values) and accepts valid input. The
test logic matches the actual _validate() implementation in unfao.py — if
the real code diverges from the test replica, a developer would notice.
```

### Claim 3.3
```
A regression test exists for every code fix applied in this session (C-01
null validation, C-18 warning suppression removal, C-20 zero-area guards,
make_valid preprocessing, batch failure tracking) such that reverting any
single fix would cause at least one test to fail.
```

### Claim 3.4
```
An integration test exists that enriches a DataFrame through the mapper
(enrich_dataframe_with_pg_info) and then checks the output against the
manager's filter_cols list and null validation rules — testing the full
mapper-to-manager data path in a single test.
```

### Claim 3.5
```
An end-to-end test exists or can be constructed that exercises the full
pipeline from _read() through _save(), verifying that the output parquet
file has the correct schema (all 9 metadata columns present and non-null)
and that the upload metadata includes the enrichment_description timestamp.
```

---

## Layer 4 — Can we detect drift and breakage?

### Claim 4.1
```
The CI pipeline (GitHub Actions run_pytest.yml) runs all tests on every
push to development and main, and the pytest step is active (not commented
out). A test failure would block the workflow.
```

### Claim 4.2
```
If a future contributor changes the assignment algorithm from area-majority
to centroid-based (e.g., replacing the overlap loop with a point-in-polygon
check), at least one existing test in test_mapping.py fails.
```

### Claim 4.3
```
If the enrichment output schema changes (a column in filter_cols is renamed,
added, or removed in either the mapper's _process_pg_batch or the manager's
_append_metadata), at least one existing test fails.
```

---

## Progress Tracker

| Claim | Status | Round | Findings | Date |
|-------|--------|-------|----------|------|
| 1.1 | FALSIFIED | 1 | 3H/1S: cache guarantee contradicts C-05, return types underspecified (~170 keys not 4), CIC says WARNING code uses DEBUG, admin1 return has undocumented keys. All are CIC-doc issues — underlying code already in register. | 2026-06-02 |
| 1.2 | FALSIFIED | 1 | 2H: 3/7 raises lack logger.error (CIC claims ADR-008 compliance), 18 os.getenv() pass None without validation (CIC claims boundary failure). Already in C-19, C-13. | 2026-06-02 |
| 1.3 | SURVIVED | 1 | clean — ADR-011 consistent with code and FAO notes, schema divergence covered in prerequisite section | 2026-06-02 |
| 2.1 | SURVIVED | 1 | clean — interior cells: correct country, overlap_ratio=1.0, method="largest overlap" | 2026-06-02 |
| 2.2 | SURVIVED | 1 | clean — border cell: correct country (AAA=60%), overlap_ratio=0.60. Observation: synthetic data can't produce centroid-area disagreement. | 2026-06-02 |
| 2.3 | SURVIVED | 1 | clean — all 4 cells: admin1/admin2 consistent with admin0 country. No cross-border subnational assignment. | 2026-06-02 |
| 2.4 | SURVIVED | 1 | clean — all 9 filter_cols present in enriched output. 15 extra columns also present but filtered by _append_metadata. | 2026-06-02 |
| 3.1 | CONTESTED | 1 | 0H/5S: no test for make_valid, spatial index, invalid geometry, zero-area cell, missing columns. 8 of 13 CIC items tested, 5 gaps. | 2026-06-02 |
| 3.2 | CONTESTED | 1 | 0H/2S: no wrong-type test, validation tests use replica not real _validate(). Good coverage otherwise (36 parametrized tests). | 2026-06-02 |
| 3.3 | FALSIFIED | 1 | 4H: no regression test for C-18 (warning removal), C-20 (zero-area), make_valid, C-21 (batch tracking). Only C-01 (null validation) has regression coverage. | 2026-06-02 |
| 3.4 | FALSIFIED | 1 | 1H: no integration test exists for mapper→filter_cols→validate path. Mapper and manager tested in isolation only. | 2026-06-02 |
| 3.5 | FALSIFIED | 1 | 1H: no E2E pipeline test. views-pipeline-core not in test env blocks direct instantiation. | 2026-06-02 |
| 4.1 | CONTESTED | 1 | 0H/1S: pytest step active, runs on push. But cannot verify it's a required status check for PR merges (GitHub settings, not repo). | 2026-06-02 |
| 4.2 | SURVIVED | 1 | clean — test_cell_fully_in_country_a asserts method=="largest overlap", would fail if algorithm changed to centroid. overlap_ratio key existence also sensitive. | 2026-06-02 |
| 4.3 | CONTESTED | 1 | 0H/2S: enrichment test checks 5 of 9 filter_cols, validation replica can drift from real code. Rename of existing column IS caught. | 2026-06-02 |
