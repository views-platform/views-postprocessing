# Class Intent Contract: ReconciliationModule

**Status:** Active
**Owner:** PRIO MD&D Team
**Last reviewed:** 2026-06-24
**Related ADRs:** ADR-003 (fail loud), views-frames ADR-014 (injected cross-level mapping); epic #31, migration `docs/reconciliation_migration.md`, origin #3 / views-reporting#72

---

## 1. Purpose

> Make PRIO-GRID-month (pgm) forecasts consistent with country-month (cm) totals: within each `(time, country)`, scale the country's grid cells so their per-draw sum equals the country forecast, preserving each cell's relative share and its zeros.

It is the frames-native, numpy-only home of the reconciliation that previously lived in views-reporting (`ForecastReconciler` + `ReconciliationModule`), ported parity-preserving.

---

## 2. Non-Goals (Explicit Exclusions)

- Does **not** embed or fetch geography. The `(time, priogrid_gid) -> country_id` mapping is **injected** at construction (views-frames ADR-014); the class never queries viewser, shapefiles, or the GAUL lookup.
- Does **not** change the algorithm. It is **top-down proportional scaling per posterior draw** (FPP3 forecast proportions), a faithful port — **not** principled joint probabilistic reconciliation (the upgrade is **C-37**, deferred).
- Does **not** load, save, or upload data; does **not** depend on pandas, torch, viewser, or wandb.
- Does **not** mutate its inputs.

---

## 3. Responsibilities and Guarantees

- Validates inputs fail-loud before any work (level, sample-count, time coverage, country coverage).
- For each `(time, country)`: scales grid cells so their per-draw sum **equals** the country forecast; preserves zero cells; clamps to non-negative.
- Returns a **new** pgm `PredictionFrame` with the same index/metadata as the input grid frame (de-mutation, C-184).
- Bit-for-bit reproduces the frozen views-reporting pipeline on the parity fixture.

---

## 4. Inputs and Assumptions

- Constructed with `map_keys` `(M, 2)` `(time, priogrid_gid)` and `map_vals` `(M,)` `country_id` covering every grid row.
- `reconcile(cm_frame, pgm_frame)`: a CM-level `PredictionFrame` (`country_id` units) and a PGM-level one (`priogrid_gid` units), **same** sample count `S` and **same** set of times. One target per call (multi-target = call per target).
- Time identifiers are opaque integers (`month_id`); country totals are authoritative.

---

## 5. Outputs and Side Effects

- Output: a new pgm `PredictionFrame` `(N, S)`, reconciled. **No** side effects (no I/O, no logging of data, no global state).
- **Memory ∝ frame size.** Grouping is `O(N log N)` (group-by-sort; register C-38), but the whole frame is held in memory at once — peak ≈ input + output ≈ `2·N·S·4` bytes. At global volume (`land` region) the **caller must chunk by time**: reconciliation is independent across months, so call `reconcile` per month-slice and write each result out rather than materialising the global frame. (C-38; verified on a global dry-run at S7, #39.)
- **Approximate where flagged:** for a draw in which *all* of a country's grid cells are zero, there are no proportions to distribute, so those cells stay zero and that draw's total is not conserved (the algorithm's documented edge case). Uncertainty is reconciled per-draw, which is a pragmatic approximation (C-37).

---

## 6. Failure Modes and Loudness

Raises `ValueError` (never silently degrades) when:
- `map_keys` is not `(M, 2)` or `map_vals` is not length `M` (constructor);
- a frame is at the wrong `SpatialLevel`;
- cm and pgm sample counts differ;
- cm and pgm cover different time steps;
- a grid row's `(time, priogrid_gid)` is absent from the mapping (raised by `cross_level_align`);
- a `(time, country)` group has no matching country forecast in `cm_frame`.

Aligns with ADR-003: ambiguity fails loud, before computation.

---

## 7. Boundaries and Interactions

- **Trusts:** the leaf `reconcile_proportional` (the math), `grouping.reconcile_pgm_to_cm` (the cross-level grouping/scatter), `validation` (the guards), `frames` (array↔frame I/O), and `views_frames` (`PredictionFrame`, `SpatioTemporalIndex`, `cross_level_align`).
- **Must not depend on:** pandas, torch, viewser, wandb, the unfao delivery code, or any geography source.
- The injected mapping is treated as opaque, caller-owned truth.

---

## 8. Examples of Correct Usage

```python
from views_postprocessing.reconciliation import ReconciliationModule

rm = ReconciliationModule(map_keys, map_vals)   # injected (time, pgid) -> country_id
reconciled_pgm = rm.reconcile(cm_frame, pgm_frame)   # one target; new frame
```

Multi-target: call `rm.reconcile(cm_t, pgm_t)` once per target.

---

## 9. Examples of Incorrect Usage

- Constructing it and expecting it to *derive* the country mapping (it never does — inject it).
- Passing a pgm frame where a cm frame is expected, or frames with different sample counts / times (raises, by design — do not pre-pad or coerce to silence it).
- Reusing it as a generic disaggregator for non-reconciliation tasks.

---

## 10. Test Alignment

- **Parity (gate):** `tests/test_reconciliation_e2e_parity.py` — the module reproduces the frozen oracle (`tests/fixtures/reconciliation_e2e_parity.npz`) bit-for-bit on every target.
- **Unit:** `tests/test_reconciliation_{frames,grouping,validation}.py` — adapters, grouping core, and each fail-loud guard.
- **Leaf parity:** `tests/test_reconciliation_parity.py` — `reconcile_proportional` vs the torch oracle.
- **Scale:** `tests/test_reconciliation_scale.py` — conservation holds across thousands of `(time, country)` groups (guards the group-by-sort logic; C-38).
- Regression-protected: bit-exact parity, zero-preservation, de-mutation, every `ValueError` guard, and grouping correctness at scale.

---

## 11. Evolution Notes

- **Stable:** the injected-mapping contract, the fail-loud guards, the de-mutated return.
- **Expected to change:** the *algorithm* — the principled probabilistic upgrade (**C-37**) will arrive as a sibling method behind this same interface (OCP); when it does, this contract's §2/§5 approximation notes must be revisited.
- The production mapping **source** (viewser-derived `country_id` vs the GAUL lookup) is decided at wiring time (S7, #39) and does not change this class's contract.

---

## End of Contract

This document defines the **intended meaning** of `ReconciliationModule`.

Changes to behavior that violate this intent are bugs.
Changes to intent must update this contract.
