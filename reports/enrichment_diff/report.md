# Enrichment engine swap — what exactly changes (africa_me)

**Date:** 2026-06-18
**Comparison:** current runtime mapper (`mapping.py`, Natural Earth + GAUL shapefiles, sequential allocation) **vs** new lookup enricher (ADR-011, built from the views-datafactory v1.3.0 area-majority GAUL parquets).
**Scope:** all 13,110 `africa_me_legacy` PRIO-GRID cells, all 9 geographic metadata columns, run on the exact production shapefiles (git-lfs).
**Reproduce:** `PYTHONPATH=. python scripts/diff_enrichment.py` → `diff_cells.csv` + `summary.json`; `python scripts/plot_enrichment_diff.py` → `maps/`.

## Headline

| | cells | share |
|---|---:|---:|
| **Identical** (all 9 columns match) | 12,597 | **96.1%** |
| Changed | 512 | 3.9% |
| **Unexplained** | **0** | **0%** |

Every single differing cell falls into a known, expected class. There are no surprises and no regressions — the differences are the FAO-contracted area-majority rule arriving end-to-end.

## What changed, by class

| Class | Cells | What it means | Expected? |
|---|---:|---|---|
| `country_reassignment` | 259 | Cell assigned to a different **country**. The old mapper picks the country by Natural Earth area-majority, then fits GAUL admin *inside* that country (sequential). The new lookup takes country + admin together from the single GAUL polygon with the largest area in the cell. They disagree on border cells. | Yes — border cells of neighbouring/enclave countries |
| `admin_reallocation` | 247 | Same country, different **province/district** (admin1/admin2). Same root cause, one level down. | Yes — cells on internal admin borders |
| `dropped_by_land_gaul` | 4 | The old mapper assigned these (via Natural Earth's detailed coastline), but they have no GAUL land coverage, so the new `land_gaul` region excludes them. gids 62356 (Prince Edward Is.), 94776, 107733, 107742 (off Madagascar). | Yes — open-ocean cells FAO should not have been getting |
| `coastal_recovery` | 2 | The old mapper left these unmapped; the new lookup assigns them. gids 104839, 170255. | Yes — coastal cells the area-majority rule recovers |
| `both_unmapped` | 1 | Neither engine maps it (pure ocean). | Yes |
| `country_code_system` | 0 | Would be: same country, different ISO string (NE vs GAUL). **None occurred** — both use standard ISO-3166 alpha-3, so for the same country they agree. No naming-convention noise. | — |

`country_reassignment` + `admin_reallocation` = **506 genuine geographic differences** (3.9% of cells), all on borders. Plus 4 ocean cells dropped and 2 coastal cells recovered.

## Why these are correct, not bugs

The new engine implements area-majority from a single consistent boundary source (GAUL), which is FAO's contracted aggregation rule (Release Note 02). The old engine mixed two boundary datasets (Natural Earth for country, GAUL for admin) and constrained admin to the NE-chosen country. Where they differ, the **new** answer is the contractually-correct one. The verification maps show the differences land precisely on country and admin borders — e.g. the Lesotho and Eswatini enclave borders (`maps/04_zoom_lesotho_sa.png`), exactly where a tiny enclave's cells are split between two algorithms.

## Maps (`reports/enrichment_diff/maps/`)

| File | Shows |
|---|---|
| `01_agree_disagree.png` | All africa_me cells: identical (grey) vs changed (red) |
| `02_by_class.png` | Each cell coloured by difference class |
| `03_country_before_after.png` | Country assignment side-by-side: old (NE) vs new (GAUL) |
| `04_zoom_lesotho_sa.png` | Zoom: Lesotho / Eswatini / South Africa border reassignments |
| `05_zoom_namibia_botswana.png` | Zoom: Namibia / Botswana / South Africa / Mozambique borders |

## Bottom line

Swapping the enrichment engine changes the geography of **512 of 13,110 africa_me cells (3.9%)**, every one of them on a border or coastline, every one explained, with the new values being the area-majority answers FAO's contract specifies. Nothing is unexplained; nothing regresses. The remaining columns (coordinates, and 96.1% of all cells) are bit-for-bit identical.

For the global delivery, the same classes will appear at larger absolute counts (more borders), plus the 6 Azores supplement cells which are outside africa_me. This africa_me run is the exact, auditable baseline.
