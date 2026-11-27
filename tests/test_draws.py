"""Unit tests for the no-collapse invariant (ADR-013 §6 / views-models#149 / #45).

Pure primitives in, raise-or-pass out — no framework, no pandas.
"""

import numpy as np
import pytest

from views_postprocessing.delivery.draws import (
    DrawsCollapseError,
    assert_draws_uncollapsed,
)


def _draws(n=6, s=8, seed=0):
    """A genuine sampled payload: (n, s) with real per-row variance."""
    return np.random.default_rng(seed).gamma(2.0, size=(n, s)).astype(np.float32)


def test_genuine_draws_pass():
    values = _draws()
    assert assert_draws_uncollapsed(values, 8, s_min=2) is None


def test_pgm_zero_inflation_is_legal():
    # The key non-rule: most rows constant (zero-conflict cells), ONE row varied → pass.
    values = np.zeros((100, 8), dtype=np.float32)
    values[42] = np.arange(8)
    assert assert_draws_uncollapsed(values, 8, s_min=2) is None


def test_collapsed_1d_payload_raises():
    with pytest.raises(DrawsCollapseError, match="2-D"):
        assert_draws_uncollapsed(np.zeros(10), 8, s_min=2)


def test_3d_payload_raises():
    with pytest.raises(DrawsCollapseError, match="2-D"):
        assert_draws_uncollapsed(np.zeros((4, 3, 8)), 8, s_min=2)


def test_header_payload_mismatch_raises_naming_both():
    with pytest.raises(DrawsCollapseError) as exc:
        assert_draws_uncollapsed(_draws(s=8), 1024, s_min=2)
    msg = str(exc.value)
    assert "1024" in msg  # declared
    assert "S=8" in msg  # found


def test_below_s_min_floor_raises():
    # A conformant-but-thin payload below the delivery floor must not ship.
    with pytest.raises(DrawsCollapseError, match="s_min"):
        assert_draws_uncollapsed(_draws(s=2), 2, s_min=4)


def test_skeleton_floor_is_two():
    # The walking-skeleton configuration: S=2, s_min=2 passes.
    values = np.column_stack([np.zeros(5), np.ones(5)]).astype(np.float32)
    assert assert_draws_uncollapsed(values, 2, s_min=2) is None


def test_fully_degenerate_payload_raises():
    # Every row constant across draws = a collapsed forecast wearing a sampled header.
    values = np.tile(np.arange(6, dtype=np.float32).reshape(-1, 1), (1, 8))
    with pytest.raises(DrawsCollapseError, match="draw-degenerate"):
        assert_draws_uncollapsed(values, 8, s_min=2)


def test_nan_rows_count_as_varied_documented_behavior():
    # Documented: NaN compares unequal to everything, so a NaN row is "varied" here —
    # NaN payloads are the null gates' job, not this invariant's.
    values = np.zeros((3, 4), dtype=np.float32)
    values[1, 2] = np.nan
    assert assert_draws_uncollapsed(values, 4, s_min=2) is None


def test_label_appears_in_message():
    with pytest.raises(DrawsCollapseError, match="second-store"):
        assert_draws_uncollapsed(np.zeros(3), 8, s_min=2, label="second-store")


def test_an_empty_payload_is_refused_as_empty_and_not_as_collapsed():
    """0 rows is not a collapse, and saying so sent readers to the wrong place.

    `np.any(arr != arr[:, :1], axis=1).any()` over zero rows is False, so the
    degeneracy branch fired and reported "every one of the 0 rows is
    draw-degenerate (all 8 draws identical per row)" — vacuously true. It pointed
    the reader at the summarizer and the ADR-013 §6 contract when the real fault was
    a target that resolved to no rows, which would have delivered zero cells to a
    partner. Found by `/code-review max`, 2026-11-12.
    """
    with pytest.raises(DrawsCollapseError, match="0 rows") as excinfo:
        assert_draws_uncollapsed(np.zeros((0, 8), dtype="float32"), 8, s_min=2)
    # The old message is the thing under test: it must not come back.
    assert "degenerate" not in str(excinfo.value)


def test_input_that_is_not_an_array_at_all_is_refused_as_malformed():
    """Ragged input raised numpy's bare ValueError, which reads as a §6 verdict.

    `DrawsCollapseError` subclasses `ValueError`, so a caller catching the narrow
    type missed this entirely while a caller catching `ValueError` blamed the policy
    gate for malformed input. Nothing about the draws has been checked at that point.
    """
    with pytest.raises(DrawsCollapseError, match="could not be read as an array"):
        assert_draws_uncollapsed([[1, 2], [3]], 2, s_min=2)
