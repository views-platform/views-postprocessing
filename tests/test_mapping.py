"""Tests for PriogridCountryMapper.

Covers CIC guarantees and failure modes using synthetic shapefiles.
See docs/CICs/PriogridCountryMapper.md for the contract under test.
"""

import pytest
import pandas as pd
from shapely.geometry import Point


# ---------------------------------------------------------------------------
# GREEN: Determinism (CIC §3 — "same GID always maps to same country")
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_same_gid_returns_identical_result(self, mapper):
        result1 = mapper.find_country_for_gid(1)
        result2 = mapper.find_country_for_gid(1)
        assert result1 == result2

    def test_determinism_across_all_cells(self, mapper):
        for gid in [1, 2, 3, 4]:
            assert mapper.find_country_for_gid(gid) == mapper.find_country_for_gid(gid)

    def test_admin1_determinism(self, mapper):
        for gid in [1, 2, 3, 4]:
            assert mapper.find_admin1_for_gid(gid) == mapper.find_admin1_for_gid(gid)

    def test_admin2_determinism(self, mapper):
        for gid in [1, 2, 3, 4]:
            assert mapper.find_admin2_for_gid(gid) == mapper.find_admin2_for_gid(gid)


# ---------------------------------------------------------------------------
# GREEN: Largest-overlap assignment (CIC §3 — core algorithm)
# ---------------------------------------------------------------------------

class TestLargestOverlap:
    def test_cell_fully_in_country_a(self, mapper):
        result = mapper.find_country_for_gid(1)
        assert result is not None
        assert result["iso_a3"] == "AAA"
        assert result["method"] == "largest overlap"

    def test_cell_fully_in_country_b(self, mapper):
        result = mapper.find_country_for_gid(2)
        assert result is not None
        assert result["iso_a3"] == "BBB"

    def test_border_cell_assigned_to_larger_overlap(self, mapper):
        """Cell 3 spans x=[0.7, 1.2]: 0.3 in AAA, 0.2 in BBB → AAA wins."""
        result = mapper.find_country_for_gid(3)
        assert result is not None
        assert result["iso_a3"] == "AAA"
        assert result["overlap_ratio"] > 0.5

    def test_overlap_ratio_is_float(self, mapper):
        result = mapper.find_country_for_gid(1)
        assert isinstance(result["overlap_ratio"], float)
        assert 0.0 < result["overlap_ratio"] <= 1.0


# ---------------------------------------------------------------------------
# GREEN: Admin-level assignment (CIC §3)
# ---------------------------------------------------------------------------

class TestAdminAssignment:
    def test_admin1_for_interior_cell(self, mapper):
        result = mapper.find_admin1_for_gid(1)
        assert result is not None
        assert result["gaul1_name"] == "A-South"
        assert result["iso3_code"] == "AAA"

    def test_admin1_for_upper_cell(self, mapper):
        result = mapper.find_admin1_for_gid(4)
        assert result is not None
        assert result["gaul1_name"] == "A-North"

    def test_admin2_for_interior_cell(self, mapper):
        result = mapper.find_admin2_for_gid(1)
        assert result is not None
        assert result["gaul2_name"] == "A-South-W"

    def test_admin1_consistent_with_country(self, mapper):
        for gid in [1, 2, 4]:
            country = mapper.find_country_for_gid(gid)
            admin1 = mapper.find_admin1_for_gid(gid)
            if country and admin1:
                assert admin1["iso3_code"] == country["iso_a3"]


# ---------------------------------------------------------------------------
# GREEN: Output schema for DataFrame enrichment (CIC §3, §5)
# ---------------------------------------------------------------------------

class TestEnrichDataframe:
    def test_enrichment_adds_expected_columns(self, mapper):
        df = pd.DataFrame({
            "priogrid_id": [1, 2, 4],
            "month_id": [100, 100, 100],
            "pred_value": [0.5, 0.3, 0.1],
        })
        enriched = mapper.enrich_dataframe_with_pg_info(
            df, pg_id_col="priogrid_id", time_id_col="month_id",
            batch_size=10, use_multiprocessing=False, show_progress=False
        )
        expected_cols = [
            "pg_xcoord", "pg_ycoord", "country_iso_a3",
            "admin1_gaul1_code", "admin1_gaul1_name",
            "admin1_gaul0_code", "admin1_gaul0_name",
            "admin2_gaul2_code", "admin2_gaul2_name",
        ]
        for col in expected_cols:
            assert col in enriched.columns, f"Missing column: {col}"

    def test_enrichment_preserves_row_identity(self, mapper):
        df = pd.DataFrame({
            "priogrid_id": [1, 2],
            "month_id": [100, 100],
        })
        enriched = mapper.enrich_dataframe_with_pg_info(
            df, pg_id_col="priogrid_id", time_id_col="month_id",
            batch_size=10, use_multiprocessing=False, show_progress=False
        )
        assert list(enriched["priogrid_id"]) == [1, 2]

    def test_enrichment_row_count_preserved(self, mapper):
        df = pd.DataFrame({
            "priogrid_id": [1, 2, 3, 4],
            "month_id": [100, 100, 100, 100],
        })
        enriched = mapper.enrich_dataframe_with_pg_info(
            df, pg_id_col="priogrid_id", time_id_col="month_id",
            batch_size=10, use_multiprocessing=False, show_progress=False
        )
        assert len(enriched) == 4


