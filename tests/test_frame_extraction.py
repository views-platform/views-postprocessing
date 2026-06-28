"""Parity tests for the frame-native seam (`unfao/frame_extraction.py`).

The golden-equivalence proof the migration relies on: the same data expressed *both* as the
manager's pandas MultiIndex frame and as a views-frames `PredictionFrame` must yield
**identical primitives** through the two seams (`extraction` vs `frame_extraction`), so the
representation-free `delivery/` invariants behave the same on either.
"""

import numpy as np
import pandas as pd

from views_postprocessing.unfao import extraction, frame_extraction
from views_postprocessing.unfao.frames import build_prediction_frame

# One dataset, two representations: 3 cells × 2 months (rows deliberately unsorted).
_ROWS = [(101, 3), (100, 1), (100, 2), (101, 1), (100, 3), (101, 2)]
_TIME = np.array([t for t, _ in _ROWS], dtype=np.int64)
_UNIT = np.array([u for _, u in _ROWS], dtype=np.int64)


def _pandas_frame() -> pd.DataFrame:
    idx = pd.MultiIndex.from_tuples(_ROWS, names=["month_id", "priogrid_gid"])
    return pd.DataFrame({"pred_ln_sb_best": np.zeros(len(_ROWS))}, index=idx)


def _prediction_frame():
    return build_prediction_frame(np.zeros((len(_ROWS), 1), dtype=np.float32), _TIME, _UNIT)


def test_cells_of_parity():
    df, pf = _pandas_frame(), _prediction_frame()
    assert frame_extraction.cells_of(pf) == extraction.cells_of(df) == {1, 2, 3}


def test_months_of_parity():
    df, pf = _pandas_frame(), _prediction_frame()
    np.testing.assert_array_equal(
        frame_extraction.months_of(pf), extraction.months_of(df)
    )
    np.testing.assert_array_equal(frame_extraction.months_of(pf), np.array([100, 101]))


def test_months_of_is_int64_ascending():
    pf = _prediction_frame()
    out = frame_extraction.months_of(pf)
    assert out.dtype == np.int64
    assert list(out) == sorted(out)
