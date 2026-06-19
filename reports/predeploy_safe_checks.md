# Pre-deploy safe checks (read-only)

Date: 2026-06-18. These only read files. No code changed.

| # | Check | Result |
|---|-------|--------|
| 1 | Lookup data clean — 64,742 cells, no nulls, no bad codes, coordinates in range | **PASS** |
| 2 | Disputed places labeled (see below) | **PASS** (for review) |
| 3 | New code runs without the heavy map library (geopandas) | **PASS** |
| 4 | A delivery is traceable to a lookup version | **PARTIAL** |

## Check 2 — how GAUL labels sensitive places (for your eyes before FAO's)

| Place | ISO code in data | GAUL name | Cells |
|-------|------------------|-----------|-------|
| Jammu & Kashmir | `xJK` | Jammu And Kashmir | 75 |
| Arunachal Pradesh | `xAP` | Arunachal Pradesh | 23 |
| Aksai Chin | `xAC` | Aksai Chin | 11 |
| Taiwan | `TWN` | "Taiwan Province of China" | 23 |
| Palestine | `PSE` | Palestine | 3 |
| Western Sahara | `ESH` | Western Sahara | 101 |
| Somaliland area | `SOM` | Somalia (the old "-99" is gone) | 234 |
| Crimea | — | not present in the lookup region | 0 |

Non-standard `x*` ISO codes present: `xAB, xAC, xAP, xHT, xIT, xJK, xMS` (GAUL's codes for 7 disputed zones with no official ISO code).

## Check 4 — the partial

The lookup file itself is stamped with its version (region + source digests). But when a delivery is uploaded to FAO, the description only says a generic "ADR-011 lookup" — not the exact version. So today you can trace a delivery to "the lookup", but not to "this exact lookup build". Small gap; fixable later.
