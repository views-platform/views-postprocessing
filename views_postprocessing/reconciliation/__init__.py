"""Forecast reconciliation (pgm forecasts reconciled to cm totals).

Slice 1 ports the top-down proportional method from views-reporting as a pure
numpy function. New methods (e.g. principled probabilistic reconciliation, C-37)
should be added as sibling modules, not by modifying ``proportional``.
"""

from views_postprocessing.reconciliation.proportional import reconcile_proportional

__all__ = ["reconcile_proportional"]
