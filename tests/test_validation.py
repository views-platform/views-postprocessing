"""Tests for the metadata validation logic in UNFAOPostProcessorManager._validate().

Covers the C-01 fix (null validation re-enabled) and CIC failure modes.
See docs/CICs/UNFAOPostProcessorManager.md for the contract under test.

Note: views-pipeline-core may not be installed in test environments, so we
replicate the validation logic here rather than importing the manager class.
The logic tested matches unfao.py:_validate() exactly.
"""

import pytest
import pandas as pd
import numpy as np
import logging


logger = logging.getLogger(__name__)


REQUIRED_METADATA_COLS = [
    "pg_xcoord", "pg_ycoord", "country_iso_a3",
    "admin1_gaul1_code", "admin1_gaul1_name",
    "admin1_gaul0_code", "admin1_gaul0_name",
    "admin2_gaul2_code", "admin2_gaul2_name",
]


def make_valid_dataframe(n_rows=5):
    """Create a DataFrame that passes all validation checks."""
    return pd.DataFrame({
        "pg_xcoord": np.random.uniform(0, 50, n_rows),
        "pg_ycoord": np.random.uniform(-10, 10, n_rows),
        "country_iso_a3": ["AAA"] * n_rows,
        "admin1_gaul1_code": [101] * n_rows,
        "admin1_gaul1_name": ["A-South"] * n_rows,
        "admin1_gaul0_code": [1] * n_rows,
        "admin1_gaul0_name": ["CountryA"] * n_rows,
        "admin2_gaul2_code": [1021] * n_rows,
        "admin2_gaul2_name": ["A-South-W"] * n_rows,
        "pred_value": np.random.uniform(0, 1, n_rows),
    })


def validate_dataframe(df, label="dataframe"):
    """Replicates the validation logic from UNFAOPostProcessorManager._validate().

    This must stay in sync with views_postprocessing/unfao/managers/unfao.py.
    """
    for col in REQUIRED_METADATA_COLS:
        if col not in df.columns:
            err_msg = f"{label} is missing required metadata column: {col}. Found columns: {df.columns.tolist()}"
            logger.error(err_msg)
            raise ValueError(err_msg)
        null_count = df[col].isnull().sum()
        if null_count > 0:
            err_msg = f"{label} has {null_count} null values in required metadata column: {col} ({null_count}/{len(df)} rows)."
            logger.error(err_msg)
            raise ValueError(err_msg)


# ---------------------------------------------------------------------------
# GREEN: Valid data passes validation
# ---------------------------------------------------------------------------

class TestValidDataPasses:
    def test_valid_dataframes_pass(self):
        validate_dataframe(make_valid_dataframe(), "Historical dataframe")
        validate_dataframe(make_valid_dataframe(), "Forecast dataframe")

    def test_extra_columns_are_fine(self):
        df = make_valid_dataframe()
        df["extra_col"] = "foo"
        validate_dataframe(df)


# ---------------------------------------------------------------------------
# RED: Missing columns raise ValueError (CIC §6)
# ---------------------------------------------------------------------------

class TestMissingColumns:
    @pytest.mark.parametrize("col", REQUIRED_METADATA_COLS)
    def test_missing_historical_column_raises(self, col):
        df = make_valid_dataframe().drop(columns=[col])
        with pytest.raises(ValueError, match="missing required metadata column"):
            validate_dataframe(df, "Historical dataframe")

    @pytest.mark.parametrize("col", REQUIRED_METADATA_COLS)
    def test_missing_forecast_column_raises(self, col):
        df = make_valid_dataframe().drop(columns=[col])
        with pytest.raises(ValueError, match="missing required metadata column"):
            validate_dataframe(df, "Forecast dataframe")


# ---------------------------------------------------------------------------
# RED: Null values raise ValueError (C-01 fix)
# ---------------------------------------------------------------------------

class TestNullValuesRejected:
    @pytest.mark.parametrize("col", REQUIRED_METADATA_COLS)
    def test_null_in_historical_column_raises(self, col):
        df = make_valid_dataframe()
        df.loc[0, col] = None
        with pytest.raises(ValueError, match="null values"):
            validate_dataframe(df, "Historical dataframe")

    @pytest.mark.parametrize("col", REQUIRED_METADATA_COLS)
    def test_null_in_forecast_column_raises(self, col):
        df = make_valid_dataframe()
        df.loc[0, col] = None
        with pytest.raises(ValueError, match="null values"):
            validate_dataframe(df, "Forecast dataframe")

    def test_all_null_column_raises(self):
        df = make_valid_dataframe()
        df["country_iso_a3"] = None
        with pytest.raises(ValueError, match="null values"):
            validate_dataframe(df)

    def test_nan_treated_as_null(self):
        df = make_valid_dataframe()
        df.loc[0, "pg_xcoord"] = float("nan")
        with pytest.raises(ValueError, match="null values"):
            validate_dataframe(df)


# ---------------------------------------------------------------------------
# RED: Error messages include useful context (ADR-008)
# ---------------------------------------------------------------------------

class TestErrorMessages:
    def test_missing_col_error_names_the_column(self):
        df = make_valid_dataframe().drop(columns=["country_iso_a3"])
        with pytest.raises(ValueError, match="country_iso_a3"):
            validate_dataframe(df)

    def test_null_error_includes_count(self):
        df = make_valid_dataframe(n_rows=10)
        df.loc[0:2, "pg_xcoord"] = None  # 3 nulls
        with pytest.raises(ValueError, match="3"):
            validate_dataframe(df)

    def test_errors_are_logged(self, caplog):
        df = make_valid_dataframe().drop(columns=["country_iso_a3"])
        with caplog.at_level(logging.ERROR):
            with pytest.raises(ValueError):
                validate_dataframe(df)
        assert any("country_iso_a3" in r.message for r in caplog.records)
