"""``views_postprocessing.delivery`` — representation-free delivery-integrity invariants.

Partner-agnostic: FAO and the coming UN-agency deliveries reuse these. Every module
in this package operates on **primitives only** (sets of ints, numpy arrays, scalars,
dicts) and **must not import pandas or views_frames** — the representation seam lives
in ``views_postprocessing/unfao/extraction.py``.

Invariants here are **called by** delivery managers, **never inherited into** them
(see the epic design contract, views-postprocessing#51). The manager's pattern is
``extract → call invariant → raise``; this package owns the *rule*, the extraction
module owns the *representation*, and the two never share a file.
"""
