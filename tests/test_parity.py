"""Gid-set parity invariant (delivery/parity.py) — §5.2, primitives only."""

import pytest

from views_postprocessing.delivery.parity import GidParityError, assert_gid_set_parity


def test_identical_sets_pass():
    assert assert_gid_set_parity([1, 2, 3], {3, 2, 1}) is None


def test_sidecar_missing_a_forecast_cell_raises_naming_it():
    with pytest.raises(GidParityError, match=r"missing.*\[3\]"):
        assert_gid_set_parity([1, 2, 3], [1, 2])


def test_extra_sidecar_cell_raises_naming_it():
    with pytest.raises(GidParityError, match=r"extra.*\[9\]"):
        assert_gid_set_parity([1, 2], [1, 2, 9])


def test_label_appears_in_message():
    with pytest.raises(GidParityError, match="ocha-sidecar"):
        assert_gid_set_parity([1], [2], label="ocha-sidecar")
