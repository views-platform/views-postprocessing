"""Conformance proof: this repo's data satisfies the views-frames contract.

Phase 1 of the numpy/views-frames migration. Builds the repo's two kinds of
data as views-frames value objects via the ``unfao.frames`` adapters and runs
the published ``assert_frame_contract`` against each:

    forecasts (pred_ln_*) -> PredictionFrame  (N, 1)
    actuals   (ged_*)     -> TargetFrame       (N, 1)

This makes views-postprocessing the first live cross-repo consumer of the
frozen views-frames 1.0 contract. Offline and synthetic — no zarr, no Appwrite,
no network. ``assert_frame_contract`` checks the structural invariants
(float32, explicit trailing axis, integer identifiers of length N) and a
save/load round-trip; it raises on any violation.
"""

import numpy as np
import pandas as pd
import pytest

from views_frames import PredictionFrame, TargetFrame
from views_frames.conformance import assert_frame_contract

from views_postprocessing.unfao.frames import to_prediction_frame, to_target_frame

_TIME_ID = "month_id"
_PG_ID = "priogrid_gid"


def _frame(months=(100, 101), gids=(1, 2, 3)):
    """Synthetic (month_id, priogrid_gid)-indexed frame with a pred and a ged column."""
    rows = [(m, g) for m in months for g in gids]
    idx = pd.MultiIndex.from_tuples(rows, names=[_TIME_ID, _PG_ID])
    rng = np.random.default_rng(0)
    return pd.DataFrame(
        {
            "pred_ln_sb_best": rng.gamma(2.0, 1.0, size=len(rows)),
            "lr_ged_sb": rng.integers(0, 50, size=len(rows)),
        },
        index=idx,
    )


class TestPredictionFrameConformance:
    def test_satisfies_frame_contract(self):
        pf = to_prediction_frame(_frame(), "pred_ln_sb_best")
        assert_frame_contract(pf)  # raises on any violation (incl. round-trip)

    def test_shape_and_sample_axis(self):
        df = _frame()
        pf = to_prediction_frame(df, "pred_ln_sb_best")
        assert isinstance(pf, PredictionFrame)
        assert pf.n_rows == len(df)
        assert pf.sample_count == 1  # scalar point predictions -> explicit S=1
        assert pf.is_sample is False
        assert pf.values.dtype == np.float32

    def test_identifiers_match_our_index_flat_columns(self):
        df = _frame().reset_index()  # also exercise the reset_index() column path
        pf = to_prediction_frame(df, "pred_ln_sb_best")
        np.testing.assert_array_equal(pf.index.time, df[_TIME_ID].to_numpy())
        np.testing.assert_array_equal(pf.index.unit, df[_PG_ID].to_numpy())

    def test_values_come_from_the_named_column(self):
        # Guards against wiring the wrong column: values must equal the source.
        df = _frame()
        pf = to_prediction_frame(df, "pred_ln_sb_best")
        np.testing.assert_array_equal(
            pf.values[:, 0], df["pred_ln_sb_best"].to_numpy().astype(np.float32)
        )


class TestTargetFrameConformance:
    def test_satisfies_frame_contract(self):
        tf = to_target_frame(_frame(), "lr_ged_sb")
        assert_frame_contract(tf)

    def test_observed_actuals_shape(self):
        df = _frame()
        tf = to_target_frame(df, "lr_ged_sb")
        assert isinstance(tf, TargetFrame)
        assert tf.n_rows == len(df)
        assert tf.values.shape == (len(df), 1)
        assert tf.sample_count == 1
        assert tf.is_sample is False


class TestAdapterGuards:
    def test_missing_value_column_raises(self):
        with pytest.raises(ValueError, match="not found"):
            to_prediction_frame(_frame(), "does_not_exist")

    def test_missing_identifiers_raise(self):
        df = pd.DataFrame({"pred_ln_sb_best": [1.0, 2.0]})  # no month_id/priogrid_gid
        with pytest.raises(ValueError, match="month_id"):
            to_prediction_frame(df, "pred_ln_sb_best")
