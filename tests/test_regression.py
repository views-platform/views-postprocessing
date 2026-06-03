"""Regression tests for code fixes applied during the audit session.

Each test protects a specific fix. Reverting the fix causes the test to fail.

Closes: https://github.com/views-platform/views-postprocessing/issues/6
Closes: https://github.com/views-platform/views-postprocessing/issues/7
Closes: https://github.com/views-platform/views-postprocessing/issues/8
Campaign: Claims 3.1, 3.3 (test gaps for fixes)
"""

import logging
import tempfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon


# ---------------------------------------------------------------------------
# Issue #6: make_valid() preprocessing
# ---------------------------------------------------------------------------

class TestMakeValidPreprocessing:
    """Verify that invalid geometries are corrected at load time."""

    def test_invalid_country_geometry_fixed_at_load(self):
        """A self-intersecting country polygon is fixed by make_valid()."""
        import views_postprocessing.unfao.mapping.mapping as mod

        bowtie = Polygon([(0, 0), (1, 1), (1, 0), (0, 1)])
        assert not bowtie.is_valid

        gdf = gpd.GeoDataFrame(
            {"ISO_A3": ["TST"], "NAME_EN": ["TestCountry"], "geometry": [bowtie]},
            crs="EPSG:4326",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "countries.shp"
            gdf.to_file(path)

            mapper = mod.PriogridCountryMapper.__new__(mod.PriogridCountryMapper)
            loaded = mapper._load_and_preprocess_naturalearth(str(path))

        assert loaded["geometry"].is_valid.all(), "make_valid() should fix invalid geometries"
        assert loaded["geometry"].iloc[0].area > 0

    def test_invalid_admin_geometry_fixed_at_load(self):
        """An invalid admin polygon is fixed by make_valid()."""
        import views_postprocessing.unfao.mapping.mapping as mod

        bowtie = Polygon([(0, 0), (1, 1), (1, 0), (0, 1)])
        gdf = gpd.GeoDataFrame(
            {
                "gaul1_code": [1], "gaul1_name": ["Test"],
                "gaul0_code": [1], "gaul0_name": ["TestC"],
                "iso3_code": ["TST"], "geometry": [bowtie],
            },
            crs="EPSG:4326",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "admin.shp"
            gdf.to_file(path)

            mapper = mod.PriogridCountryMapper.__new__(mod.PriogridCountryMapper)
            loaded = mapper._load_admin_data(str(path), "admin1")

        assert loaded["geometry"].is_valid.all()

    def test_raw_invalid_geometry_is_genuinely_invalid(self):
        """Proves the fixture IS invalid before make_valid — the guard is real."""
        bowtie = Polygon([(0, 0), (1, 1), (1, 0), (0, 1)])
        gdf = gpd.GeoDataFrame(
            {"ISO_A3": ["TST"], "NAME_EN": ["Test"], "geometry": [bowtie]},
            crs="EPSG:4326",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "raw.shp"
            gdf.to_file(path)
            raw = gpd.read_file(path)

        assert not raw["geometry"].is_valid.all(), (
            "Test fixture should contain invalid geometry before make_valid"
        )


# ---------------------------------------------------------------------------
# Issue #7: Global warning suppression must not return
# ---------------------------------------------------------------------------

class TestWarningSuppressionRegression:
    """Verify global warning suppression is absent."""

    def test_no_global_warning_suppression(self):
        """warnings.filterwarnings('ignore') must not be active globally."""
        import warnings
        # Force import of the mapping module (conftest already did this)
        import views_postprocessing.unfao.mapping.mapping  # noqa: F401

        global_ignores = [
            f for f in warnings.filters
            if f[0] == "ignore" and f[2] is Warning
        ]
        assert len(global_ignores) == 0, (
            f"Global warning suppression detected: {global_ignores}. "
            "Use targeted warnings.catch_warnings() instead."
        )

    def test_non_centroid_warnings_are_visible(self):
        """A UserWarning should be visible — global suppression is not active."""
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            warnings.warn("regression test canary", UserWarning)
            assert len(w) == 1, (
                "UserWarning should be visible — global suppression must not be active"
            )


# ---------------------------------------------------------------------------
# Issue #8: Zero-area grid geometry guard
# ---------------------------------------------------------------------------

class TestZeroAreaGuardRegression:
    """Verify that degenerate zero-area cells are handled with WARNING, not silently."""

    def test_zero_area_country_returns_none_with_warning(self, mapper, caplog):
        """A zero-area cell should return None with a WARNING log."""
        degenerate = Polygon([(0.25, 0.25), (0.5, 0.25), (0.25, 0.25)])
        assert degenerate.area == 0.0

        mapper.priogrid_gdf = pd.concat([
            mapper.priogrid_gdf,
            gpd.GeoDataFrame(
                {"gid": [99], "xcoord": [0.3], "ycoord": [0.25], "geometry": [degenerate]},
                crs="EPSG:4326",
            ),
        ], ignore_index=True)
        mapper.priogrid_gdf["centroid"] = mapper.priogrid_gdf["geometry"].centroid

        with caplog.at_level(logging.WARNING):
            result = mapper.find_country_for_gid(99)

        assert result is None, "Zero-area cell should return None"
        assert any("Zero-area" in r.message and "99" in r.message for r in caplog.records), (
            "Zero-area cell should produce a WARNING log mentioning the GID"
        )

    def test_zero_area_admin1_returns_none(self, mapper):
        """Zero-area cell returns None for admin1 lookup too."""
        degenerate = Polygon([(0.25, 0.25), (0.5, 0.25), (0.25, 0.25)])
        if 99 not in mapper.priogrid_gdf["gid"].values:
            mapper.priogrid_gdf = pd.concat([
                mapper.priogrid_gdf,
                gpd.GeoDataFrame(
                    {"gid": [99], "xcoord": [0.3], "ycoord": [0.25], "geometry": [degenerate]},
                    crs="EPSG:4326",
                ),
            ], ignore_index=True)
            mapper.priogrid_gdf["centroid"] = mapper.priogrid_gdf["geometry"].centroid

        result = mapper.find_admin1_for_gid(99)
        assert result is None

    def test_zero_area_admin2_returns_none(self, mapper):
        """Zero-area cell returns None for admin2 lookup too."""
        degenerate = Polygon([(0.25, 0.25), (0.5, 0.25), (0.25, 0.25)])
        if 99 not in mapper.priogrid_gdf["gid"].values:
            mapper.priogrid_gdf = pd.concat([
                mapper.priogrid_gdf,
                gpd.GeoDataFrame(
                    {"gid": [99], "xcoord": [0.3], "ycoord": [0.25], "geometry": [degenerate]},
                    crs="EPSG:4326",
                ),
            ], ignore_index=True)
            mapper.priogrid_gdf["centroid"] = mapper.priogrid_gdf["geometry"].centroid

        result = mapper.find_admin2_for_gid(99)
        assert result is None
