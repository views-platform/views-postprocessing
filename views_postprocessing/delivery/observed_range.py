"""Observed-range invariant: a delivery of *observed* history must not ship months
the producer has not actually observed (register C-26, S2).

Representation-free — primitives only (a month array + a scalar boundary). The
boundary (``last_valid_month_id``) is a **producer** fact, read from views-datafactory
(see ``views_postprocessing/unfao/source_metadata.py``); this module only decides which
months are fabricated, never how to fetch or filter them.

Why this matters: the historical request runs to the current calendar month, but UCDP
data ends earlier (reporting lag). The tail months come back as zero-padding and would
ship to the partner as "zero conflict" — fabricated. Months at or below the boundary
are observed; months above it are padding and must be dropped before delivery.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def fabricated_months(months: NDArray, last_valid_month_id: int) -> NDArray[np.int64]:
    """The distinct months strictly beyond the producer's last observed month.

    These carry no observed data (zero-padding) and must not ship as observed history.
    """
    m = np.asarray(months, dtype=np.int64)
    return np.unique(m[m > int(last_valid_month_id)])


def is_observed(month: int, last_valid_month_id: int) -> bool:
    """Whether ``month`` is at or below the producer's last observed month."""
    return int(month) <= int(last_valid_month_id)
