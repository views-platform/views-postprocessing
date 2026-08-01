# enrichment_diff — committed evidence artifacts

These files are **deliberately committed** generated artifacts: they are the
auditable account of exactly what changes when the enrichment engine is swapped
(ADR-011), required for the FAO accountability conversation. They are evidence,
not build output that is consumed by code.

| File | What it is | Regenerate with |
|------|-----------|-----------------|
| `report.md` | Human-readable summary + disputed-territory analysis | (hand-written) |
| `summary.json` | Per-class difference counts | `scripts/diff_enrichment.py` |
| `diff_cells.csv` | Per-cell, per-column old-vs-new record (13,110 rows) | `scripts/diff_enrichment.py` |
| `maps/*.png` | The 5 verification maps | `scripts/plot_enrichment_diff.py` |

To regenerate (needs the real shapefiles via `git lfs pull` and a local
views-datafactory checkout; set `$VIEWS_DATAFACTORY` if it is not the sibling
directory):

```bash
PYTHONPATH=. python scripts/diff_enrichment.py
PYTHONPATH=. python scripts/plot_enrichment_diff.py
```

If these are ever regenerated for a different region or GAUL version, replace
the whole directory so the report, counts, CSV, and maps stay mutually
consistent.
