"""Test fixtures for views-postprocessing.

Handles the module-level set_default_mapper() side effect (C-02) by
intercepting shapefile loading during import and substituting synthetic
geodata. This lets tests run without Git LFS or production shapefiles.
"""

import pytest
import geopandas as gpd
from shapely.geometry import box
import tempfile
import shutil
import atexit
from pathlib import Path


# ── Synthetic shapefile data ──────────────────────────────────────────────

_COUNTRIES = gpd.GeoDataFrame(
    {
        "ISO_A3": ["AAA", "BBB"],
        "NAME_EN": ["CountryA", "CountryB"],
        "geometry": [box(0.0, 0.0, 1.0, 2.0), box(1.0, 0.0, 2.0, 2.0)],
    },
    crs="EPSG:4326",
)

_PRIOGRID = gpd.GeoDataFrame(
    {
        "gid": [1, 2, 3, 4],
        "xcoord": [0.25, 1.75, 0.85, 0.25],
        "ycoord": [0.25, 0.25, 0.25, 1.25],
        "geometry": [
            box(0.0, 0.0, 0.5, 0.5),     # cell 1: fully in AAA
            box(1.5, 0.0, 2.0, 0.5),     # cell 2: fully in BBB
            box(0.7, 0.0, 1.2, 0.5),     # cell 3: 60% AAA / 40% BBB
            box(0.0, 1.0, 0.5, 1.5),     # cell 4: fully in AAA (upper)
        ],
    },
    crs="EPSG:4326",
)

_ADMIN1 = gpd.GeoDataFrame(
    {
        "gaul1_code": [101, 102, 201, 202],
        "gaul1_name": ["A-North", "A-South", "B-North", "B-South"],
        "gaul0_code": [1, 1, 2, 2],
        "gaul0_name": ["CountryA", "CountryA", "CountryB", "CountryB"],
        "iso3_code": ["AAA", "AAA", "BBB", "BBB"],
        "geometry": [
            box(0.0, 1.0, 1.0, 2.0), box(0.0, 0.0, 1.0, 1.0),
            box(1.0, 1.0, 2.0, 2.0), box(1.0, 0.0, 2.0, 1.0),
        ],
    },
    crs="EPSG:4326",
)

_ADMIN2 = gpd.GeoDataFrame(
    {
        "gaul2_code": [1011, 1012, 1021, 1022, 2011, 2012, 2021, 2022],
        "gaul2_name": [
            "A-North-W", "A-North-E", "A-South-W", "A-South-E",
            "B-North-W", "B-North-E", "B-South-W", "B-South-E",
        ],
        "gaul1_code": [101, 101, 102, 102, 201, 201, 202, 202],
        "gaul1_name": [
            "A-North", "A-North", "A-South", "A-South",
            "B-North", "B-North", "B-South", "B-South",
        ],
        "gaul0_code": [1, 1, 1, 1, 2, 2, 2, 2],
        "gaul0_name": [
            "CountryA", "CountryA", "CountryA", "CountryA",
            "CountryB", "CountryB", "CountryB", "CountryB",
        ],
        "iso3_code": ["AAA", "AAA", "AAA", "AAA", "BBB", "BBB", "BBB", "BBB"],
        "geometry": [
            box(0.0, 1.0, 0.5, 2.0), box(0.5, 1.0, 1.0, 2.0),
            box(0.0, 0.0, 0.5, 1.0), box(0.5, 0.0, 1.0, 1.0),
            box(1.0, 1.0, 1.5, 2.0), box(1.5, 1.0, 2.0, 2.0),
            box(1.0, 0.0, 1.5, 1.0), box(1.5, 0.0, 2.0, 1.0),
        ],
    },
    crs="EPSG:4326",
)


# ── Write synthetics to disk ─────────────────────────────────────────────

_tmpdir = Path(tempfile.mkdtemp(prefix="views_test_"))
atexit.register(lambda: shutil.rmtree(_tmpdir, ignore_errors=True))

_synth_paths = {}
for _name, _gdf in [("countries", _COUNTRIES), ("priogrid", _PRIOGRID),
                     ("admin1", _ADMIN1), ("admin2", _ADMIN2)]:
    _d = _tmpdir / _name
    _d.mkdir()
    _p = _d / f"{_name}.shp"
    _gdf.to_file(_p)
    _synth_paths[_name] = str(_p)

_PATH_MAP = {
    "ne_10m_admin_0_countries": _synth_paths["countries"],
    "ne_110m_admin_0_countries": _synth_paths["countries"],
    "priogrid_cellshp": _synth_paths["priogrid"],
    "GAUL_2024_L1": _synth_paths["admin1"],
    "GAUL_2024_L2": _synth_paths["admin2"],
}


# ── Permanent gpd.read_file intercept ────────────────────────────────────
# Keep the patch active for the entire test session so that constructing
# new PriogridCountryMapper instances in fixtures also uses synthetics.

_orig_read_file = gpd.read_file


def _intercepting_read_file(path, *args, **kwargs):
    path_str = str(path)
    for substr, synth in _PATH_MAP.items():
        if substr in path_str:
            return _orig_read_file(synth, *args, **kwargs)
    return _orig_read_file(path, *args, **kwargs)


gpd.read_file = _intercepting_read_file

# Import the mapping module — set_default_mapper() now uses synthetics
import views_postprocessing.unfao.mapping.mapping as _mapping_mod  # noqa: E402


# ── Session-scoped fixtures ──────────────────────────────────────────────

@pytest.fixture(scope="session")
def mapper():
    """PriogridCountryMapper with in-memory cache, backed by synthetic geodata."""
    return _mapping_mod.PriogridCountryMapper(use_disk_cache=False)


@pytest.fixture(scope="session")
def mapper_disk_cache(tmp_path_factory):
    """PriogridCountryMapper with disk cache, backed by synthetic geodata."""
    cache_dir = tmp_path_factory.mktemp("disk_cache")
    return _mapping_mod.PriogridCountryMapper(use_disk_cache=True, cache_dir=str(cache_dir))
