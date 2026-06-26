"""Unit tests for the representation-free coverage invariant (S1 / C-34).

Pure primitives in, raise-or-pass out — no framework, no pandas.
"""

import pytest

from views_postprocessing.delivery.coverage import (
    EXPECTED_CELLS,
    CoverageError,
    assert_complete_coverage,
    expected_for,
)


def test_correct_count_passes():
    assert assert_complete_coverage({1, 2, 3}, 3) is None


def test_under_coverage_raises():
    with pytest.raises(CoverageError, match="under-coverage"):
        assert_complete_coverage({1, 2}, 3)


def test_over_coverage_raises():
    with pytest.raises(CoverageError, match="over-coverage"):
        assert_complete_coverage({1, 2, 3, 4}, 3)


def test_label_appears_in_message():
    with pytest.raises(CoverageError, match="forecast"):
        assert_complete_coverage(set(), 1, label="forecast")


def test_land_gaul_is_pinned():
    assert expected_for("land_gaul") == 64_736
    assert EXPECTED_CELLS["land_gaul"] == 64_736


def test_unpinned_or_missing_region_is_none():
    # africa_me_legacy is deliberately unpinned (ambiguous count); None must not raise.
    assert expected_for("africa_me_legacy") is None
    assert expected_for(None) is None
    assert expected_for("does_not_exist") is None
