# Cells excluded from FAO global delivery

**Status:** disclosure note for the `land_gaul` global rollout (register C-30 / D-10, sprint S4 / #55).
**Source of truth:** views-datafactory v1.4.0 — `land_gaul` curated region (`land − land_gaul`).
**Pinned in code:** `views_postprocessing/delivery/coverage.py` (`EXCLUDED_GIDS_BY_REGION["land_gaul"]`).

## What FAO should know

The VIEWS global historical delivery covers the `land_gaul` region: **64,742** PRIO-GRID
cells — every land cell for which FAO's **GAUL 2024** boundaries provide an administrative
assignment.

**76 land cells are deliberately excluded.** They are remote sub-Antarctic islands that
fall outside GAUL 2024 coverage (e.g. Macquarie Island, the Auckland Islands, Prince
Edward Islands, South Sandwich Islands). They have **no** country/admin assignment in any
source, so they are dropped at the region level rather than shipped with a placeholder —
shipping them would attribute partner rows to a non-country (`-1`). Conflict activity in
these cells is negligible to nil.

This is the full, frozen exclusion list. If a future delivery's coverage changes, the
frozen list in code diverges loudly (it is asserted in `tests/test_delivery_coverage.py`
against the producer), so any drift is caught before delivery rather than silently
absorbed.

## History

The exclusion count was **82** when `land_gaul` was first curated (datafactory #159).
It dropped to **76** when datafactory #163 (ADR-043) supplemented **6 Azorean cells**
(gids 182470, 183190, 183909, 183910, 186058, 186778) into `land_gaul` — those are now
**covered and delivered**, not excluded.

## The 76 excluded gids

```
 51078  51798  53979  54699  56852  56853  58318  62356
 94776  99027 107733 107742 110367 112944 114769 116931
118753 121625 123748 124038 124425 124759 126561 126624
128012 129079 129387 129574 130919 131639 132525 146125
153966 157829 159987 160708 173423 179900 190724 201850
202249 203404 206592 208007 210596 212353 212774 221061
223941 225390 227961 229161 229429 229430 229866 233436
233743 234640 235586 235942 235943 235951 235954 236054
237351 238123 238231 238954 239705 240318 240319 240975
240977 241153 247862 248595
```
