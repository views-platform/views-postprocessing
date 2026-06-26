"""Unit tests for the pandas->primitives extraction seam (unfao/extraction.py)."""

import numpy as np
import pandas as pd

from views_postprocessing.unfao import extraction


def _frame(rows):
    """rows: list of (month_id, priogrid_gid)."""
    idx = pd.MultiIndex.from_tuples(rows, names=["month_id", "priogrid_gid"])
    return pd.DataFrame({"lr_ged_sb": np.zeros(len(rows))}, index=idx)


def test_cells_of_returns_distinct_gids():
    df = _frame([(100, 1), (100, 2), (101, 1), (101, 2), (101, 3)])
    assert extraction.cells_of(df) == {1, 2, 3}


def test_months_of_returns_distinct_sorted_months():
    df = _frame([(101, 1), (100, 1), (100, 2), (102, 1)])
    np.testing.assert_array_equal(extraction.months_of(df), np.array([100, 101, 102]))


def test_drop_months_above_removes_padding_rows():
    df = _frame([(100, 1), (101, 1), (102, 1), (103, 1)])
    clipped = extraction.drop_months_above(df, last_valid_month_id=101)
    np.testing.assert_array_equal(extraction.months_of(clipped), np.array([100, 101]))
    assert len(clipped) == 2


def test_works_on_flat_columns_too():
    df = pd.DataFrame({"month_id": [100, 100, 101], "priogrid_gid": [1, 2, 1]})
    assert extraction.cells_of(df) == {1, 2}
    np.testing.assert_array_equal(extraction.months_of(df), np.array([100, 101]))
