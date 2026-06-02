"""Integration tests for the mapper-to-manager boundary contract.

Verifies that PriogridCountryMapper.enrich_dataframe_with_pg_info() produces
output compatible with UNFAOPostProcessorManager._append_metadata()'s filter_cols
and _validate()'s null checks.

Closes: https://github.com/views-platform/views-postprocessing/issues/4
Campaign: Claim 3.4 (FALSIFIED — no integration test existed)
"""

import pandas as pd

FILTER_COLS_METADATA = [
    "pg_xcoord",
    "pg_ycoord",
    "country_iso_a3",
    "admin1_gaul1_code",
    "admin1_gaul1_name",
    "admin1_gaul0_code",
    "admin1_gaul0_name",
    "admin2_gaul2_code",
    "admin2_gaul2_name",
]

REQUIRED_METADATA_COLS = FILTER_COLS_METADATA


class TestMapperToManagerBoundary:
    """Verify the enrichment output matches what the manager consumes."""

    def test_all_filter_cols_present_in_enrichment(self, mapper):
        df = pd.DataFrame({
            "priogrid_gid": [1, 2, 3, 4],
            "month_id": [100, 100, 100, 100],
        })
        enriched = mapper.enrich_dataframe_with_pg_info(
            df, pg_id_col="priogrid_gid", time_id_col="month_id",
            only_metadata=True, batch_size=10,
            use_multiprocessing=False, show_progress=False,
        )
        for col in FILTER_COLS_METADATA:
            assert col in enriched.columns, (
                f"filter_cols column '{col}' missing from enrichment output. "
                f"Available: {sorted(enriched.columns.tolist())}"
            )

    def test_no_nulls_in_metadata_columns_for_valid_gids(self, mapper):
        df = pd.DataFrame({
            "priogrid_gid": [1, 2, 4],
            "month_id": [100, 100, 100],
        })
        enriched = mapper.enrich_dataframe_with_pg_info(
            df, pg_id_col="priogrid_gid", time_id_col="month_id",
            only_metadata=True, batch_size=10,
            use_multiprocessing=False, show_progress=False,
        )
        for col in FILTER_COLS_METADATA:
            null_count = enriched[col].isnull().sum()
            assert null_count == 0, (
                f"Column '{col}' has {null_count} nulls in enrichment output for valid GIDs"
            )

    def test_country_iso_a3_contains_valid_codes(self, mapper):
        df = pd.DataFrame({
            "priogrid_gid": [1, 2, 3, 4],
            "month_id": [100, 100, 100, 100],
        })
        enriched = mapper.enrich_dataframe_with_pg_info(
            df, pg_id_col="priogrid_gid", time_id_col="month_id",
            only_metadata=True, batch_size=10,
            use_multiprocessing=False, show_progress=False,
        )
        valid_codes = {"AAA", "BBB"}
        actual_codes = set(enriched["country_iso_a3"].dropna().unique())
        assert actual_codes.issubset(valid_codes), (
            f"Unexpected ISO codes: {actual_codes - valid_codes}"
        )

    def test_admin_codes_are_numeric(self, mapper):
        df = pd.DataFrame({
            "priogrid_gid": [1, 2, 4],
            "month_id": [100, 100, 100],
        })
        enriched = mapper.enrich_dataframe_with_pg_info(
            df, pg_id_col="priogrid_gid", time_id_col="month_id",
            only_metadata=True, batch_size=10,
            use_multiprocessing=False, show_progress=False,
        )
        for col in ["admin1_gaul1_code", "admin1_gaul0_code", "admin2_gaul2_code"]:
            assert pd.api.types.is_numeric_dtype(enriched[col]), (
                f"Column '{col}' should be numeric, got {enriched[col].dtype}"
            )

    def test_coordinates_are_float(self, mapper):
        df = pd.DataFrame({
            "priogrid_gid": [1, 2],
            "month_id": [100, 100],
        })
        enriched = mapper.enrich_dataframe_with_pg_info(
            df, pg_id_col="priogrid_gid", time_id_col="month_id",
            only_metadata=True, batch_size=10,
            use_multiprocessing=False, show_progress=False,
        )
        for col in ["pg_xcoord", "pg_ycoord"]:
            assert pd.api.types.is_float_dtype(enriched[col]), (
                f"Column '{col}' should be float, got {enriched[col].dtype}"
            )

    def test_row_count_preserved(self, mapper):
        df = pd.DataFrame({
            "priogrid_gid": [1, 2, 3, 4],
            "month_id": [100, 100, 100, 100],
        })
        enriched = mapper.enrich_dataframe_with_pg_info(
            df, pg_id_col="priogrid_gid", time_id_col="month_id",
            only_metadata=True, batch_size=10,
            use_multiprocessing=False, show_progress=False,
        )
        assert len(enriched) == 4


class TestEnrichmentThenValidation:
    """Verify that mapper output passes the manager's validation logic."""

    def test_enriched_output_passes_validation(self, mapper):
        df = pd.DataFrame({
            "priogrid_gid": [1, 2, 4],
            "month_id": [100, 100, 100],
        })
        enriched = mapper.enrich_dataframe_with_pg_info(
            df, pg_id_col="priogrid_gid", time_id_col="month_id",
            only_metadata=True, batch_size=10,
            use_multiprocessing=False, show_progress=False,
        )
        for col in REQUIRED_METADATA_COLS:
            assert col in enriched.columns, f"Validation would fail: '{col}' missing"
            null_count = enriched[col].isnull().sum()
            assert null_count == 0, (
                f"Validation would fail: '{col}' has {null_count} nulls"
            )
