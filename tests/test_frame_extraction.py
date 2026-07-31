"""Tests for the representation seam (`unfao/frame_extraction.py`).

**These were parity tests until #151.** They proved that the same data expressed as a
pandas MultiIndex frame and as a views-frames `PredictionFrame` yielded *identical*
primitives through the two seams — the golden-equivalence proof the migration relied
on, and exactly the right test while both existed.

The pandas seam was retired in #151 (unreachable since #149 retired the pandas
delivery), so parity now has nothing to compare against. What the parity assertions
were really pinning — the **absolute** primitives the seam must return — was already
written into them, so it is asserted directly here. Nothing was weakened: the
expected values are unchanged, they simply no longer route through a deleted module
to be checked.

The frame is deliberately built with **unsorted rows**, because the invariants
downstream assume `months_of` returns ascending int64 regardless of input order.
"""

import numpy as np

from views_postprocessing.unfao import frame_extraction
from views_postprocessing.unfao.frames import build_prediction_frame

# 3 cells × 2 months, rows deliberately unsorted.
_ROWS = [(101, 3), (100, 1), (100, 2), (101, 1), (100, 3), (101, 2)]
_TIME = np.array([t for t, _ in _ROWS], dtype=np.int64)
_UNIT = np.array([u for _, u in _ROWS], dtype=np.int64)


def _prediction_frame():
    return build_prediction_frame(np.zeros((len(_ROWS), 1), dtype=np.float32), _TIME, _UNIT)


def test_cells_of_returns_the_distinct_gids():
    assert frame_extraction.cells_of(_prediction_frame()) == {1, 2, 3}


def test_months_of_returns_distinct_months_from_unsorted_rows():
    np.testing.assert_array_equal(
        frame_extraction.months_of(_prediction_frame()), np.array([100, 101])
    )


def test_months_of_is_int64_ascending():
    pf = _prediction_frame()
    out = frame_extraction.months_of(pf)
    assert out.dtype == np.int64
    assert list(out) == sorted(out)


def test_drop_units_removes_only_declared_cells():
    import numpy as np

    from views_postprocessing.unfao.frame_extraction import drop_units
    from views_postprocessing.unfao.frames import build_prediction_frame

    values = np.arange(12, dtype=np.float32).reshape(6, 2)
    time = np.full(6, 543, dtype=np.int64)
    unit = np.array([1, 2, 3, 4, 5, 6], dtype=np.int64)
    frame = build_prediction_frame(values, time, unit)

    curated = drop_units(frame, frozenset({2, 5}))
    assert list(np.asarray(curated.index.unit)) == [1, 3, 4, 6]
    np.testing.assert_array_equal(curated.values, values[[0, 2, 3, 5]])
    # rows survive intact and aligned; empty exclusion is the identity
    assert drop_units(frame, frozenset()) is frame
    # excluded cells absent from the frame are a no-op, not an error (declared
    # exclusions describe the region, not this payload)
    assert drop_units(frame, frozenset({99})).n_rows == 6
