"""Unit tests for the representation-free observed-range invariant (S2 / C-26)."""

import numpy as np

from views_postprocessing.delivery.observed_range import fabricated_months, is_observed


def test_fabricated_months_returns_months_beyond_boundary():
    out = fabricated_months(np.array([100, 101, 102, 103]), last_valid_month_id=101)
    np.testing.assert_array_equal(out, np.array([102, 103]))


def test_fabricated_months_empty_when_all_observed():
    out = fabricated_months(np.array([98, 99, 100]), last_valid_month_id=100)
    assert out.size == 0


def test_fabricated_months_distinct_and_sorted():
    out = fabricated_months(np.array([105, 102, 105, 103, 102]), last_valid_month_id=101)
    np.testing.assert_array_equal(out, np.array([102, 103, 105]))


def test_is_observed_boundary_is_inclusive():
    assert is_observed(100, 100) is True
    assert is_observed(101, 100) is False
    assert is_observed(50, 100) is True