# ---------------------------------------------------------------------------
# GREEN: Cache equivalence (CIC §3 — "cache mode doesn't affect results")
# ---------------------------------------------------------------------------

class TestCacheEquivalence:
    def test_memory_and_disk_cache_produce_same_country(self, mapper, mapper_disk_cache):
        for gid in [1, 2, 3, 4]:
            mem_result = mapper.find_country_for_gid(gid)
            disk_result = mapper_disk_cache.find_country_for_gid(gid)
            if mem_result is None:
                assert disk_result is None
            else:
                assert mem_result["iso_a3"] == disk_result["iso_a3"]
                assert abs(mem_result["overlap_ratio"] - disk_result["overlap_ratio"]) < 1e-9

    def test_memory_and_disk_cache_produce_same_admin1(self, mapper, mapper_disk_cache):
        for gid in [1, 2, 4]:
            mem = mapper.find_admin1_for_gid(gid)
            disk = mapper_disk_cache.find_admin1_for_gid(gid)
            if mem is None:
                assert disk is None
            else:
                assert mem["gaul1_code"] == disk["gaul1_code"]


# ---------------------------------------------------------------------------
# RED: GID not found returns None (CIC §6)
# ---------------------------------------------------------------------------

class TestGidNotFound:
    def test_nonexistent_gid_returns_none(self, mapper):
        assert mapper.find_country_for_gid(999999) is None

    def test_nonexistent_gid_admin1_returns_none(self, mapper):
        assert mapper.find_admin1_for_gid(999999) is None

    def test_nonexistent_gid_admin2_returns_none(self, mapper):
        assert mapper.find_admin2_for_gid(999999) is None


# ---------------------------------------------------------------------------
# RED: Invalid point geometry raises ValueError (CIC §6)
# ---------------------------------------------------------------------------

class TestInvalidGeometry:
    def test_invalid_point_raises(self, mapper):
        from shapely import wkt
        invalid_point = wkt.loads("POINT (0 0)")
        invalid_point = Point(float("nan"), float("nan"))
        with pytest.raises((ValueError, Exception)):
            mapper.find_gid_for_point(invalid_point)


# ---------------------------------------------------------------------------
# RED: Missing shapefile raises at init (CIC §6)
# ---------------------------------------------------------------------------

class TestMissingShapefile:
    def test_missing_country_shapefile_raises(self):
        import views_postprocessing.unfao.mapping.mapping as mod
        import tempfile
        import os

        tmpdir = tempfile.mkdtemp()
        missing_path = os.path.join(tmpdir, "nonexistent", "missing.shp")
        orig = mod.NATURAL_EARTH_COUNTRY_PATH
        mod.NATURAL_EARTH_COUNTRY_PATH = missing_path
        try:
            with pytest.raises(Exception):
                mod.PriogridCountryMapper(use_disk_cache=False)
        finally:
            mod.NATURAL_EARTH_COUNTRY_PATH = orig
            os.rmdir(tmpdir)


# ---------------------------------------------------------------------------
# RED: batch_country_mapping crashes with disk cache (C-05)
# ---------------------------------------------------------------------------

class TestBatchCountryMappingDiskCacheBug:
    def test_batch_country_mapping_with_disk_cache_raises(self, mapper_disk_cache):
        """Documents known bug C-05: batch_country_mapping accesses
        self._country_cache which doesn't exist in disk-cache mode."""
        with pytest.raises(AttributeError):
            mapper_disk_cache.batch_country_mapping([1, 2])


# ---------------------------------------------------------------------------
# GREEN: Reverse lookup (find_gids_for_country)
# ---------------------------------------------------------------------------

class TestReverseLookup:
    def test_finds_gids_for_known_country(self, mapper):
        gids = mapper.find_gids_for_country("AAA")
        assert isinstance(gids, list)
        assert len(gids) > 0
        assert 1 in gids  # cell 1 is fully in AAA

    def test_unknown_country_returns_empty(self, mapper):
        gids = mapper.find_gids_for_country("ZZZ")
        assert gids == []

    def test_interior_cells_in_reverse_lookup(self, mapper):
        """Cells fully contained by a country should appear in its reverse lookup."""
        gids_a = mapper.find_gids_for_country("AAA")
        assert 1 in gids_a  # fully in AAA
        assert 4 in gids_a  # fully in AAA

        gids_b = mapper.find_gids_for_country("BBB")
        assert 2 in gids_b  # fully in BBB


# ---------------------------------------------------------------------------
# BEIGE: Utility methods
# ---------------------------------------------------------------------------

class TestUtilityMethods:
    def test_get_all_iso_a3_codes(self, mapper):
        codes = mapper.get_all_iso_a3_codes()
        assert "AAA" in codes
        assert "BBB" in codes

    def test_find_country_by_iso_a3(self, mapper):
        result = mapper.find_country_by_iso_a3("AAA")
        assert result is not None
        assert result["country_name"] == "CountryA"

    def test_find_country_by_invalid_code(self, mapper):
        assert mapper.find_country_by_iso_a3("ZZ") is None  # not 3 chars

    def test_find_all_admin_for_gid(self, mapper):
        result = mapper.find_all_admin_for_gid(1)
        assert "country" in result
        assert "admin1" in result
        assert "admin2" in result
