"""Unit tests for the representation-free forecast-identity invariant (S3 / C-25)."""

import pytest

from views_postprocessing.delivery.identity import (
    ForecastIdentityError,
    assert_forecast_identity,
)


def test_matching_identity_passes():
    selected = {"name": "fatalities_ensemble", "loa": "pgm", "category": "forecast"}
    expected = {"name": "fatalities_ensemble", "loa": "pgm"}
    assert_forecast_identity(selected, expected)  # no raise


def test_name_mismatch_fails_loud_naming_expected_and_found():
    selected = {"name": "stray_model", "loa": "pgm"}
    expected = {"name": "fatalities_ensemble", "loa": "pgm"}
    with pytest.raises(ForecastIdentityError) as exc:
        assert_forecast_identity(selected, expected)
    msg = str(exc.value)
    assert "name" in msg
    assert "fatalities_ensemble" in msg  # expected
    assert "stray_model" in msg  # found


def test_loa_mismatch_raises():
    with pytest.raises(ForecastIdentityError):
        assert_forecast_identity({"name": "m", "loa": "cm"}, {"name": "m", "loa": "pgm"})


def test_missing_key_is_treated_as_mismatch():
    with pytest.raises(ForecastIdentityError):
        assert_forecast_identity({"loa": "pgm"}, {"name": "m", "loa": "pgm"})


def test_only_expected_keys_are_checked():
    # extra metadata on `selected` is ignored — the caller decides what identity means.
    selected = {"name": "m", "loa": "pgm", "category": "forecast", "targets": ["a"]}
    assert_forecast_identity(selected, {"name": "m"})  # no raise


def test_label_appears_in_message():
    with pytest.raises(ForecastIdentityError, match="historical"):
        assert_forecast_identity({"name": "x"}, {"name": "y"}, label="historical")
