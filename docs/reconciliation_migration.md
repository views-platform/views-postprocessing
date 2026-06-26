# Reconciliation — moved to views-frames

Forecast reconciliation **no longer lives in views-postprocessing.** It moved to the
`views_frames_reconcile` sibling in the views-frames mono-wheel — a frame→frame
operation belongs in the frames foundation, not bolted onto FAO delivery (which does
not use reconciliation).

- **Home:** `views_frames_reconcile` (views-frames ≥ 1.7.0) — Epic 11 /
  views-platform/views-frames#131, ADR-023. Parity-proven bit-identical to the copy
  that briefly lived here.
- **Consumer wiring:** views-models `reconciliation/reconciler_factory.py` (the ADR-014
  composition root) imports it directly — views-platform/views-models#191 (PR #202).
- **This repo:** vpp was only ever a way-station (epic #31); its copy was parity-proven
  (PR #30) and then retired here (#62). The pipeline-core port collapse and
  views-reporting retirement continue separately (pipeline-core#221, #40 / views-reporting#72).

Migration history is preserved in git and in the risk register (C-37, C-38, C-42).
