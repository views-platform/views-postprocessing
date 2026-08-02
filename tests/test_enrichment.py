"""Tests for the lookup-based enricher (ADR-011, Stage 1).

Run against the committed gaul_lookup.parquet — no datafactory checkout or
shapefiles required. These tests pin the contract the enricher must satisfy so
that swapping it in for the runtime mapper (Stage 3) is invisible downstream.
"""

import pandas as pd
import pytest

from views_postprocessing.contract import gaul_lookup
from views_postprocessing.contract.enrichment import (
    GaulLookupEnricher,
    METADATA_COLS,
)

# The 5 africa_me_legacy ocean cells that have no GAUL assignment — they must
# NOT be in the lookup (they are excluded upstream by the land_gaul region).
OCEAN_CELLS = [62356, 94776, 99027, 107733, 107742]

CODE_COLS = ["admin1_gaul1_code", "admin1_gaul0_code", "admin2_gaul2_code"]
NAME_COLS = ["admin1_gaul1_name", "admin1_gaul0_name", "admin2_gaul2_name",
             "country_iso_a3"]


@pytest.fixture(scope="module")
def enricher():
    return GaulLookupEnricher()


@pytest.fixture(scope="module")
def lookup():
    """The committed artifact as a pandas frame, built here rather than reached for.

    Until S4 (#89) this was ``enricher._lookup`` — the enricher's own private pandas
    frame. It no longer has one: the lookup side is numpy + pyarrow, and pandas is a
    type-only import there. These tests are about the **artifact**, not the enricher,
    so they load it directly.

    The ``set_index`` is deliberate and forward-looking. ``to_pandas()`` currently
    restores ``priogrid_gid`` as the index from the parquet's embedded pandas
    metadata — metadata that **S5 (#90) removes** when the builder becomes
    pyarrow-native. Handling both shapes means these tests do not have to change
    again then.
    """
    df = gaul_lookup.load().to_pandas()
    if "priogrid_gid" in df.columns:
        df = df.set_index("priogrid_gid")
    return df


class TestLookupIntegrity:
    """The committed lookup must be clean by construction."""

    def test_expected_cell_count(self, lookup):
        # land_gaul region: 64,742 fully-complete land cells.
        assert len(lookup) == 64_742

    def test_no_nulls_anywhere(self, lookup):
        assert int(lookup.isna().sum().sum()) == 0

    def test_no_minus_one_sentinel_in_codes(self, lookup):
        for c in CODE_COLS:
            assert (lookup[c] != -1).all(), f"{c} has -1 sentinel"

    def test_no_empty_strings_in_names(self, lookup):
        for c in NAME_COLS:
            assert (lookup[c].astype(str).str.len() > 0).all()

    def test_has_exactly_the_nine_contract_columns(self, lookup):
        assert list(lookup.columns) == METADATA_COLS

    def test_dtypes(self, lookup):
        for c in CODE_COLS:
            assert pd.api.types.is_numeric_dtype(lookup[c]), c
        for c in ["pg_xcoord", "pg_ycoord"]:
            assert pd.api.types.is_float_dtype(lookup[c]), c
        for c in NAME_COLS:
            assert isinstance(lookup[c].dtype, pd.CategoricalDtype), c

    def test_ocean_cells_excluded(self, lookup):
        for gid in OCEAN_CELLS:
            assert gid not in lookup.index, f"ocean cell {gid} should be excluded"


class TestCoordinateFormula:
    """pg_xcoord/pg_ycoord must follow the PRIO-GRID 0.5-degree formula."""

    def test_known_coordinates(self, lookup):
        for gid in lookup.index[:50]:
            x = -180.0 + ((gid - 1) % 720) * 0.5 + 0.25
            y = -90.0 + ((gid - 1) // 720) * 0.5 + 0.25
            assert lookup.loc[gid, "pg_xcoord"] == pytest.approx(x)
            assert lookup.loc[gid, "pg_ycoord"] == pytest.approx(y)


class TestEnricherContract:
    """enrich() must reproduce the 9-column contract the manager consumes."""

    def _frame(self, gids):
        return pd.DataFrame({
            "priogrid_gid": gids,
            "month_id": [100] * len(gids),
        })

    def test_all_metadata_cols_present(self, enricher, lookup):
        gids = lookup.index[:10].tolist()
        out = enricher.enrich_dataframe_with_pg_info(
            self._frame(gids), pg_id_col="priogrid_gid", time_id_col="month_id",
        )
        for c in METADATA_COLS:
            assert c in out.columns

    def test_no_nulls_for_known_gids(self, enricher, lookup):
        gids = lookup.index[:100].tolist()
        out = enricher.enrich_dataframe_with_pg_info(
            self._frame(gids), pg_id_col="priogrid_gid", time_id_col="month_id",
        )
        for c in METADATA_COLS:
            assert out[c].isna().sum() == 0, c

    def test_values_match_lookup(self, enricher, lookup):
        gids = lookup.index[:20].tolist()
        out = enricher.enrich_dataframe_with_pg_info(
            self._frame(gids), pg_id_col="priogrid_gid", time_id_col="month_id",
        ).set_index("priogrid_gid")
        for gid in gids:
            assert out.loc[gid, "country_iso_a3"] == lookup.loc[gid, "country_iso_a3"]
            assert out.loc[gid, "admin2_gaul2_code"] == lookup.loc[gid, "admin2_gaul2_code"]

    def test_row_count_preserved(self, enricher, lookup):
        gids = lookup.index[:7].tolist()
        out = enricher.enrich_dataframe_with_pg_info(
            self._frame(gids), pg_id_col="priogrid_gid", time_id_col="month_id",
        )
        assert len(out) == 7

    def test_codes_numeric_coords_float(self, enricher, lookup):
        gids = lookup.index[:5].tolist()
        out = enricher.enrich_dataframe_with_pg_info(
            self._frame(gids), pg_id_col="priogrid_gid", time_id_col="month_id",
        )
        for c in CODE_COLS:
            assert pd.api.types.is_numeric_dtype(out[c]), c
        for c in ["pg_xcoord", "pg_ycoord"]:
            assert pd.api.types.is_float_dtype(out[c]), c


class TestFailLoud:
    """Unknown / excluded cells must surface as NaN, not a sentinel."""

    def test_unknown_gid_yields_null(self, enricher, lookup):
        good = int(lookup.index[0])
        df = pd.DataFrame({"priogrid_gid": [good, 999_999], "month_id": [1, 1]})
        out = enricher.enrich_dataframe_with_pg_info(
            df, pg_id_col="priogrid_gid", time_id_col="month_id",
        ).set_index("priogrid_gid")
        assert out.loc[good, "country_iso_a3"] is not None
        assert pd.isna(out.loc[999_999, "country_iso_a3"])
        for c in CODE_COLS:
            assert pd.isna(out.loc[999_999, c])

    def test_ocean_cell_yields_null(self, enricher):
        df = pd.DataFrame({"priogrid_gid": OCEAN_CELLS,
                           "month_id": [1] * len(OCEAN_CELLS)})
        out = enricher.enrich_dataframe_with_pg_info(
            df, pg_id_col="priogrid_gid", time_id_col="month_id",
        )
        # Every ocean cell is absent from the lookup -> all-null metadata.
        assert out["country_iso_a3"].isna().all()

    def test_missing_pg_id_col_raises(self, enricher):
        with pytest.raises(ValueError, match="not found"):
            enricher.enrich_dataframe_with_pg_info(
                pd.DataFrame({"x": [1]}), pg_id_col="priogrid_gid",
            )
