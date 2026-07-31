"""Conformance + parity tests for the views-frames constructors (`unfao/frames.py`).

`build_prediction_frame` / `build_target_frame` take **declared primitives** — a 2-D
`(N, S)` value array + `(time, unit)` arrays — and build a views-frames value object. These
tests prove (1) the constructors carry the declared values faithfully (the parity oracle:
build primitives → construct → assert arrays equal), (2) the result satisfies the published
`assert_frame_contract`, and (3) the constructors **fail loud** rather than infer/reshape
when the declared shape is wrong.

No pandas: the pandas→primitives unpacking lives in the extraction seam (a separate story);
this module only exercises the primitives→frame boundary.
"""

import numpy as np
import pytest

from views_frames import PredictionFrame, TargetFrame
from views_frames.conformance import assert_frame_contract

from views_postprocessing.contract.frames import build_prediction_frame, build_target_frame

# Declared identifiers for a small PGM block: 3 cells across 2 months (N = 6).
_TIME = np.array([100, 100, 100, 101, 101, 101], dtype=np.int64)
_UNIT = np.array([1, 2, 3, 1, 2, 3], dtype=np.int64)
_N = _TIME.shape[0]


class TestPredictionFramePoint:
    def test_point_is_single_sample(self):
        values = np.arange(_N, dtype=np.float32).reshape(_N, 1)  # declared (N, 1)
        pf = build_prediction_frame(values, _TIME, _UNIT)
        assert isinstance(pf, PredictionFrame)
        assert pf.sample_count == 1
        assert pf.is_sample is False
        assert_frame_contract(pf)

    def test_point_values_carried_faithfully(self):
        values = np.array([[0.0], [1.5], [2.5], [3.5], [4.5], [5.5]], dtype=np.float32)
        pf = build_prediction_frame(values, _TIME, _UNIT)
        np.testing.assert_array_equal(pf.values, values)


class TestPredictionFrameSamples:
    def test_samples_carry_the_full_NxS_array(self):
        S = 5
        rng = np.random.default_rng(0)
        values = rng.gamma(2.0, size=(_N, S)).astype(np.float32)  # declared (N, S)
        pf = build_prediction_frame(values, _TIME, _UNIT)
        assert pf.sample_count == S
        assert pf.is_sample is True
        np.testing.assert_array_equal(pf.values, values)  # parity: no collapse, no reshape
        assert_frame_contract(pf)

    def test_identifiers_match_declared_arrays(self):
        values = np.zeros((_N, 3), dtype=np.float32)
        pf = build_prediction_frame(values, _TIME, _UNIT)
        np.testing.assert_array_equal(pf.index.time, _TIME)
        np.testing.assert_array_equal(pf.index.unit, _UNIT)


class TestTargetFrame:
    def test_target_is_single_valued(self):
        values = np.arange(_N, dtype=np.float32).reshape(_N, 1)
        tf = build_target_frame(values, _TIME, _UNIT)
        assert isinstance(tf, TargetFrame)
        assert tf.sample_count == 1
        np.testing.assert_array_equal(tf.values, values)
        assert_frame_contract(tf)


class TestFailLoudNotInfer:
    """The constructors declare-and-assert; they never reshape/stack/guess."""

    def test_1d_values_raise_not_reshaped(self):
        with pytest.raises(ValueError):
            build_prediction_frame(np.arange(_N, dtype=np.float32), _TIME, _UNIT)

    def test_object_dtype_cells_raise_not_stacked(self):
        # an object-dtype column of per-cell arrays is NOT silently stacked into (N, S)
        cells = np.empty(_N, dtype=object)
        for i in range(_N):
            cells[i] = np.array([float(i), float(i)], dtype=np.float32)
        with pytest.raises((ValueError, TypeError)):
            build_prediction_frame(cells, _TIME, _UNIT)

    def test_target_with_sample_axis_raises(self):
        with pytest.raises(ValueError):
            build_target_frame(np.zeros((_N, 2), dtype=np.float32), _TIME, _UNIT)

    def test_row_count_mismatch_raises(self):
        values = np.zeros((_N + 1, 1), dtype=np.float32)
        with pytest.raises(ValueError):
            build_prediction_frame(values, _TIME, _UNIT)
