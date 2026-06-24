# Reconciliation migration — notes & decisions

Tracks the migration of forecast reconciliation from views-reporting into this
repo. Epic: **#31**; tracking checklist: **#41**; origin: **#3** / views-reporting#72.
Story S6 (#38) formalises this into the `ReconciliationModule` CIC.

## Status

- **Slice 1 (PR #30) — done.** Leaf algorithm `reconcile_proportional`
  (`views_postprocessing/reconciliation/proportional.py`), pure numpy, **bit-exact**
  parity vs the views-reporting torch oracle (`tests/test_reconciliation_parity.py`).
- **S0 (#32) — done.** End-to-end oracle fixture captured offline
  (`tests/fixtures/reconciliation_e2e_parity.npz`, via
  `scripts/gen_reconciliation_e2e_fixture.py`). Decisions below.
- **S1–S5 (#33–#37) — done.** The frames-native module is complete and
  **end-to-end parity-proven**: `cm/pgm` adapters (`reconciliation/frames.py`),
  the `cross_level_align` grouping core (`reconciliation/grouping.py`), fail-loud
  validation (`reconciliation/validation.py`), and the public
  `ReconciliationModule` (`reconciliation/module.py`) — which reproduces the
  frozen views-reporting pipeline **bit-for-bit** on every target
  (`tests/test_reconciliation_e2e_parity.py`). No torch / pandas / viewser / wandb.
- **S6 (#38) — done.** CIC at `docs/CICs/ReconciliationModule.md`.
- **In-repo migration complete.** Remaining: S7 (#39) pipeline-core repoint and
  S8 (#40) views-reporting phase-out — both cross-repo, **blocked** on this
  landing; and the principled-algorithm upgrade (**C-37**), a separate epic.

## D-R1 — Group by injected VIEWS `country_id`, not GAUL (for parity)

The frozen oracle groups grid cells by **VIEWS `country_id`** (from viewser's
`country_month` LOA). This repo's GAUL lookup (`data/gaul_lookup.parquet`) numbers
countries by **`admin1_gaul0_code`** — a *different* id system. The migration is
**parity-preserving**, so the frames-native module groups by the **same VIEWS
`country_id`**, **injected** by the caller (the leaf never embeds geography —
views-frames ADR-014). The fixture bypasses viewser by pre-setting
`pg_ds._country_to_grids_cache`.

> **Deferred (S7, #39):** whether the *production* mapping should eventually come
> from our GAUL lookup instead of viewser is a separate decision, taken at wiring
> time. It does **not** affect parity and is out of scope until the migration is
> wired and proven.

## D-R2 — The fixture deliberately includes the all-zero-country-draw edge case

When *every* grid cell of a country is zero for a posterior draw, proportional
scaling has no proportions to distribute, so the oracle leaves those cells **zero**
(country total not conserved for that draw — the algorithm's documented edge case).
The S0 fixture's sparsity (~30% zeros, small countries) produces such draws
(178 across the battery), captured verbatim. The frames-native module must
**reproduce this behaviour** (parity, not "correctness"); improving it belongs to
the principled-reconciliation upgrade (**C-37**), not this migration.

## Parity oracle (how the fixture is made)

`scripts/gen_reconciliation_e2e_fixture.py` builds a realistic cm + pgm sample
(5 countries of varying size, 3 months, 2 targets, 100 samples), injects the
`country_id` mapping, runs the **untouched** views-reporting `ReconciliationModule`
on CPU with WandB patched out, and freezes `(cm, pg, pg_country, recon)` to npz.
It needs pipeline-core + views-reporting + torch **only at generation time** (the
`views_pipeline` conda env); the committed fixture is consumed offline (numpy only),
so CI needs none of them.
