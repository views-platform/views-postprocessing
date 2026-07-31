"""Partner-neutral delivery machinery — everything a delivery needs that is not FAO.

The repository has three top-level packages and they answer three different questions:

    delivery/    what makes a delivery VALID   — representation-free invariants
    contract/    how a delivery is BUILT       — this package
    unfao/       who a delivery is FOR         — one partner's product and manager

**Why this package exists (register C-69, #153).** Until now ~800 of `unfao/`'s
1,001 lines were partner-neutral: the whole ADR-013 wire, the frame seam, the GAUL
asset, the artifact builders. A clone — views-crafdapi, views-productionapi — had to
import `views_postprocessing.contract.wire` to get a wire contract that has nothing to
do with FAO, or fork it and start a third copy. That is the CRP violation (things not
reused together forced together) and it was the last structural blocker to cloning.

`delivery/` already had this right: its docstring says *"Partner-agnostic: FAO and the
coming UN-agency deliveries reuse these"* and nothing in it names FAO. This package
extends that property to the machinery.

**Nothing here may import `unfao`.** That is the whole point, and it is enforced
mechanically rather than by convention — see `tests/test_clone_readiness.py` (#155).

What a clone supplies for itself: its product declarations, its store coordinates,
and its manager. See `docs/CLONING.md`.
"""
