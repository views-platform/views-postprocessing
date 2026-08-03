"""Tests for the lookup-based enricher (ADR-011, Stage 1).

Run against the committed gaul_lookup.parquet — no datafactory checkout or
shapefiles required. These tests pin the contract the enricher must satisfy so
that swapping it in for the runtime mapper (Stage 3) is invisible downstream.
"""

import pandas as pd
import logging

import pyarrow as pa
import pyarrow.parquet as pq
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


# ── the guarantees the CIC states, pinned (S4 / #89; ADR-014 §1) ─────────────
#
# The CIC claims row/order/index preservation "verified across eight input shapes"
# and names the output dtypes. That verification was a throwaway script run once
# during development — a guarantee resting on a claim rather than on a check, which
# is precisely what ADR-014 §1 forbids, written by the story after the ADR landed.
# These commit it.


class TestConstructionRefusals:
    """Degenerate lookups must fail at construction, naming the lookup."""

    def _write(self, path, gids):
        cols = {"priogrid_gid": pa.array(gids, pa.int64())}
        for c in METADATA_COLS:
            cols[c] = pa.array(
                [0.0] * len(gids) if c in ("pg_xcoord", "pg_ycoord") or c.endswith("_code")
                else ["x"] * len(gids),
                pa.float64() if c in ("pg_xcoord", "pg_ycoord") or c.endswith("_code") else pa.string(),
            )
        t = pa.table(cols).replace_schema_metadata({b"lookup_version": b"t@00000000"})
        pq.write_table(t, path)
        return path

    def test_an_empty_lookup_is_refused_at_construction(self, tmp_path):
        """It used to raise IndexError from inside the gather instead — the guard
        `(len(self._keys) > 0) & (...)` read as a guard and was not one, because `&`
        evaluates both operands."""
        path = self._write(tmp_path / "empty.parquet", [])
        with pytest.raises(ValueError, match="is empty"):
            GaulLookupEnricher(path)

    def test_a_null_key_is_refused_at_construction(self, tmp_path):
        """A null key would coerce to the same sentinel as an unusable query id, the
        two would collide, and the row would be reported FOUND — receiving another
        cell's metadata. That is the fabricated value this module forbids (cf. C-35)."""
        cols = {"priogrid_gid": pa.array([1, None, 3], pa.int64())}
        for c in METADATA_COLS:
            numeric = c in ("pg_xcoord", "pg_ycoord") or c.endswith("_code")
            cols[c] = pa.array([0.0] * 3 if numeric else ["x"] * 3,
                               pa.float64() if numeric else pa.string())
        path = tmp_path / "nullkey.parquet"
        pq.write_table(pa.table(cols).replace_schema_metadata({b"lookup_version": b"t@0"}), path)
        with pytest.raises(ValueError, match="null values"):
            GaulLookupEnricher(path)


class TestUnusableCellIds:
    """A value that is not a cell id gathers to null — never to a guessed cell.

    Each case was verified against the pandas merge this replaced; the behaviour
    below is that merge's, not an invention. The drifted-float case is the one that
    matters most: a blind `astype(np.int64)` truncates `54220.000000001` to `54220`
    and matches a real, *different* cell, silently.
    """

    def _out(self, enricher, col):
        return enricher.enrich_dataframe_with_pg_info(
            pd.DataFrame({"priogrid_gid": col, "month_id": [1] * len(col)}),
            pg_id_col="priogrid_gid", time_id_col="month_id",
        )

    def test_a_missing_gid_yields_null_and_does_not_crash(self, enricher, lookup):
        good = lookup.index[:2].tolist()
        out = self._out(enricher, [float(good[0]), float("nan"), float(good[1])])
        assert len(out) == 3
        assert out["country_iso_a3"].isna().sum() == 1

    def test_a_non_integral_gid_never_matches_a_neighbouring_cell(self, enricher, lookup):
        gid = int(lookup.index[100])
        out = self._out(enricher, [float(gid) + 1e-9])
        assert out["country_iso_a3"].isna().all(), (
            "a drifted float matched a cell — truncation turned it into a different, "
            "real gid and fabricated that cell's geography"
        )

    def test_pandas_na_yields_null_rather_than_a_bare_typeerror(self, enricher, lookup):
        good = lookup.index[:2].tolist()
        out = self._out(enricher, pd.array([good[0], pd.NA, good[1]], dtype="Int64"))
        assert len(out) == 3 and out["country_iso_a3"].isna().sum() == 1

    def test_the_warning_names_unknown_cells_but_invents_no_id_for_unusable_ones(
        self, enricher, lookup, caplog
    ):
        good = int(lookup.index[0])
        with caplog.at_level(logging.WARNING):
            self._out(enricher, [float(good), float("nan"), 999999.0])
        message = " ".join(r.getMessage() for r in caplog.records)
        assert "999999" in message, "the genuinely unknown cell must be named"
        assert "no usable cell id" in message
        assert "[0]" not in message, (
            "an unusable id was reported as cell 0 — a cell nobody asked about"
        )


class TestFramePropertiesPreserved:
    """Row count, order and index survive the gather. Was CIC prose; now a check."""

    @pytest.mark.parametrize("shape", ["ordered", "reversed", "duplicated", "single", "empty"])
    def test_row_count_and_order_are_preserved(self, enricher, lookup, shape):
        gids = {
            "ordered": lookup.index[:50].tolist(),
            "reversed": lookup.index[:50].tolist()[::-1],
            "duplicated": lookup.index[:5].tolist() * 3,
            "single": lookup.index[:1].tolist(),
            "empty": [],
        }[shape]
        out = enricher.enrich_dataframe_with_pg_info(
            pd.DataFrame({"priogrid_gid": gids, "month_id": [1] * len(gids)}),
            pg_id_col="priogrid_gid", time_id_col="month_id",
        )
        assert len(out) == len(gids)
        assert out["priogrid_gid"].tolist() == gids

    def test_a_non_default_index_is_preserved(self, enricher, lookup):
        gids = lookup.index[:20].tolist()
        df = pd.DataFrame({"priogrid_gid": gids, "month_id": [1] * 20},
                          index=range(1000, 1020))
        out = enricher.enrich_dataframe_with_pg_info(
            df, pg_id_col="priogrid_gid", time_id_col="month_id")
        assert out.index.equals(df.index), (
            "the index moved. The pandas merge this replaced mutated it on empty "
            "input; the gather must not mutate it on any input."
        )

    def test_name_columns_are_object_not_categorical(self, enricher, lookup):
        """The CIC states this dtype. It changed in #89 and was measured, not guessed."""
        out = enricher.enrich_dataframe_with_pg_info(
            pd.DataFrame({"priogrid_gid": lookup.index[:5].tolist(), "month_id": [1] * 5}),
            pg_id_col="priogrid_gid", time_id_col="month_id",
        )
        for c in NAME_COLS:
            assert out[c].dtype == object, f"{c} is {out[c].dtype}, CIC says object"
