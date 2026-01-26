import pandas as pd
import geopandas as gpd
from datetime import datetime
from shapely.geometry import shape
from shapely.geometry import Point as ShapelyPoint
from shapely import wkt
import warnings
from abc import ABC, abstractmethod
from typing import Optional, Union, List, Dict, Any

from functools import lru_cache, partial
from collections import OrderedDict
import math
import numpy as np
import logging
from pathlib import Path
import os

from multiprocessing import Pool, Manager, cpu_count
from joblib import Memory
from cachetools import LRUCache, TTLCache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore")

NATURAL_EARTH_COUNTRY_PATH = (
    Path(__file__).parent.parent.parent
    / "shapefiles"
    / "ne_10m_admin_0_countries"
    / "ne_10m_admin_0_countries.shp"
)

PRIOGRID_SHAPEFILE_PATH = (
    Path(__file__).parent.parent.parent
    / "shapefiles"
    / "priogrid_cellshp"
    / "priogrid_cell.shp"
)
ADM_1_SHAPEFILE_PATH = (
    Path(__file__).parent.parent.parent
    / "shapefiles"
    / "GAUL_2024_L1"
    / "GAUL_2024_L1.shp"
)
ADM_2_SHAPEFILE_PATH = (
    Path(__file__).parent.parent.parent
    / "shapefiles"
    / "GAUL_2024_L2"
    / "GAUL_2024_L2.shp"
)

# Configure disk cache
CACHE_DIR = Path.home() / ".priogrid_mapper_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Cache sizes
COUNTRY_CACHE_MAXSIZE = 100000
GID_CACHE_MAXSIZE = 100000
GIDS_FOR_COUNTRY_CACHE_MAXSIZE = 10000000
ADMIN1_CACHE_MAXSIZE = 100000
ADMIN2_CACHE_MAXSIZE = 100000

# Global disk caches (shared across instances)
_disk_country_cache = Memory(location=CACHE_DIR / "country", verbose=0)
_disk_admin1_cache = Memory(location=CACHE_DIR / "admin1", verbose=0)
_disk_admin2_cache = Memory(location=CACHE_DIR / "admin2", verbose=0)
_disk_gid_cache = Memory(location=CACHE_DIR / "gid", verbose=0)


class DistanceCache:
    """Simple LRU cache for distance calculations."""

    def __init__(self, maxsize=1000):
        self.cache = OrderedDict()
        self.maxsize = maxsize

    def get(self, key):
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    def set(self, key, value):
        self.cache[key] = value
        self.cache.move_to_end(key)
        if len(self.cache) > self.maxsize:
            self.cache.popitem(last=False)


# Global distance cache
_distance_cache = DistanceCache()


def cached_haversine(lat1, lon1, lat2, lon2):
    """Calculate haversine distance with caching."""
    # Validate coordinates
    if (
        not (-90 <= lat1 <= 90)
        or not (-180 <= lon1 <= 180)
        or not (-90 <= lat2 <= 90)
        or not (-180 <= lon2 <= 180)
    ):
        raise ValueError(
            "Invalid coordinates: latitudes must be between -90 and 90, longitudes between -180 and 180"
        )

    # Create a cache key based on the coordinates (rounded to 6 decimal places)
    cache_key = (round(lat1, 6), round(lon1, 6), round(lat2, 6), round(lon2, 6))

    # Check cache first
    cached_result = _distance_cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    # Not in cache, perform the calculation
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    result = 6371.0 * c  # Earth radius in kilometers

    # Update cache
    _distance_cache.set(cache_key, result)
    return result


class PriogridCountryMapper:
    """
    A comprehensive class for mapping between PRIO-GRID cells and countries using Natural Earth shapefiles.
    Now with persistent disk caching for improved performance across sessions.

    Attributes:
        countries_gdf (GeoDataFrame): Processed Natural Earth country data
        priogrid_gdf (GeoDataFrame): Processed PRIO-GRID data with cell geometries and centroids
        priogrid_sindex (SpatialIndex): Spatial index for faster PRIO-GRID queries
    """

    def __init__(self, use_disk_cache=True, cache_dir=None, cache_ttl=None):
        """
        Initialize the PriogridCountryMapper with optional disk caching.

        Parameters:
            use_disk_cache (bool): Whether to use persistent disk caching
            cache_dir (str or Path): Custom cache directory path
            cache_ttl (int): Time-to-live for cache entries in seconds (None for no expiration)
        """
        # Initialize attributes used in __del__ immediately to prevent AttributeError
        # if an exception occurs during initialization (e.g., missing shapefiles).
        self._process_pool = None
        self._max_workers = cpu_count()

        # Load Natural Earth country data
        # NOTE: This is the line that was crashing in your traceback (line 134)
        country_path = str(NATURAL_EARTH_COUNTRY_PATH)
        self.countries_gdf = self._load_and_preprocess_naturalearth(country_path)

        # Load PRIO-GRID data
        self.priogrid_gdf = self._load_priogrid(str(PRIOGRID_SHAPEFILE_PATH))

        self.priogrid_sindex = (
            self.priogrid_gdf.sindex if hasattr(self.priogrid_gdf, "sindex") else None
        )

        # Configure caching
        self.use_disk_cache = use_disk_cache
        self.cache_ttl = cache_ttl

        if use_disk_cache:
            # Set up custom cache directory if provided
            if cache_dir:
                self.cache_dir = Path(cache_dir)
                os.makedirs(self.cache_dir, exist_ok=True)
            else:
                self.cache_dir = CACHE_DIR

            # Initialize disk caches
            self._disk_country_cache = Memory(
                location=self.cache_dir / "country", verbose=0
            )
            self._disk_admin1_cache = Memory(
                location=self.cache_dir / "admin1", verbose=0
            )
            self._disk_admin2_cache = Memory(
                location=self.cache_dir / "admin2", verbose=0
            )
            self._disk_gid_cache = Memory(location=self.cache_dir / "gid", verbose=0)

            logger.info(f"Using disk cache at: {self.cache_dir}")
        else:
            # Initialize in-memory caches as instance variables
            if cache_ttl:
                self._country_cache = TTLCache(
                    maxsize=COUNTRY_CACHE_MAXSIZE, ttl=cache_ttl
                )
                self._gid_cache = TTLCache(maxsize=GID_CACHE_MAXSIZE, ttl=cache_ttl)
                self._gids_for_country_cache = TTLCache(
                    maxsize=GIDS_FOR_COUNTRY_CACHE_MAXSIZE, ttl=cache_ttl
                )
                self._admin1_cache = TTLCache(
                    maxsize=ADMIN1_CACHE_MAXSIZE, ttl=cache_ttl
                )
                self._admin2_cache = TTLCache(
                    maxsize=ADMIN2_CACHE_MAXSIZE, ttl=cache_ttl
                )
            else:
                self._country_cache = LRUCache(maxsize=COUNTRY_CACHE_MAXSIZE)
                self._gid_cache = LRUCache(maxsize=GID_CACHE_MAXSIZE)
                self._gids_for_country_cache = LRUCache(
                    maxsize=GIDS_FOR_COUNTRY_CACHE_MAXSIZE
                )
                self._admin1_cache = LRUCache(maxsize=ADMIN1_CACHE_MAXSIZE)
                self._admin2_cache = LRUCache(maxsize=ADMIN2_CACHE_MAXSIZE)

            logger.info("Using in-memory caching")

        # Load admin1 and admin2 data if paths are provided
        self.admin1_path = str(ADM_1_SHAPEFILE_PATH)
        self.admin2_path = str(ADM_2_SHAPEFILE_PATH)

        self.admin1_gdf = None
        self.admin2_gdf = None

        if self.admin1_path:
            self.admin1_gdf = self._load_admin_data(self.admin1_path, "admin1")
            self.admin1_sindex = (
                self.admin1_gdf.sindex if hasattr(self.admin1_gdf, "sindex") else None
            )
        else:
            self.admin1_sindex = None

        if self.admin2_path:
            self.admin2_gdf = self._load_admin_data(self.admin2_path, "admin2")
            self.admin2_sindex = (
                self.admin2_gdf.sindex if hasattr(self.admin2_gdf, "sindex") else None
            )
        else:
            self.admin2_sindex = None

    def _get_gid_cache_key(self, gid):
        """Generate a consistent cache key for GID-based lookups"""
        return f"gid_{gid}"

    def _get_point_cache_key(self, point_geometry):
        """Generate a consistent cache key for point-based lookups"""
        return f"point_{round(point_geometry.x, 6)}_{round(point_geometry.y, 6)}"

    def _get_country_cache_key(self, iso_a3):
        """Generate a consistent cache key for country-based lookups"""
        return f"country_{iso_a3.upper() if iso_a3 else iso_a3}"

    def _get_admin_cache_key(self, gid, admin_level):
        """Generate a consistent cache key for admin-based lookups"""
        return f"{admin_level}_{gid}"

    def clear_cache(self, cache_type="all"):
        """
        Clear cached data.

        Parameters:
            cache_type (str): Type of cache to clear ("all", "country", "admin1", "admin2", "gid")
        """
        if self.use_disk_cache:
            if cache_type == "all" or cache_type == "country":
                self._disk_country_cache.clear()
                logger.info("Cleared country cache")

            if cache_type == "all" or cache_type == "admin1":
                self._disk_admin1_cache.clear()
                logger.info("Cleared admin1 cache")

            if cache_type == "all" or cache_type == "admin2":
                self._disk_admin2_cache.clear()
                logger.info("Cleared admin2 cache")

            if cache_type == "all" or cache_type == "gid":
                self._disk_gid_cache.clear()
                logger.info("Cleared GID cache")
        else:
            if cache_type == "all" or cache_type == "country":
                self._country_cache.clear()
                logger.info("Cleared country cache")

            if cache_type == "all" or cache_type == "admin1":
                self._admin1_cache.clear()
                logger.info("Cleared admin1 cache")

            if cache_type == "all" or cache_type == "admin2":
                self._admin2_cache.clear()
                logger.info("Cleared admin2 cache")

            if cache_type == "all" or cache_type == "gid":
                self._gid_cache.clear()
                logger.info("Cleared GID cache")

    def get_cache_stats(self):
        """
        Get statistics about cache usage.

        Returns:
            dict: Cache statistics
        """
        if self.use_disk_cache:
            stats = {
                "cache_type": "disk",
                "cache_dir": str(self.cache_dir),
                "country_cache_size": len(self._disk_country_cache),
                "admin1_cache_size": len(self._disk_admin1_cache),
                "admin2_cache_size": len(self._disk_admin2_cache),
                "gid_cache_size": len(self._disk_gid_cache),
            }

            # Calculate total cache size on disk
            total_size = 0
            for cache_dir in [
                self.cache_dir / d for d in ["country", "admin1", "admin2", "gid"]
            ]:
                if cache_dir.exists():
                    for file in cache_dir.glob("*"):
                        if file.is_file():
                            total_size += file.stat().st_size

            stats["total_disk_size_mb"] = round(total_size / (1024 * 1024), 2)
        else:
            stats = {
                "cache_type": "memory",
                "country_cache_size": len(self._country_cache),
                "country_cache_maxsize": self._country_cache.maxsize,
                "gid_cache_size": len(self._gid_cache),
                "gid_cache_maxsize": self._gid_cache.maxsize,
                "admin1_cache_size": len(self._admin1_cache),
                "admin1_cache_maxsize": self._admin1_cache.maxsize,
                "admin2_cache_size": len(self._admin2_cache),
                "admin2_cache_maxsize": self._admin2_cache.maxsize,
            }

            if hasattr(self._country_cache, "currsize"):
                stats["country_cache_hit_rate"] = (
                    f"{self._country_cache.hits}/{self._country_cache.hits + self._country_cache.misses}"
                )
                stats["gid_cache_hit_rate"] = (
                    f"{self._gid_cache.hits}/{self._gid_cache.hits + self._gid_cache.misses}"
                )

        return stats

    def warm_cache(self, gid_list=None, iso_a3_list=None):
        """
        Warm up the cache with frequently accessed data.

        Parameters:
            gid_list (list): List of GIDs to pre-cache
            iso_a3_list (list): List of ISO A3 codes to pre-cache
        """
        if gid_list:
            logger.info(f"Warming cache with {len(gid_list)} GIDs")
            for gid in gid_list:
                self.find_country_for_gid(gid)
                self.find_admin1_for_gid(gid)
                self.find_admin2_for_gid(gid)

        if iso_a3_list:
            logger.info(f"Warming cache with {len(iso_a3_list)} countries")
            for iso_a3 in iso_a3_list:
                self.find_country_by_iso_a3(iso_a3)
                self.find_gids_for_country(iso_a3)

        logger.info("Cache warming complete")

    def __del__(self):
        if self._process_pool:
            self._process_pool.close()
            self._process_pool.join()

    def _init_process_pool(self):
        """Initialize the process pool if not already done"""
        if self._process_pool is None:
            self._process_pool = Pool(processes=self._max_workers)

    def batch_country_mapping_parallel(self, gid_list, batch_size=1000):
        """
        Find countries for multiple PRIO-GRID cells using multiprocessing.

        Parameters:
            gid_list (list): List of PRIO-GRID cell IDs
            batch_size (int): Number of GIDs to process in each batch

        Returns:
            DataFrame: Results of the batch mapping
        """
        self._init_process_pool()

        # Split into batches
        batches = [
            gid_list[i : i + batch_size] for i in range(0, len(gid_list), batch_size)
        ]

        # Create partial function for mapping
        map_func = partial(self._process_gid_batch)

        # Process batches in parallel
        results = []
        for batch_result in self._process_pool.imap_unordered(map_func, batches):
            results.extend(batch_result)

        return pd.DataFrame(results)

    def _process_gid_batch(self, gid_batch):
        """Process a batch of GIDs in a single process"""
        batch_results = []
        for gid in gid_batch:
            result = self.find_country_for_gid(gid)
            batch_results.append(result)
        return batch_results

    def _load_and_preprocess_naturalearth(self, country_path):
        """
        Load and preprocess the Natural Earth country dataset from the provided path.

        Parameters:
            country_path (str): Path to the Natural Earth country dataset file

        Returns:
            GeoDataFrame: Processed Natural Earth data with proper geometry

        Raises:
            FileNotFoundError: If the file cannot be found
            ValueError: If the file format is unsupported or data cannot be parsed
        """
        # Load Natural Earth data
        if country_path.endswith(".shp"):
            countries_gdf = gpd.read_file(country_path)
        else:
            # Assume it's a CSV with WKT geometry
            countries_df = pd.read_csv(country_path)

            # Parse the WKT geometry, removing the SRID prefix if present
            def parse_wkt(wkt_str):
                if wkt_str.startswith("SRID=4326;"):
                    wkt_str = wkt_str.replace("SRID=4326;", "")
                return wkt.loads(wkt_str)

            countries_df["geometry"] = countries_df["geometry"].apply(parse_wkt)
            countries_gdf = gpd.GeoDataFrame(countries_df, geometry="geometry")

        # Set CRS if not already set
        if countries_gdf.crs is None:
            countries_gdf.set_crs(epsg=4326, inplace=True)

        # Validate data
        self._validate_naturalearth_data(countries_gdf)

        return countries_gdf

    def _validate_naturalearth_data(self, countries_gdf):
        """Validate Natural Earth data for consistency and correctness."""
        # Check for required columns
        required_columns = ["ISO_A3", "NAME_EN", "geometry"]
        missing_columns = [
            col for col in required_columns if col not in countries_gdf.columns
        ]
        if missing_columns:
            raise ValueError(
                f"Missing required columns in Natural Earth data: {missing_columns}"
            )

        # Check geometry validity
        invalid_geometries = countries_gdf[~countries_gdf["geometry"].is_valid]
        if not invalid_geometries.empty:
            logger.warning(
                f"Found {len(invalid_geometries)} invalid geometries in Natural Earth data"
            )

    def _load_priogrid(self, priogrid_path):
        """
        Load and preprocess the PRIO-GRID data from the provided path.

        Parameters:
            priogrid_path (str): Path to the PRIO-GRID dataset file

        Returns:
            GeoDataFrame: Processed PRIO-GRID data with geometry and centroid fields

        Raises:
            FileNotFoundError: If the file cannot be found
            ValueError: If the file format is unsupported or data cannot be parsed
        """
        # Load PRIO-GRID data
        priogrid_gdf = gpd.read_file(priogrid_path)

        # Ensure CRS is set
        if priogrid_gdf.crs is None:
            priogrid_gdf.set_crs(epsg=4326, inplace=True)

        # Calculate centroid of each grid cell for point-in-polygon testing
        priogrid_gdf["centroid"] = priogrid_gdf["geometry"].centroid

        # Validate data
        self._validate_priogrid_data(priogrid_gdf)

        return priogrid_gdf

    def _validate_priogrid_data(self, priogrid_gdf):
        """Validate PRIO-GRID data for consistency and correctness."""
        # Check for required columns
        required_columns = ["gid", "geometry", "centroid"]
        missing_columns = [
            col for col in required_columns if col not in priogrid_gdf.columns
        ]
        if missing_columns:
            raise ValueError(
                f"Missing required columns in PRIO-GRID data: {missing_columns}"
            )

        # Check geometry validity
        invalid_geometries = priogrid_gdf[~priogrid_gdf["geometry"].is_valid]
        if not invalid_geometries.empty:
            logger.warning(
                f"Found {len(invalid_geometries)} invalid geometries in PRIO-GRID data"
            )

    def find_gid_for_point(self, point_geometry):
        """
        Find the PRIO-GRID cell ID that contains a point using spatial index for faster query.

        Parameters:
            point_geometry (shapely.geometry.Point): Point geometry to locate

        Returns:
            int or None: PRIO-GRID cell ID containing the point, or None if not found
        """
        if self.use_disk_cache:
            # Use disk cache
            @self._disk_gid_cache.cache()
            def _find_gid_for_point_impl(point_geometry):
                # Validate input geometry
                if not point_geometry.is_valid:
                    raise ValueError("Invalid point geometry")

                # Not in cache, perform the expensive operation
                if self.priogrid_sindex:
                    possible_matches_index = list(
                        self.priogrid_sindex.intersection(point_geometry.bounds)
                    )
                    possible_matches = self.priogrid_gdf.iloc[possible_matches_index]
                    precise_matches = possible_matches[
                        possible_matches.intersects(point_geometry)
                    ]

                    if len(precise_matches) > 0:
                        result = precise_matches.iloc[0]["gid"]
                    else:
                        result = None
                else:
                    # Fallback to iterative search
                    result = None
                    for _, grid_cell in self.priogrid_gdf.iterrows():
                        if grid_cell["geometry"].contains(point_geometry):
                            result = grid_cell["gid"]
                            break

                return result

            return _find_gid_for_point_impl(point_geometry)
        else:
            # Use in-memory cache
            # Validate input geometry
            if not point_geometry.is_valid:
                raise ValueError("Invalid point geometry")

            # Create a consistent cache key
            cache_key = self._get_point_cache_key(point_geometry)

            # Check cache first
            if cache_key in self._gid_cache:
                return self._gid_cache[cache_key]

            # Not in cache, perform the expensive operation
            if self.priogrid_sindex:
                possible_matches_index = list(
                    self.priogrid_sindex.intersection(point_geometry.bounds)
                )
                possible_matches = self.priogrid_gdf.iloc[possible_matches_index]
                precise_matches = possible_matches[
                    possible_matches.intersects(point_geometry)
                ]

                if len(precise_matches) > 0:
                    result = precise_matches.iloc[0]["gid"]
                else:
                    result = None
            else:
                # Fallback to iterative search
                result = None
                for _, grid_cell in self.priogrid_gdf.iterrows():
                    if grid_cell["geometry"].contains(point_geometry):
                        result = grid_cell["gid"]
                        break

            # Update cache
            self._gid_cache[cache_key] = result
            return result

    def find_country_for_gid(self, gid):
        """
        Find the country information for a PRIO-GRID cell using majority area-based method.
        Now with persistent disk caching.
        """
        if self.use_disk_cache:
            # Use disk cache
            @self._disk_country_cache.cache()
            def _find_country_for_gid_impl(gid):
                # Get the PRIO-GRID cell
                grid_cell = self.priogrid_gdf[self.priogrid_gdf["gid"] == gid]
                if len(grid_cell) == 0:
                    return None

                grid_geometry = grid_cell["geometry"].iloc[0]
                grid_centroid = grid_cell["centroid"].iloc[0]

                # Use spatial index to find potentially intersecting countries
                if hasattr(self.countries_gdf, "sindex"):
                    possible_countries_idx = list(
                        self.countries_gdf.sindex.intersection(grid_geometry.bounds)
                    )
                    candidate_countries = self.countries_gdf.iloc[
                        possible_countries_idx
                    ]
                    candidate_countries = candidate_countries[
                        candidate_countries.intersects(grid_geometry)
                    ]
                else:
                    candidate_countries = self.countries_gdf[
                        self.countries_gdf.intersects(grid_geometry)
                    ]

                # Calculate area overlaps
                overlaps = []
                for _, country in candidate_countries.iterrows():
                    try:
                        intersection = country["geometry"].intersection(grid_geometry)
                        overlap_area = intersection.area
                        total_area = grid_geometry.area
                        overlap_ratio = overlap_area / total_area

                        overlaps.append(
                            {
                                "country_data": country,
                                "overlap_area": overlap_area,
                                "overlap_ratio": overlap_ratio,
                            }
                        )
                    except Exception as e:
                        logger.debug(f"Overlap calculation error for GID {gid}: {e}")
                        continue

                # Sort by overlap ratio (descending)
                overlaps.sort(key=lambda x: x["overlap_ratio"], reverse=True)

                # Assignment rule: always use largest overlap
                result = None
                if overlaps:
                    country = overlaps[0]["country_data"]
                    method_used = "largest overlap"

                # Prepare result
                if overlaps:
                    result = {
                        "gid": int(gid),
                        "iso_a3": country["ISO_A3"],
                        "country_name": country["NAME_EN"],
                        "overlap_ratio": (
                            float(overlaps[0]["overlap_ratio"]) if overlaps else 0.0
                        ),
                        "method": method_used,
                    }

                    # Add all available country data
                    for col in country.index:
                        if col not in ["geometry", "ISO_A3", "NAME_EN"]:
                            result[col] = country[col]

                return result

            return _find_country_for_gid_impl(gid)
        else:
            # Use in-memory cache
            # Generate consistent cache key
            cache_key = self._get_gid_cache_key(gid)

            # Check cache first
            if cache_key in self._country_cache:
                cached_value = self._country_cache[cache_key]
                if cached_value is None:
                    return None
                result = cached_value.copy()
                return result

            # Get the PRIO-GRID cell
            grid_cell = self.priogrid_gdf[self.priogrid_gdf["gid"] == gid]
            if len(grid_cell) == 0:
                self._country_cache[cache_key] = None
                return None

            grid_geometry = grid_cell["geometry"].iloc[0]
            grid_centroid = grid_cell["centroid"].iloc[0]

            # Use spatial index to find potentially intersecting countries
            if hasattr(self.countries_gdf, "sindex"):
                possible_countries_idx = list(
                    self.countries_gdf.sindex.intersection(grid_geometry.bounds)
                )
                candidate_countries = self.countries_gdf.iloc[possible_countries_idx]
                candidate_countries = candidate_countries[
                    candidate_countries.intersects(grid_geometry)
                ]
            else:
                candidate_countries = self.countries_gdf[
                    self.countries_gdf.intersects(grid_geometry)
                ]

            # Calculate area overlaps
            overlaps = []
            for _, country in candidate_countries.iterrows():
                try:
                    intersection = country["geometry"].intersection(grid_geometry)
                    overlap_area = intersection.area
                    total_area = grid_geometry.area
                    overlap_ratio = overlap_area / total_area

                    overlaps.append(
                        {
                            "country_data": country,
                            "overlap_area": overlap_area,
                            "overlap_ratio": overlap_ratio,
                        }
                    )
                except Exception as e:
                    logger.debug(f"Overlap calculation error for GID {gid}: {e}")
                    continue

            # Sort by overlap ratio (descending)
            overlaps.sort(key=lambda x: x["overlap_ratio"], reverse=True)

            # Assignment rule: always use largest overlap
            result = None
            if overlaps:
                country = overlaps[0]["country_data"]
                method_used = "largest overlap"

            # Prepare result
            if overlaps:
                result = {
                    "gid": int(gid),
                    "iso_a3": country["ISO_A3"],
                    "country_name": country["NAME_EN"],
                    "overlap_ratio": (
                        float(overlaps[0]["overlap_ratio"]) if overlaps else 0.0
                    ),
                    "method": method_used,
                }

                # Add all available country data
                for col in country.index:
                    if col not in ["geometry", "ISO_A3", "NAME_EN"]:
                        result[col] = country[col]

            # Update cache
            self._country_cache[cache_key] = result
            return result

    def batch_country_mapping(self, gid_list):
        """
        Optimized batch mapping using vectorized operations where possible.
        """
        results = []
        cache_hits = 0

        for gid in gid_list:
            # Check cache first
            cache_key = self._get_gid_cache_key(gid)
            if cache_key in self._country_cache:
                cached_value = self._country_cache[cache_key]
                if cached_value is not None:
                    results.append(cached_value.copy())
                else:
                    results.append(None)
                cache_hits += 1
                continue

            # Not in cache, process this GID
            result = self.find_country_for_gid(gid)
            results.append(result)

        if cache_hits > 0:
            logger.info(
                f"Cache hits: {cache_hits}/{len(gid_list)} ({cache_hits/len(gid_list)*100:.1f}%)"
            )

        return pd.DataFrame([r for r in results if r is not None])

    def find_gids_for_country(self, iso_a3):
        """
        Find all PRIO-GRID cells that belong to a specific country.
        Optimized using spatial indexing and vectorized operations.
        """
        if self.use_disk_cache:
            # Use disk cache
            @self._disk_country_cache.cache()
            def _find_gids_for_country_impl(iso_a3):
                # Filter Natural Earth data for the specific country
                country = self.countries_gdf[self.countries_gdf["ISO_A3"] == iso_a3]

                if len(country) == 0:
                    return []
                else:
                    # Get the country geometry
                    country_geometry = country.iloc[0]["geometry"]

                    # OPTIMIZATION: Use spatial index to quickly find intersecting grid cells
                    if self.priogrid_sindex:
                        possible_matches_index = list(
                            self.priogrid_sindex.intersection(country_geometry.bounds)
                        )
                        candidate_grid_cells = self.priogrid_gdf.iloc[
                            possible_matches_index
                        ]
                        intersecting_cells = candidate_grid_cells[
                            candidate_grid_cells.intersects(country_geometry)
                        ]
                    else:
                        intersecting_cells = self.priogrid_gdf[
                            self.priogrid_gdf.intersects(country_geometry)
                        ]

                    if len(intersecting_cells) == 0:
                        result = []
                    else:
                        # OPTIMIZATION: Process with early termination
                        matching_gids = self._find_dominant_country_gids(
                            intersecting_cells, country_geometry, iso_a3
                        )
                        result = matching_gids

                return result

            return _find_gids_for_country_impl(iso_a3)
        else:
            # Use in-memory cache
            # Create consistent cache key
            cache_key = self._get_country_cache_key(iso_a3)

            # Check cache first
            if cache_key in self._gids_for_country_cache:
                result = self._gids_for_country_cache[cache_key]
                return result

            # Not in cache, perform optimized operation
            # Filter Natural Earth data for the specific country
            country = self.countries_gdf[self.countries_gdf["ISO_A3"] == iso_a3]

            if len(country) == 0:
                result = []
            else:
                # Get the country geometry
                country_geometry = country.iloc[0]["geometry"]

                # OPTIMIZATION: Use spatial index to quickly find intersecting grid cells
                if self.priogrid_sindex:
                    possible_matches_index = list(
                        self.priogrid_sindex.intersection(country_geometry.bounds)
                    )
                    candidate_grid_cells = self.priogrid_gdf.iloc[
                        possible_matches_index
                    ]
                    intersecting_cells = candidate_grid_cells[
                        candidate_grid_cells.intersects(country_geometry)
                    ]
                else:
                    intersecting_cells = self.priogrid_gdf[
                        self.priogrid_gdf.intersects(country_geometry)
                    ]

                if len(intersecting_cells) == 0:
                    result = []
                else:
                    # OPTIMIZATION: Process with early termination
                    matching_gids = self._find_dominant_country_gids(
                        intersecting_cells, country_geometry, iso_a3
                    )
                    result = matching_gids

            # Update cache
            self._gids_for_country_cache[cache_key] = result
            return result

    def _find_dominant_country_gids(self, intersecting_cells, country_geometry, iso_a3):
        """Find grid cells where target country has dominant area using optimized approach."""
        matching_gids = []

        for _, grid_cell in intersecting_cells.iterrows():
            grid_geometry = grid_cell["geometry"]
            grid_gid = grid_cell["gid"]

            # OPTIMIZATION 1: Early check for complete containment
            if country_geometry.contains(grid_geometry):
                matching_gids.append(int(grid_gid))
                continue

            # Calculate overlap with the target country
            try:
                intersection = country_geometry.intersection(grid_geometry)
                overlap_ratio = intersection.area / grid_geometry.area

                # If overlap is significant, include it
                if overlap_ratio > 0.5:
                    matching_gids.append(int(grid_gid))
            except Exception as e:
                # Handle potential geometry errors gracefully
                logger.debug(f"Geometry error for GID {grid_gid}: {e}")
                continue

        return matching_gids

    def get_all_iso_a3_codes(self):
        """
        Get a list of all unique ISO A3 codes in the Natural Earth dataset.

        Returns:
            list: List of unique ISO A3 codes
        """
        return self.countries_gdf["ISO_A3"].unique().tolist()

    def visualize_grid_and_country(self, gid):
        """
        Visualize a PRIO-GRID cell and the country it belongs to.

        Parameters:
            gid (int): PRIO-GRID cell ID

        Raises:
            ImportError: If matplotlib is not available
            ValueError: If the PRIO-GRID cell ID is not found
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.error("Matplotlib is required for visualization")
            return

        # Get the grid cell
        grid_cell = self.priogrid_gdf[self.priogrid_gdf["gid"] == gid]

        if len(grid_cell) == 0:
            raise ValueError(f"PRIO-GRID cell with ID {gid} not found")

        # Find which country contains the grid cell based on majority area
        country_info = self.find_country_for_gid(gid)
        containing_country = None

        if country_info:
            iso_a3 = country_info["iso_a3"]
            containing_country = self.countries_gdf[
                self.countries_gdf["ISO_A3"] == iso_a3
            ].iloc[0]

        # Create plot
        fig, ax = plt.subplots(1, 1, figsize=(10, 8))

        # Plot all countries
        self.countries_gdf.plot(ax=ax, color="lightgray", edgecolor="white", alpha=0.5)

        # Highlight the containing country
        if containing_country is not None:
            gpd.GeoDataFrame([containing_country], geometry="geometry").plot(
                ax=ax, color="lightblue", edgecolor="blue", alpha=0.7
            )

        # Plot the grid cell
        grid_cell.plot(ax=ax, color="red", alpha=0.7)

        # Add centroid marker
        centroid = grid_cell["centroid"].iloc[0]
        ax.scatter(
            centroid.x,
            centroid.y,
            color="yellow",
            s=100,
            marker="*",
            edgecolor="black",
            label="Grid Centroid",
        )

        # Set title and legend
        country_name = (
            containing_country["NAME_EN"]
            if containing_country is not None
            else "No Country"
        )
        method = country_info.get("method", "unknown") if country_info else "unknown"
        overlap_ratio = country_info.get("overlap_ratio", 0) if country_info else 0

        ax.set_title(
            f"PRIO-GRID Cell {gid} in {country_name}\n"
            f"Method: {method} | Overlap Ratio: {overlap_ratio:.3f}"
        )
        ax.legend()

        plt.tight_layout()
        plt.show()

    def calculate_capital_distance(self, grid_lat, grid_lon, capital_coords):
        """
        Calculate distance from grid cell to capital.

        Parameters:
            grid_lat: Latitude of grid centroid
            grid_lon: Longitude of grid centroid
            capital_coords: Tuple of (capital_lon, capital_lat) or None

        Returns:
            float or None: Distance in kilometers or None if calculation fails
        """
        if capital_coords is None or None in capital_coords:
            return None

        try:
            capital_lon, capital_lat = capital_coords
            return cached_haversine(grid_lat, grid_lon, capital_lat, capital_lon)
        except Exception as e:
            logger.error(f"Error calculating capital distance: {e}")
            return None

    def get_gid_from_point(self, point: ShapelyPoint) -> Optional[int]:
        """
        Find the PRIO-GRID cell ID that contains a point.

        Parameters:
            point (ShapelyPoint): Point geometry to locate

        Returns:
            int or None: PRIO-GRID cell ID containing the point, or None if not found
        """
        for _, grid_cell in self.priogrid_gdf.iterrows():
            if grid_cell["geometry"].contains(point):
                return grid_cell["gid"]
        return None

    def get_point_from_gid(self, gid: int) -> Optional["Point"]:
        """
        Get the centroid point of a PRIO-GRID cell.

        Parameters:
            gid (int): PRIO-GRID cell ID

        Returns:
            Point or None: Point object representing the centroid, or None if not found
        """
        # from ..space import Point
        grid_cell = self.priogrid_gdf[self.priogrid_gdf["gid"] == gid]
        if len(grid_cell) == 0:
            return None
        centroid = grid_cell["centroid"].iloc[0]
        return Point(lat=centroid.y, lon=centroid.x)

    def _load_admin_data(self, admin_path, admin_level):
        """
        Load and preprocess admin1 or admin2 data from the provided path.

        Parameters:
            admin_path (str): Path to the admin dataset file
            admin_level (str): Either "admin1" or "admin2"

        Returns:
            GeoDataFrame: Processed admin data with proper geometry
        """
        # Load admin data
        if admin_path.endswith(".shp"):
            admin_gdf = gpd.read_file(admin_path)
        else:
            # Assume it's a CSV with WKT geometry
            admin_df = pd.read_csv(admin_path)

            # Parse the WKT geometry, removing the SRID prefix if present
            def parse_wkt(wkt_str):
                if wkt_str.startswith("SRID=4326;"):
                    wkt_str = wkt_str.replace("SRID=4326;", "")
                return wkt.loads(wkt_str)

            admin_df["geometry"] = admin_df["geometry"].apply(parse_wkt)
            admin_gdf = gpd.GeoDataFrame(admin_df, geometry="geometry")

        # Set CRS if not already set
        if admin_gdf.crs is None:
            admin_gdf.set_crs(epsg=4326, inplace=True)

        # Validate data
        self._validate_admin_data(admin_gdf, admin_level)

        return admin_gdf

    def _validate_admin_data(self, admin_gdf, admin_level):
        """Validate admin data for consistency and correctness."""
        # Check for required columns based on admin level
        if admin_level == "admin1":
            required_columns = ["gaul1_code", "gaul1_name", "iso3_code", "geometry"]
        else:  # admin2
            required_columns = ["gaul2_code", "gaul2_name", "iso3_code", "geometry"]

        missing_columns = [
            col for col in required_columns if col not in admin_gdf.columns
        ]
        if missing_columns:
            raise ValueError(
                f"Missing required columns in {admin_level} data: {missing_columns}"
            )

        # Check geometry validity
        invalid_geometries = admin_gdf[~admin_gdf["geometry"].is_valid]
        if not invalid_geometries.empty:
            logger.warning(
                f"Found {len(invalid_geometries)} invalid geometries in {admin_level} data"
            )

    def find_admin1_for_gid(self, gid):
        """
        Find the admin1 information for a PRIO-GRID cell.
        First determines the country, then finds the admin1 region within that country.
        Now with persistent disk caching.
        """
        if self.admin1_gdf is None:
            logger.warning("Admin1 data not loaded. Cannot find admin1 for GID.")
            return None

        if self.use_disk_cache:
            # Use disk cache
            @self._disk_admin1_cache.cache()
            def _find_admin1_for_gid_impl(gid):
                # First find the country for this GID
                country_info = self.find_country_for_gid(gid)
                if not country_info:
                    return None

                iso_a3 = country_info["iso_a3"]

                # Get the PRIO-GRID cell
                grid_cell = self.priogrid_gdf[self.priogrid_gdf["gid"] == gid]
                if len(grid_cell) == 0:
                    return None

                grid_geometry = grid_cell["geometry"].iloc[0]

                # Filter admin1 regions to only those in the same country
                country_admin1 = self.admin1_gdf[self.admin1_gdf["iso3_code"] == iso_a3]

                if len(country_admin1) == 0:
                    return None

                # Use spatial index to find potentially intersecting admin1 regions
                if self.admin1_sindex:
                    possible_admin1_idx = list(
                        self.admin1_sindex.intersection(grid_geometry.bounds)
                    )
                    candidate_admin1 = self.admin1_gdf.iloc[possible_admin1_idx]
                    candidate_admin1 = candidate_admin1[
                        candidate_admin1.intersects(grid_geometry)
                    ]
                    # Filter to only those in the same country
                    candidate_admin1 = candidate_admin1[
                        candidate_admin1["iso3_code"] == iso_a3
                    ]
                else:
                    candidate_admin1 = country_admin1[
                        country_admin1.intersects(grid_geometry)
                    ]

                if len(candidate_admin1) == 0:
                    return None

                # Calculate overlaps and use largest overlap
                overlaps = []
                for _, admin1 in candidate_admin1.iterrows():
                    try:
                        intersection = admin1["geometry"].intersection(grid_geometry)
                        overlap_area = intersection.area
                        total_area = grid_geometry.area
                        overlap_ratio = overlap_area / total_area

                        overlaps.append(
                            {
                                "admin1_data": admin1,
                                "overlap_area": overlap_area,
                                "overlap_ratio": overlap_ratio,
                            }
                        )
                    except Exception as e:
                        logger.debug(f"Overlap calculation error for GID {gid}: {e}")
                        continue

                # Sort by overlap ratio (descending)
                overlaps.sort(key=lambda x: x["overlap_ratio"], reverse=True)

                if not overlaps:
                    return None

                admin1 = overlaps[0]["admin1_data"]
                method_used = "largest overlap"

                # Prepare result
                result = {
                    "gid": int(gid),
                    "gaul1_code": (
                        int(admin1["gaul1_code"])
                        if admin1["gaul1_code"] is not None
                        else None
                    ),
                    "gaul1_name": admin1["gaul1_name"],
                    "iso3_code": admin1["iso3_code"],
                    "method": method_used,
                }

                # Add additional fields if available
                if "gaul0_code" in admin1:
                    result["gaul0_code"] = (
                        int(admin1["gaul0_code"])
                        if admin1["gaul0_code"] is not None
                        else None
                    )
                if "gaul0_name" in admin1:
                    result["gaul0_name"] = admin1["gaul0_name"]
                if "continent" in admin1:
                    result["continent"] = admin1["continent"]
                if "disp_en" in admin1:
                    result["disp_en"] = admin1["disp_en"]

                return result

            return _find_admin1_for_gid_impl(gid)
        else:
            # Use in-memory cache
            # Generate consistent cache key
            cache_key = self._get_admin_cache_key(gid, "admin1")

            # Check cache first
            if cache_key in self._admin1_cache:
                cached_value = self._admin1_cache[cache_key]
                if cached_value is not None:
                    result = cached_value.copy()
                    return result
                else:
                    return None

            # First find the country for this GID
            country_info = self.find_country_for_gid(gid)
            if not country_info:
                self._admin1_cache[cache_key] = None
                return None

            iso_a3 = country_info["iso_a3"]

            # Get the PRIO-GRID cell
            grid_cell = self.priogrid_gdf[self.priogrid_gdf["gid"] == gid]
            if len(grid_cell) == 0:
                self._admin1_cache[cache_key] = None
                return None

            grid_geometry = grid_cell["geometry"].iloc[0]

            # Filter admin1 regions to only those in the same country
            country_admin1 = self.admin1_gdf[self.admin1_gdf["iso3_code"] == iso_a3]

            if len(country_admin1) == 0:
                self._admin1_cache[cache_key] = None
                return None

            # Use spatial index to find potentially intersecting admin1 regions
            if self.admin1_sindex:
                possible_admin1_idx = list(
                    self.admin1_sindex.intersection(grid_geometry.bounds)
                )
                candidate_admin1 = self.admin1_gdf.iloc[possible_admin1_idx]
                candidate_admin1 = candidate_admin1[
                    candidate_admin1.intersects(grid_geometry)
                ]
                # Filter to only those in the same country
                candidate_admin1 = candidate_admin1[
                    candidate_admin1["iso3_code"] == iso_a3
                ]
            else:
                candidate_admin1 = country_admin1[
                    country_admin1.intersects(grid_geometry)
                ]

            if len(candidate_admin1) == 0:
                self._admin1_cache[cache_key] = None
                return None

            # Calculate overlaps and use largest overlap
            overlaps = []
            for _, admin1 in candidate_admin1.iterrows():
                try:
                    intersection = admin1["geometry"].intersection(grid_geometry)
                    overlap_area = intersection.area
                    total_area = grid_geometry.area
                    overlap_ratio = overlap_area / total_area

                    overlaps.append(
                        {
                            "admin1_data": admin1,
                            "overlap_area": overlap_area,
                            "overlap_ratio": overlap_ratio,
                        }
                    )
                except Exception as e:
                    logger.debug(f"Overlap calculation error for GID {gid}: {e}")
                    continue

            # Sort by overlap ratio (descending)
            overlaps.sort(key=lambda x: x["overlap_ratio"], reverse=True)

            if not overlaps:
                self._admin1_cache[cache_key] = None
                return None

            admin1 = overlaps[0]["admin1_data"]
            method_used = "largest overlap"

            # Prepare result
            result = {
                "gid": int(gid),
                "gaul1_code": (
                    int(admin1["gaul1_code"])
                    if admin1["gaul1_code"] is not None
                    else None
                ),
                "gaul1_name": admin1["gaul1_name"],
                "iso3_code": admin1["iso3_code"],
                "method": method_used,
            }

            # Add additional fields if available
            if "gaul0_code" in admin1:
                result["gaul0_code"] = (
                    int(admin1["gaul0_code"])
                    if admin1["gaul0_code"] is not None
                    else None
                )
            if "gaul0_name" in admin1:
                result["gaul0_name"] = admin1["gaul0_name"]
            if "continent" in admin1:
                result["continent"] = admin1["continent"]
            if "disp_en" in admin1:
                result["disp_en"] = admin1["disp_en"]

            # Update cache
            self._admin1_cache[cache_key] = result
            return result

    def find_admin2_for_gid(self, gid):
        """
        Find the admin2 information for a PRIO-GRID cell.
        First determines the country, then finds the admin2 region within that country.
        Now with persistent disk caching.
        """
        if self.admin2_gdf is None:
            logger.warning("Admin2 data not loaded. Cannot find admin2 for GID.")
            return None

        if self.use_disk_cache:
            # Use disk cache
            @self._disk_admin2_cache.cache()
            def _find_admin2_for_gid_impl(gid):
                # First find the country for this GID
                country_info = self.find_country_for_gid(gid)
                if not country_info:
                    return None

                iso_a3 = country_info["iso_a3"]

                # Get the PRIO-GRID cell
                grid_cell = self.priogrid_gdf[self.priogrid_gdf["gid"] == gid]
                if len(grid_cell) == 0:
                    return None

                grid_geometry = grid_cell["geometry"].iloc[0]

                # Filter admin2 regions to only those in the same country
                country_admin2 = self.admin2_gdf[self.admin2_gdf["iso3_code"] == iso_a3]

                if len(country_admin2) == 0:
                    return None

                # Use spatial index to find potentially intersecting admin2 regions
                if self.admin2_sindex:
                    possible_admin2_idx = list(
                        self.admin2_sindex.intersection(grid_geometry.bounds)
                    )
                    candidate_admin2 = self.admin2_gdf.iloc[possible_admin2_idx]
                    candidate_admin2 = candidate_admin2[
                        candidate_admin2.intersects(grid_geometry)
                    ]
                    # Filter to only those in the same country
                    candidate_admin2 = candidate_admin2[
                        candidate_admin2["iso3_code"] == iso_a3
                    ]
                else:
                    candidate_admin2 = country_admin2[
                        country_admin2.intersects(grid_geometry)
                    ]

                if len(candidate_admin2) == 0:
                    return None

                # Calculate overlaps and use largest overlap
                overlaps = []
                for _, admin2 in candidate_admin2.iterrows():
                    try:
                        intersection = admin2["geometry"].intersection(grid_geometry)
                        overlap_area = intersection.area
                        total_area = grid_geometry.area
                        overlap_ratio = overlap_area / total_area

                        overlaps.append(
                            {
                                "admin2_data": admin2,
                                "overlap_area": overlap_area,
                                "overlap_ratio": overlap_ratio,
                            }
                        )
                    except Exception as e:
                        logger.debug(f"Overlap calculation error for GID {gid}: {e}")
                        continue

                # Sort by overlap ratio (descending)
                overlaps.sort(key=lambda x: x["overlap_ratio"], reverse=True)

                if not overlaps:
                    return None

                admin2 = overlaps[0]["admin2_data"]
                method_used = "largest overlap"

                # Prepare result
                result = {
                    "gid": int(gid),
                    "gaul2_code": (
                        int(admin2["gaul2_code"])
                        if admin2["gaul2_code"] is not None
                        else None
                    ),
                    "gaul2_name": admin2["gaul2_name"],
                    "iso3_code": admin2["iso3_code"],
                    "method": method_used,
                }

                # Add additional fields if available
                if "gaul0_code" in admin2:
                    result["gaul0_code"] = (
                        int(admin2["gaul0_code"])
                        if admin2["gaul0_code"] is not None
                        else None
                    )
                if "gaul0_name" in admin2:
                    result["gaul0_name"] = admin2["gaul0_name"]
                if "gaul1_code" in admin2:
                    result["gaul1_code"] = (
                        int(admin2["gaul1_code"])
                        if admin2["gaul1_code"] is not None
                        else None
                    )
                if "gaul1_name" in admin2:
                    result["gaul1_name"] = admin2["gaul1_name"]
                if "continent" in admin2:
                    result["continent"] = admin2["continent"]
                if "disp_en" in admin2:
                    result["disp_en"] = admin2["disp_en"]

                return result

            return _find_admin2_for_gid_impl(gid)
        else:
            # Use in-memory cache
            # Generate consistent cache key
            cache_key = self._get_admin_cache_key(gid, "admin2")

            # Check cache first
            if cache_key in self._admin2_cache:
                cached_value = self._admin2_cache[cache_key]
                if cached_value is not None:
                    result = cached_value.copy()
                    return result
                else:
                    return None

            # First find the country for this GID
            country_info = self.find_country_for_gid(gid)
            if not country_info:
                self._admin2_cache[cache_key] = None
                return None

            iso_a3 = country_info["iso_a3"]

            # Get the PRIO-GRID cell
            grid_cell = self.priogrid_gdf[self.priogrid_gdf["gid"] == gid]
            if len(grid_cell) == 0:
                self._admin2_cache[cache_key] = None
                return None

            grid_geometry = grid_cell["geometry"].iloc[0]

            # Filter admin2 regions to only those in the same country
            country_admin2 = self.admin2_gdf[self.admin2_gdf["iso3_code"] == iso_a3]

            if len(country_admin2) == 0:
                self._admin2_cache[cache_key] = None
                return None

            # Use spatial index to find potentially intersecting admin2 regions
            if self.admin2_sindex:
                possible_admin2_idx = list(
                    self.admin2_sindex.intersection(grid_geometry.bounds)
                )
                candidate_admin2 = self.admin2_gdf.iloc[possible_admin2_idx]
                candidate_admin2 = candidate_admin2[
                    candidate_admin2.intersects(grid_geometry)
                ]
                # Filter to only those in the same country
                candidate_admin2 = candidate_admin2[
                    candidate_admin2["iso3_code"] == iso_a3
                ]
            else:
                candidate_admin2 = country_admin2[
                    country_admin2.intersects(grid_geometry)
                ]

            if len(candidate_admin2) == 0:
                self._admin2_cache[cache_key] = None
                return None

            # Calculate overlaps and use largest overlap
            overlaps = []
            for _, admin2 in candidate_admin2.iterrows():
                try:
                    intersection = admin2["geometry"].intersection(grid_geometry)
                    overlap_area = intersection.area
                    total_area = grid_geometry.area
                    overlap_ratio = overlap_area / total_area

                    overlaps.append(
                        {
                            "admin2_data": admin2,
                            "overlap_area": overlap_area,
                            "overlap_ratio": overlap_ratio,
                        }
                    )
                except Exception as e:
                    logger.debug(f"Overlap calculation error for GID {gid}: {e}")
                    continue

            # Sort by overlap ratio (descending)
            overlaps.sort(key=lambda x: x["overlap_ratio"], reverse=True)

            if not overlaps:
                self._admin2_cache[cache_key] = None
                return None

            admin2 = overlaps[0]["admin2_data"]
            method_used = "largest overlap"

            # Prepare result
            result = {
                "gid": int(gid),
                "gaul2_code": (
                    int(admin2["gaul2_code"])
                    if admin2["gaul2_code"] is not None
                    else None
                ),
                "gaul2_name": admin2["gaul2_name"],
                "iso3_code": admin2["iso3_code"],
                "method": method_used,
            }

            # Add additional fields if available
            if "gaul0_code" in admin2:
                result["gaul0_code"] = (
                    int(admin2["gaul0_code"])
                    if admin2["gaul0_code"] is not None
                    else None
                )
            if "gaul0_name" in admin2:
                result["gaul0_name"] = admin2["gaul0_name"]
            if "gaul1_code" in admin2:
                result["gaul1_code"] = (
                    int(admin2["gaul1_code"])
                    if admin2["gaul1_code"] is not None
                    else None
                )
            if "gaul1_name" in admin2:
                result["gaul1_name"] = admin2["gaul1_name"]
            if "continent" in admin2:
                result["continent"] = admin2["continent"]
            if "disp_en" in admin2:
                result["disp_en"] = admin2["disp_en"]

            # Update cache
            self._admin2_cache[cache_key] = result
            return result

    def find_all_admin_for_gid(self, gid):
        """
        Find country, admin1, and admin2 information for a PRIO-GRID cell.

        Parameters:
            gid (int): PRIO-GRID cell ID

        Returns:
            dict: Combined information for country, admin1, and admin2
        """
        result = {"gid": int(gid)}

        # Find country information
        country_info = self.find_country_for_gid(gid)
        if country_info:
            result["country"] = country_info

        # Find admin1 information
        admin1_info = self.find_admin1_for_gid(gid)
        if admin1_info:
            result["admin1"] = admin1_info

        # Find admin2 information
        admin2_info = self.find_admin2_for_gid(gid)
        if admin2_info:
            result["admin2"] = admin2_info

        return result

    def batch_admin_mapping(self, gid_list, admin_level="admin1"):
        """
        Batch mapping for admin1 or admin2 using vectorized operations.

        Parameters:
            gid_list (list): List of PRIO-GRID cell IDs
            admin_level (str): Either "admin1" or "admin2"

        Returns:
            DataFrame: Results of the batch mapping
        """
        if admin_level not in ["admin1", "admin2"]:
            raise ValueError("admin_level must be either 'admin1' or 'admin2'")

        if admin_level == "admin1" and self.admin1_gdf is None:
            raise ValueError("Admin1 data not loaded")
        if admin_level == "admin2" and self.admin2_gdf is None:
            raise ValueError("Admin2 data not loaded")

        # Select the appropriate find function
        if admin_level == "admin1":
            find_func = self.find_admin1_for_gid
            cache = self._admin1_cache
        else:  # admin2
            find_func = self.find_admin2_for_gid
            cache = self._admin2_cache

        results = []
        cache_hits = 0

        for gid in gid_list:
            # Check cache first
            cache_key = self._get_admin_cache_key(gid, admin_level)
            if cache_key in cache:
                cached_value = cache[cache_key]
                if cached_value is not None:
                    results.append(cached_value.copy())
                else:
                    results.append(None)
                cache_hits += 1
                continue

            # Not in cache, process this GID
            result = find_func(gid)
            results.append(result)

        if cache_hits > 0:
            logger.info(
                f"Cache hits: {cache_hits}/{len(gid_list)} ({cache_hits/len(gid_list)*100:.1f}%)"
            )

        return pd.DataFrame([r for r in results if r is not None])

    def batch_admin_mapping_parallel(
        self, gid_list, admin_level="admin1", batch_size=1000
    ):
        """
        Batch mapping for admin1 or admin2 using multiprocessing.

        Parameters:
            gid_list (list): List of PRIO-GRID cell IDs
            admin_level (str): Either "admin1" or "admin2"
            batch_size (int): Number of GIDs to process in each batch

        Returns:
            DataFrame: Results of the batch mapping
        """
        if admin_level not in ["admin1", "admin2"]:
            raise ValueError("admin_level must be either 'admin1' or 'admin2'")

        if admin_level == "admin1" and self.admin1_gdf is None:
            raise ValueError("Admin1 data not loaded")
        if admin_level == "admin2" and self.admin2_gdf is None:
            raise ValueError("Admin2 data not loaded")

        self._init_process_pool()

        # Split into batches
        batches = [
            gid_list[i : i + batch_size] for i in range(0, len(gid_list), batch_size)
        ]

        # Select the appropriate find function
        if admin_level == "admin1":
            find_func = self.find_admin1_for_gid
        else:  # admin2
            find_func = self.find_admin2_for_gid

        # Create partial function for mapping
        map_func = partial(self._process_gid_batch_admin, find_func=find_func)

        # Process batches in parallel
        results = []
        for batch_result in self._process_pool.imap_unordered(map_func, batches):
            results.extend(batch_result)

        return pd.DataFrame(results)

    def _process_gid_batch_admin(self, gid_batch, find_func):
        """Process a batch of GIDs in a single process for admin mapping"""
        batch_results = []
        for gid in gid_batch:
            result = find_func(gid)
            batch_results.append(result)
        return batch_results

    def find_all_admin_for_point(self, point_geometry):
        """
        Find country, admin1, and admin2 information for a point.

        Parameters:
            point_geometry (shapely.geometry.Point): Point geometry to locate

        Returns:
            dict: Combined information for country, admin1, and admin2
        """
        # Find the GID for the point
        gid = self.find_gid_for_point(point_geometry)
        if gid is None:
            return None

        # Use the existing method to find all admin information
        return self.find_all_admin_for_gid(gid)

    def extend_find_country_for_gid(self, gid):
        """
        Extended version of find_country_for_gid that also includes admin1 and admin2 information.

        Parameters:
            gid (int): PRIO-GRID cell ID

        Returns:
            dict: Combined information for country, admin1, and admin2
        """
        # Get country information using the existing method
        result = self.find_country_for_gid(gid)

        if result is None:
            return None

        # Add admin1 information
        admin1_info = self.find_admin1_for_gid(gid)
        if admin1_info:
            result["admin1"] = admin1_info

        # Add admin2 information
        admin2_info = self.find_admin2_for_gid(gid)
        if admin2_info:
            result["admin2"] = admin2_info

        return result

    def visualize_grid_and_admin(
        self, gid, admin_level="admin1", show_all_admins=False
    ):
        """
        Visualize a PRIO-GRID cell and its corresponding admin1 or admin2 boundary.

        Parameters:
            gid (int): PRIO-GRID cell ID
            admin_level (str): Either "admin1" or "admin2"
            show_all_admins (bool): If True, shows all admin regions in the area,
                                otherwise only shows the one containing the grid cell

        Raises:
            ImportError: If matplotlib is not available
            ValueError: If the PRIO-GRID cell ID is not found or admin data is not loaded
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
        except ImportError:
            logger.error("Matplotlib is required for visualization")
            return

        if admin_level not in ["admin1", "admin2"]:
            raise ValueError("admin_level must be either 'admin1' or 'admin2'")

        # Check if admin data is loaded
        if admin_level == "admin1" and self.admin1_gdf is None:
            raise ValueError("Admin1 data not loaded. Cannot visualize admin1.")
        if admin_level == "admin2" and self.admin2_gdf is None:
            raise ValueError("Admin2 data not loaded. Cannot visualize admin2.")

        # Get the grid cell
        grid_cell = self.priogrid_gdf[self.priogrid_gdf["gid"] == gid]
        if len(grid_cell) == 0:
            raise ValueError(f"PRIO-GRID cell with ID {gid} not found")

        grid_geometry = grid_cell["geometry"].iloc[0]
        grid_centroid = grid_cell["centroid"].iloc[0]

        # Select appropriate admin data
        if admin_level == "admin1":
            admin_gdf = self.admin1_gdf
            admin_code_col = "gaul1_code"
            admin_name_col = "gaul1_name"
            find_func = self.find_admin1_for_gid
        else:  # admin2
            admin_gdf = self.admin2_gdf
            admin_code_col = "gaul2_code"
            admin_name_col = "gaul2_name"
            find_func = self.find_admin2_for_gid

        # Find the admin region containing the grid cell
        admin_info = find_func(gid)

        # Create plot
        fig, ax = plt.subplots(1, 1, figsize=(12, 10))

        if show_all_admins:
            # Show all admin regions that intersect with the grid cell's bounds
            if admin_level == "admin1" and self.admin1_sindex:
                possible_admins_idx = list(
                    self.admin1_sindex.intersection(grid_geometry.bounds)
                )
                nearby_admins = self.admin1_gdf.iloc[possible_admins_idx]
            elif admin_level == "admin2" and self.admin2_sindex:
                possible_admins_idx = list(
                    self.admin2_sindex.intersection(grid_geometry.bounds)
                )
                nearby_admins = self.admin2_gdf.iloc[possible_admins_idx]
            else:
                nearby_admins = admin_gdf[admin_gdf.intersects(grid_geometry.buffer(1))]

            # Plot all nearby admin regions
            nearby_admins.plot(
                ax=ax, color="lightgray", edgecolor="white", alpha=0.5, linewidth=0.5
            )

            # Highlight the containing admin region if found
            if admin_info:
                containing_admin = admin_gdf[
                    admin_gdf[admin_code_col] == admin_info[admin_code_col]
                ]
                if len(containing_admin) > 0:
                    containing_admin.plot(
                        ax=ax,
                        color="lightblue",
                        edgecolor="blue",
                        alpha=0.7,
                        linewidth=1.5,
                    )
        else:
            # Only show the containing admin region
            if admin_info:
                containing_admin = admin_gdf[
                    admin_gdf[admin_code_col] == admin_info[admin_code_col]
                ]
                if len(containing_admin) > 0:
                    containing_admin.plot(
                        ax=ax,
                        color="lightblue",
                        edgecolor="blue",
                        alpha=0.7,
                        linewidth=1.5,
                    )

        # Plot the grid cell
        grid_cell.plot(ax=ax, color="red", alpha=0.8, edgecolor="darkred", linewidth=2)

        # Add centroid marker
        ax.scatter(
            grid_centroid.x,
            grid_centroid.y,
            color="yellow",
            s=150,
            marker="*",
            edgecolor="black",
            linewidth=1,
            label="Grid Centroid",
            zorder=5,
        )

        # Set title and legend
        if admin_info:
            admin_name = admin_info[admin_name_col]
            admin_code = admin_info[admin_code_col]
            method = admin_info.get("method", "unknown")

            title = f"PRIO-GRID Cell {gid} in {admin_level.upper()} {admin_name} (Code: {admin_code})\n"
            title += f"Method: {method}"
        else:
            title = f"PRIO-GRID Cell {gid} - No {admin_level.upper()} region found"

        ax.set_title(title, fontsize=14, fontweight="bold")

        # Create legend
        legend_elements = [
            mpatches.Patch(color="red", alpha=0.8, label="PRIO-GRID Cell"),
            mpatches.Patch(
                color="lightblue", alpha=0.7, label=f"Containing {admin_level.upper()}"
            ),
            mpatches.Patch(
                color="lightgray",
                alpha=0.5,
                label="Other Admin Regions" if show_all_admins else None,
            ),
        ]

        # Filter out None values
        legend_elements = [e for e in legend_elements if e.get_label() is not None]

        ax.legend(handles=legend_elements, loc="upper right", bbox_to_anchor=(1, 1))

        # Add grid coordinates as text
        ax.text(
            grid_centroid.x,
            grid_centroid.y - 0.1,
            f'GID: {gid}\n({grid_cell["xcoord"].iloc[0]:.1f}, {grid_cell["ycoord"].iloc[0]:.1f})',
            ha="center",
            va="top",
            fontsize=9,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8),
        )

        # Set aspect ratio and remove unnecessary axes
        ax.set_aspect("equal")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.show()

    def visualize_admin_regions_for_gids(
        self,
        gid_list,
        admin_level="admin1",
        show_grid_cells=True,
        color_by_country=True,
        figsize=(15, 10),
    ):
        """
        Visualize admin1 or admin2 regions for multiple PRIO-GRID cells.

        Parameters:
            gid_list (list): List of PRIO-GRID cell IDs
            admin_level (str): Either "admin1" or "admin2"
            show_grid_cells (bool): Whether to show the PRIO-GRID cells on the map
            color_by_country (bool): If True, colors admin regions by country
            figsize (tuple): Figure size (width, height)

        Raises:
            ImportError: If matplotlib is not available
            ValueError: If admin data is not loaded
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
            from matplotlib.colors import LinearSegmentedColormap
            import matplotlib.cm as cm
        except ImportError:
            logger.error("Matplotlib is required for visualization")
            return

        if admin_level not in ["admin1", "admin2"]:
            raise ValueError("admin_level must be either 'admin1' or 'admin2'")

        # Check if admin data is loaded
        if admin_level == "admin1" and self.admin1_gdf is None:
            raise ValueError("Admin1 data not loaded. Cannot visualize admin1.")
        if admin_level == "admin2" and self.admin2_gdf is None:
            raise ValueError("Admin2 data not loaded. Cannot visualize admin2.")

        # Get admin information for all GIDs
        if admin_level == "admin1":
            admin_results = self.batch_admin_mapping(gid_list, admin_level="admin1")
            admin_gdf = self.admin1_gdf
            admin_code_col = "gaul1_code"
            admin_name_col = "gaul1_name"
        else:
            admin_results = self.batch_admin_mapping(gid_list, admin_level="admin2")
            admin_gdf = self.admin2_gdf
            admin_code_col = "gaul2_code"
            admin_name_col = "gaul2_name"

        if admin_results.empty:
            logger.warning(f"No {admin_level} regions found for the provided GIDs")
            return

        # Get unique admin regions
        unique_admin_codes = admin_results[admin_code_col].unique()
        admin_regions = admin_gdf[admin_gdf[admin_code_col].isin(unique_admin_codes)]

        # Get grid cells
        grid_cells = self.priogrid_gdf[self.priogrid_gdf["gid"].isin(gid_list)]

        # Create plot
        fig, ax = plt.subplots(1, 1, figsize=figsize)

        # Plot all admin regions in the area
        if color_by_country:
            # Create a colormap for countries
            unique_countries = admin_results["iso3_code"].unique()
            country_colors = plt.cm.tab20(np.linspace(0, 1, len(unique_countries)))
            country_color_map = {
                country: color
                for country, color in zip(unique_countries, country_colors)
            }

            # Plot with color based on country
            for _, admin in admin_regions.iterrows():
                admin_code = admin[admin_code_col]
                admin_row = admin_results[admin_results[admin_code_col] == admin_code]
                if not admin_row.empty:
                    country = admin_row["iso3_code"].iloc[0]
                    color = country_color_map[country]
                    admin_gdf[admin_gdf[admin_code_col] == admin_code].plot(
                        ax=ax, color=[color], edgecolor="black", alpha=0.7, linewidth=1
                    )

            # Create legend for countries
            legend_elements = [
                mpatches.Patch(color=country_color_map[country], label=country)
                for country in unique_countries
            ]
        else:
            # Plot with uniform color
            admin_regions.plot(
                ax=ax, color="lightblue", edgecolor="black", alpha=0.7, linewidth=1
            )
            legend_elements = [
                mpatches.Patch(
                    color="lightblue", alpha=0.7, label=f"{admin_level.upper()} Regions"
                )
            ]

        # Plot grid cells if requested
        if show_grid_cells:
            grid_cells.plot(
                ax=ax, color="red", alpha=0.8, edgecolor="darkred", linewidth=1.5
            )

            # Add labels for grid cells
            for _, grid_cell in grid_cells.iterrows():
                centroid = grid_cell["centroid"]
                ax.text(
                    centroid.x,
                    centroid.y,
                    str(grid_cell["gid"]),
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="white",
                    fontweight="bold",
                    bbox=dict(boxstyle="circle,pad=0.2", facecolor="red", alpha=0.7),
                )

        # Add labels for admin regions
        for _, admin in admin_regions.iterrows():
            centroid = admin["geometry"].centroid
            admin_name = admin[admin_name_col]
            admin_code = admin[admin_code_col]

            # Truncate long names
            if len(admin_name) > 20:
                admin_name = admin_name[:17] + "..."

            ax.text(
                centroid.x,
                centroid.y,
                f"{admin_name}\n({admin_code})",
                ha="center",
                va="center",
                fontsize=9,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8),
            )

        # Set title
        ax.set_title(
            f"{admin_level.upper()} Regions for {len(gid_list)} PRIO-GRID Cells\n"
            f"Found {len(unique_admin_codes)} unique {admin_level.upper()} regions",
            fontsize=14,
            fontweight="bold",
        )

        # Add grid cells to legend if shown
        if show_grid_cells:
            legend_elements.insert(
                0, mpatches.Patch(color="red", alpha=0.8, label="PRIO-GRID Cells")
            )

        ax.legend(handles=legend_elements, loc="upper right", bbox_to_anchor=(1, 1))

        # Set aspect ratio and labels
        ax.set_aspect("equal")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.grid(True, alpha=0.3)

        # Add summary statistics as text
        stats_text = f"Total GIDs: {len(gid_list)}\n"
        stats_text += (
            f"Unique {admin_level.upper()} regions: {len(unique_admin_codes)}\n"
        )
        if color_by_country:
            stats_text += f"Unique countries: {len(unique_countries)}"

        ax.text(
            0.02,
            0.98,
            stats_text,
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment="top",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="white", alpha=0.8),
        )

        plt.tight_layout()
        plt.show()

    def find_country_by_iso_a3(self, iso_a3):
        """
        Find country information by ISO A3 code from the Natural Earth dataset.

        Parameters:
            iso_a3 (str): ISO A3 code of the country (e.g., 'USA', 'FRA', 'TZA')

        Returns:
            dict: Country information with all available fields from Natural Earth,
                or None if country is not found
        """
        # Validate input
        if not isinstance(iso_a3, str) or len(iso_a3) != 3:
            logger.warning(
                f"Invalid ISO A3 code format: {iso_a3}. Expected 3-character string."
            )
            return None

        # Convert to uppercase for consistency
        iso_a3 = iso_a3.upper()

        if self.use_disk_cache:
            # Use disk cache
            @self._disk_country_cache.cache()
            def _find_country_by_iso_a3_impl(iso_a3):
                # Find the country in the Natural Earth dataset
                country_rows = self.countries_gdf[
                    self.countries_gdf["ISO_A3"] == iso_a3
                ]

                if len(country_rows) == 0:
                    return None

                # Get the first (and should be only) matching country
                country = country_rows.iloc[0]

                # Prepare result with all available country data
                result = {
                    "iso_a3": country["ISO_A3"],
                    "country_name": country["NAME_EN"],
                }

                # Add all other available fields from Natural Earth
                for col in country.index:
                    if col not in ["geometry", "ISO_A3", "NAME_EN"]:
                        # Convert numpy types to native Python types
                        value = country[col]
                        if pd.isna(value):
                            result[col] = None
                        elif isinstance(value, (np.integer, np.int64, np.int32)):
                            result[col] = int(value)
                        elif isinstance(value, (np.floating, np.float64, np.float32)):
                            result[col] = float(value)
                        elif isinstance(value, np.bool_):
                            result[col] = bool(value)
                        else:
                            result[col] = str(value)

                # Add geometry as WKT string
                if hasattr(country["geometry"], "wkt"):
                    result["geometry_wkt"] = country["geometry"].wkt

                # Add some commonly useful derived fields
                result["data_source"] = "Natural Earth"
                result["centroid"] = {
                    "lon": float(country["geometry"].centroid.x),
                    "lat": float(country["geometry"].centroid.y),
                }

                # Calculate bounding box
                bounds = country["geometry"].bounds
                result["bounds"] = {
                    "min_lon": float(bounds[0]),
                    "min_lat": float(bounds[1]),
                    "max_lon": float(bounds[2]),
                    "max_lat": float(bounds[3]),
                }

                return result

            return _find_country_by_iso_a3_impl(iso_a3)
        else:
            # Use in-memory cache
            # Generate consistent cache key
            cache_key = self._get_country_cache_key(iso_a3)

            # Check cache first
            if cache_key in self._country_cache:
                cached_value = self._country_cache[cache_key]
                if cached_value is None:
                    return None
                result = cached_value.copy()
                return result

            # Find the country in the Natural Earth dataset
            country_rows = self.countries_gdf[self.countries_gdf["ISO_A3"] == iso_a3]

            if len(country_rows) == 0:
                logger.warning(
                    f"Country with ISO A3 code '{iso_a3}' not found in Natural Earth dataset"
                )
                # Update cache with None to avoid repeated lookups
                self._country_cache[cache_key] = None
                return None

            # Get the first (and should be only) matching country
            country = country_rows.iloc[0]

            # Prepare result with all available country data
            result = {
                "iso_a3": country["ISO_A3"],
                "country_name": country["NAME_EN"],
            }

            # Add all other available fields from Natural Earth
            for col in country.index:
                if col not in ["geometry", "ISO_A3", "NAME_EN"]:
                    # Convert numpy types to native Python types
                    value = country[col]
                    if pd.isna(value):
                        result[col] = None
                    elif isinstance(value, (np.integer, np.int64, np.int32)):
                        result[col] = int(value)
                    elif isinstance(value, (np.floating, np.float64, np.float32)):
                        result[col] = float(value)
                    elif isinstance(value, np.bool_):
                        result[col] = bool(value)
                    else:
                        result[col] = str(value)

            # Add geometry as WKT string
            if hasattr(country["geometry"], "wkt"):
                result["geometry_wkt"] = country["geometry"].wkt

            # Add some commonly useful derived fields
            result["data_source"] = "Natural Earth"
            result["centroid"] = {
                "lon": float(country["geometry"].centroid.x),
                "lat": float(country["geometry"].centroid.y),
            }

            # Calculate bounding box
            bounds = country["geometry"].bounds
            result["bounds"] = {
                "min_lon": float(bounds[0]),
                "min_lat": float(bounds[1]),
                "max_lon": float(bounds[2]),
                "max_lat": float(bounds[3]),
            }

            # Update cache
            self._country_cache[cache_key] = result
            return result

    def find_multiple_countries_by_iso_a3(self, iso_a3_list):
        """
        Find information for multiple countries by their ISO A3 codes.

        Parameters:
            iso_a3_list (list): List of ISO A3 codes (e.g., ['USA', 'FRA', 'TZA'])

        Returns:
            dict: Dictionary with ISO A3 codes as keys and country info as values.
                Countries not found will have None as values.
        """
        if not isinstance(iso_a3_list, (list, tuple, set)):
            raise ValueError(
                "iso_a3_list must be a list, tuple, or set of ISO A3 codes"
            )

        results = {}
        cache_hits = 0

        for iso_a3 in iso_a3_list:
            # Check cache first
            cache_key = self._get_country_cache_key(iso_a3.upper())
            if cache_key in self._country_cache:
                cached_value = self._country_cache[cache_key]
                results[iso_a3.upper()] = (
                    cached_value.copy() if cached_value is not None else None
                )
                cache_hits += 1
            else:
                # Not in cache, fetch the country info
                country_info = self.find_country_by_iso_a3(iso_a3)
                results[iso_a3.upper()] = country_info

        if cache_hits > 0:
            logger.info(
                f"Cache hits: {cache_hits}/{len(iso_a3_list)} ({cache_hits/len(iso_a3_list)*100:.1f}%)"
            )

        return results

    def get_country_summary(self, iso_a3):
        """
        Get a summary of country information including related grid cells and admin regions.

        Parameters:
            iso_a3 (str): ISO A3 code of the country

        Returns:
            dict: Summary including country info, grid cell count, and admin region counts
        """
        # Get basic country information
        country_info = self.find_country_by_iso_a3(iso_a3)
        if not country_info:
            return None

        # Get all grid cells for this country
        gids = self.find_gids_for_country(iso_a3)

        # Count admin1 regions if available
        admin1_count = 0
        if self.admin1_gdf is not None:
            admin1_count = len(self.admin1_gdf[self.admin1_gdf["iso3_code"] == iso_a3])

        # Count admin2 regions if available
        admin2_count = 0
        if self.admin2_gdf is not None:
            admin2_count = len(self.admin2_gdf[self.admin2_gdf["iso3_code"] == iso_a3])

        # Create summary
        summary = {
            "country_info": country_info,
            "priogrid": {
                "gid_count": len(gids),
                "gid_list": gids[:100],  # Return first 100 GIDs to avoid huge responses
                "has_more": len(gids) > 100,
            },
            "admin_regions": {
                "admin1_count": admin1_count,
                "admin2_count": admin2_count,
            },
            "data_source": "Natural Earth",
        }

        return summary

    def search_countries_by_name(
        self, name_pattern, exact_match=False, case_sensitive=False
    ):
        """
        Search for countries by name pattern.

        Parameters:
            name_pattern (str): Name or pattern to search for
            exact_match (bool): If True, only exact matches are returned
            case_sensitive (bool): If True, search is case sensitive

        Returns:
            list: List of matching countries with their information
        """
        if not isinstance(name_pattern, str):
            raise ValueError("name_pattern must be a string")

        # Prepare the search pattern
        if not case_sensitive:
            name_pattern = name_pattern.lower()
            search_column = self.countries_gdf["NAME_EN"].str.lower()
        else:
            search_column = self.countries_gdf["NAME_EN"]

        # Find matches
        if exact_match:
            matching_indices = search_column == name_pattern
        else:
            matching_indices = search_column.str.contains(name_pattern, na=False)

        matching_countries = self.countries_gdf[matching_indices]

        if len(matching_countries) == 0:
            logger.info(f"No countries found matching pattern: {name_pattern}")
            return []

        # Convert matches to list of dictionaries
        results = []
        for _, country in matching_countries.iterrows():
            country_info = {
                "iso_a3": country["ISO_A3"],
                "country_name": country["NAME_EN"],
            }

            # Add a few key fields
            key_fields = [
                "CONTINENT",
                "REGION_UN",
                "SUBREGION",
                "POP_EST",
                "GDP_MD",
                "INCOME_GRP",
            ]
            for field in key_fields:
                if field in country:
                    country_info[field.lower()] = country[field]

            results.append(country_info)

        logger.info(f"Found {len(results)} countries matching pattern: {name_pattern}")
        return results

    def enrich_dataframe_with_pg_info(
        self,
        df,
        pg_id_col="priogrid_id",
        time_id_col="month_id",
        include_country=True,
        include_admin1=True,
        include_admin2=True,
        include_pg_info=True,
        country_cols=None,
        admin1_cols=None,
        admin2_cols=None,
        pg_cols=None,
        batch_size=1000,
        use_multiprocessing=True,
        show_progress=True,
        only_metadata=True,
    ):
        """
        Enrich a DataFrame with country, admin1, admin2, and PRIO-GRID information based on PRIO-GRID IDs.

        Parameters:
            df (pd.DataFrame): Input DataFrame containing PRIO-GRID IDs
            pg_id_col (str): Name of the column containing PRIO-GRID IDs
            include_country (bool): Whether to include country information
            include_admin1 (bool): Whether to include admin1 information
            include_admin2 (bool): Whether to include admin2 information
            include_pg_info (bool): Whether to include PRIO-GRID information
            country_cols (list): Specific country columns to include (None for all)
            admin1_cols (list): Specific admin1 columns to include (None for all)
            admin2_cols (list): Specific admin2 columns to include (None for all)
            pg_cols (list): Specific PRIO-GRID columns to include (None for all)
            batch_size (int): Number of PRIO-GRID IDs to process in each batch
            use_multiprocessing (bool): Whether to use multiprocessing for faster processing
            show_progress (bool): Whether to show a progress bar

        Returns:
            pd.DataFrame: Enriched DataFrame with additional columns

        Raises:
            ValueError: If pg_id_col is not found in the DataFrame
        """
        # Validate input
        if pg_id_col not in df.columns:
            raise ValueError(f"Column '{pg_id_col}' not found in DataFrame")

        if only_metadata:
            df = pd.DataFrame(df[[pg_id_col, time_id_col]])
        # Create a copy to avoid modifying the original DataFrame
        result_df = df.copy()

        # Get unique PRIO-GRID IDs to process
        unique_pg_ids = df[pg_id_col].unique()
        total_ids = len(unique_pg_ids)
        total_batches = (total_ids - 1) // batch_size + 1

        logger.info(
            f"Starting enrichment of {total_ids} unique PRIO-GRID IDs in {total_batches} batches"
        )
        logger.info(
            f"Parameters: country={include_country}, admin1={include_admin1}, admin2={include_admin2}, pg_info={include_pg_info}"
        )

        # Ensure cache directories exist
        if self.use_disk_cache:
            for cache_type in ["country", "admin1", "admin2", "gid"]:
                cache_path = self.cache_dir / cache_type
                if not cache_path.exists():
                    os.makedirs(cache_path, exist_ok=True)
                    logger.info(f"Created cache directory: {cache_path}")

        # Process in batches
        all_pg_data = {}
        processed_count = 0

        # Initialize progress bar if requested
        pbar = None
        if show_progress:
            try:
                from tqdm import tqdm

                pbar = tqdm(
                    total=total_ids, desc="Processing PRIO-GRID IDs", unit="ids"
                )
            except ImportError:
                logger.warning(
                    "tqdm not installed. Progress bar will not be shown. Install with: pip install tqdm"
                )
                show_progress = False

        if use_multiprocessing and total_ids > batch_size:
            # Use threading instead of multiprocessing to avoid pickling issues
            from concurrent.futures import ThreadPoolExecutor, as_completed

            # Split into batches
            batches = [
                unique_pg_ids[i : i + batch_size]
                for i in range(0, total_ids, batch_size)
            ]

            # Process batches in parallel using threads
            with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
                # Submit all batches for processing
                future_to_batch = {
                    executor.submit(
                        self._process_pg_batch,
                        batch_ids,
                        include_country,
                        include_admin1,
                        include_admin2,
                        include_pg_info,
                        country_cols,
                        admin1_cols,
                        admin2_cols,
                        pg_cols,
                    ): batch_idx
                    for batch_idx, batch_ids in enumerate(batches)
                }

                # Collect results as they complete
                for future in as_completed(future_to_batch):
                    batch_idx = future_to_batch[future]
                    try:
                        batch_result = future.result()
                        all_pg_data.update(batch_result)
                        processed_count += len(batches[batch_idx])

                        # Update progress
                        if pbar:
                            pbar.update(len(batches[batch_idx]))

                        # Log progress every 10% or every 5 batches
                        if (
                            batch_idx % max(5, total_batches // 10) == 0
                            or batch_idx == total_batches - 1
                        ):
                            progress_pct = (processed_count / total_ids) * 100
                            logger.info(
                                f"Progress: {processed_count}/{total_ids} ({progress_pct:.1f}%) - Batch {batch_idx + 1}/{total_batches}"
                            )

                    except Exception as e:
                        logger.error(f"Error processing batch {batch_idx}: {str(e)}")
                        # Continue with other batches even if one fails
                        continue
        else:
            # Process sequentially for smaller datasets
            for i in range(0, total_ids, batch_size):
                batch_ids = unique_pg_ids[i : i + batch_size]
                batch_num = i // batch_size + 1

                logger.info(
                    f"Processing batch {batch_num}/{total_batches} ({len(batch_ids)} IDs)"
                )

                try:
                    batch_result = self._process_pg_batch(
                        batch_ids,
                        include_country,
                        include_admin1,
                        include_admin2,
                        include_pg_info,
                        country_cols,
                        admin1_cols,
                        admin2_cols,
                        pg_cols,
                    )
                    all_pg_data.update(batch_result)
                    processed_count += len(batch_ids)

                    # Update progress
                    if pbar:
                        pbar.update(len(batch_ids))

                    # Log progress
                    progress_pct = (processed_count / total_ids) * 100
                    logger.info(
                        f"Completed batch {batch_num}/{total_batches} - {progress_pct:.1f}% complete"
                    )

                except Exception as e:
                    logger.error(f"Error processing batch {batch_num}: {str(e)}")
                    continue

        # Close progress bar
        if pbar:
            pbar.close()

        # Convert the collected data to a DataFrame
        logger.info("Converting collected data to DataFrame")
        pg_info_df = pd.DataFrame.from_dict(all_pg_data, orient="index")

        # Merge with the original DataFrame
        if not pg_info_df.empty:
            logger.info("Merging enriched data with original DataFrame")
            result_df = result_df.merge(
                pg_info_df, left_on=pg_id_col, right_on="pg_id", how="left"
            )

            # Drop the redundant pg_id column
            if "pg_id" in result_df.columns:
                result_df.drop(columns=["pg_id"], inplace=True)
        else:
            logger.warning("No enrichment data was generated")

        logger.info(
            f"Enrichment complete. Added {len(result_df.columns) - len(df.columns)} new columns"
        )
        return result_df

    def _process_pg_batch(
        self,
        pg_ids,
        include_country,
        include_admin1,
        include_admin2,
        include_pg_info,
        country_cols,
        admin1_cols,
        admin2_cols,
        pg_cols,
    ):
        """Process a batch of PRIO-GRID IDs and return their information"""
        batch_data = {}

        for pg_id in pg_ids:
            pg_data = {"pg_id": pg_id}

            # Get PRIO-GRID information
            if include_pg_info:
                grid_cell = self.priogrid_gdf[self.priogrid_gdf["gid"] == pg_id]
                if len(grid_cell) > 0:
                    grid_info = grid_cell.iloc[0].to_dict()

                    # Select specific columns if requested
                    if pg_cols is not None:
                        for col in pg_cols:
                            if col in grid_info:
                                pg_data[f"pg_{col}"] = grid_info[col]
                    else:
                        # Include all grid info with pg_ prefix
                        for key, value in grid_info.items():
                            if key != "gid":  # Skip gid as it's already the key
                                pg_data[f"pg_{key}"] = value

            # Get country information
            if include_country:
                country_info = self.find_country_for_gid(pg_id)
                if country_info:
                    # Select specific columns if requested
                    if country_cols is not None:
                        for col in country_cols:
                            if col in country_info:
                                pg_data[f"country_{col}"] = country_info[col]
                    else:
                        # Include all country info with country_ prefix
                        for key, value in country_info.items():
                            if key != "gid":  # Skip gid as it's already the key
                                pg_data[f"country_{key}"] = value

            # Get admin1 information
            if include_admin1:
                admin1_info = self.find_admin1_for_gid(pg_id)
                if admin1_info:
                    # Select specific columns if requested
                    if admin1_cols is not None:
                        for col in admin1_cols:
                            if col in admin1_info:
                                pg_data[f"admin1_{col}"] = admin1_info[col]
                    else:
                        # Include all admin1 info with admin1_ prefix
                        for key, value in admin1_info.items():
                            if key != "gid":  # Skip gid as it's already the key
                                pg_data[f"admin1_{key}"] = value

            # Get admin2 information
            if include_admin2:
                admin2_info = self.find_admin2_for_gid(pg_id)
                if admin2_info:
                    # Select specific columns if requested
                    if admin2_cols is not None:
                        for col in admin2_cols:
                            if col in admin2_info:
                                pg_data[f"admin2_{col}"] = admin2_info[col]
                    else:
                        # Include all admin2 info with admin2_ prefix
                        for key, value in admin2_info.items():
                            if key != "gid":  # Skip gid as it's already the key
                                pg_data[f"admin2_{key}"] = value

            batch_data[pg_id] = pg_data

        return batch_data

    def enrich_dataframe_with_country_info(
        self,
        df,
        iso_a3_col="iso_a3",
        include_admin1=True,
        include_admin2=True,
        country_cols=None,
        admin1_cols=None,
        admin2_cols=None,
        batch_size=1000,
        use_multiprocessing=True,
        show_progress=True,
    ):
        """
        Enrich a DataFrame with country, admin1, and admin2 information based on ISO A3 codes.

        Parameters:
            df (pd.DataFrame): Input DataFrame containing ISO A3 codes
            iso_a3_col (str): Name of the column containing ISO A3 codes
            include_admin1 (bool): Whether to include admin1 information
            include_admin2 (bool): Whether to include admin2 information
            country_cols (list): Specific country columns to include (None for all)
            admin1_cols (list): Specific admin1 columns to include (None for all)
            admin2_cols (list): Specific admin2 columns to include (None for all)
            batch_size (int): Number of ISO A3 codes to process in each batch
            use_multiprocessing (bool): Whether to use multiprocessing for faster processing
            show_progress (bool): Whether to show a progress bar

        Returns:
            pd.DataFrame: Enriched DataFrame with additional columns

        Raises:
            ValueError: If iso_a3_col is not found in the DataFrame
        """
        # Validate input
        if iso_a3_col not in df.columns:
            raise ValueError(f"Column '{iso_a3_col}' not found in DataFrame")

        # Create a copy to avoid modifying the original DataFrame
        result_df = df.copy()

        # Get unique ISO A3 codes to process
        unique_iso_a3 = df[iso_a3_col].unique()
        total_codes = len(unique_iso_a3)
        total_batches = (total_codes - 1) // batch_size + 1

        logger.info(
            f"Starting enrichment of {total_codes} unique ISO A3 codes in {total_batches} batches"
        )
        logger.info(f"Parameters: admin1={include_admin1}, admin2={include_admin2}")

        # Prepare parameters for batch processing
        process_params = {
            "include_admin1": include_admin1,
            "include_admin2": include_admin2,
            "country_cols": country_cols,
            "admin1_cols": admin1_cols,
            "admin2_cols": admin2_cols,
        }

        # Process in batches
        all_country_data = {}
        processed_count = 0

        # Initialize progress bar if requested
        pbar = None
        if show_progress:
            try:
                from tqdm import tqdm

                pbar = tqdm(
                    total=total_codes, desc="Processing ISO A3 codes", unit="codes"
                )
            except ImportError:
                logger.warning(
                    "tqdm not installed. Progress bar will not be shown. Install with: pip install tqdm"
                )
                show_progress = False

        if use_multiprocessing and total_codes > batch_size:
            # Use threading instead of multiprocessing to avoid pickling issues
            from concurrent.futures import ThreadPoolExecutor, as_completed

            # Split into batches
            batches = [
                unique_iso_a3[i : i + batch_size]
                for i in range(0, total_codes, batch_size)
            ]

            # Process batches in parallel using threads
            with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
                # Submit all batches for processing
                future_to_batch = {
                    executor.submit(
                        self._process_country_batch, batch_codes, **process_params
                    ): batch_idx
                    for batch_idx, batch_codes in enumerate(batches)
                }

                # Collect results as they complete
                for future in as_completed(future_to_batch):
                    batch_idx = future_to_batch[future]
                    try:
                        batch_result = future.result()
                        all_country_data.update(batch_result)
                        processed_count += len(batches[batch_idx])

                        # Update progress
                        if pbar:
                            pbar.update(len(batches[batch_idx]))

                        # Log progress every 10% or every 5 batches
                        if (
                            batch_idx % max(5, total_batches // 10) == 0
                            or batch_idx == total_batches - 1
                        ):
                            progress_pct = (processed_count / total_codes) * 100
                            logger.info(
                                f"Progress: {processed_count}/{total_codes} ({progress_pct:.1f}%) - Batch {batch_idx + 1}/{total_batches}"
                            )

                    except Exception as e:
                        logger.error(f"Error processing batch {batch_idx}: {str(e)}")
                        # Continue with other batches even if one fails
                        continue
        else:
            # Process sequentially for smaller datasets
            for i in range(0, total_codes, batch_size):
                batch_codes = unique_iso_a3[i : i + batch_size]
                batch_num = i // batch_size + 1

                logger.info(
                    f"Processing batch {batch_num}/{total_batches} ({len(batch_codes)} codes)"
                )

                try:
                    batch_result = self._process_country_batch(
                        batch_codes, **process_params
                    )
                    all_country_data.update(batch_result)
                    processed_count += len(batch_codes)

                    # Update progress
                    if pbar:
                        pbar.update(len(batch_codes))

                    # Log progress
                    progress_pct = (processed_count / total_codes) * 100
                    logger.info(
                        f"Completed batch {batch_num}/{total_batches} - {progress_pct:.1f}% complete"
                    )

                except Exception as e:
                    logger.error(f"Error processing batch {batch_num}: {str(e)}")
                    continue

        # Close progress bar
        if pbar:
            pbar.close()

        # Convert the collected data to a DataFrame
        logger.info("Converting collected data to DataFrame")
        country_info_df = pd.DataFrame.from_dict(all_country_data, orient="index")

        # Merge with the original DataFrame
        if not country_info_df.empty:
            logger.info("Merging enriched data with original DataFrame")
            result_df = result_df.merge(
                country_info_df, left_on=iso_a3_col, right_on="iso_a3_code", how="left"
            )

            # Drop the redundant iso_a3_code column
            if "iso_a3_code" in result_df.columns:
                result_df.drop(columns=["iso_a3_code"], inplace=True)
        else:
            logger.warning("No enrichment data was generated")

        logger.info(
            f"Enrichment complete. Added {len(result_df.columns) - len(df.columns)} new columns"
        )
        return result_df

    def _process_country_batch(
        self,
        iso_a3_codes,
        include_admin1,
        include_admin2,
        country_cols,
        admin1_cols,
        admin2_cols,
    ):
        """Process a batch of ISO A3 codes and return their information"""
        batch_data = {}

        for iso_a3 in iso_a3_codes:
            # Skip empty or invalid codes
            if pd.isna(iso_a3) or not isinstance(iso_a3, str) or len(iso_a3) != 3:
                batch_data[iso_a3] = {"iso_a3_code": iso_a3}
                continue

            country_data = {"iso_a3_code": iso_a3}

            # Get country information
            country_info = self.find_country_by_iso_a3(iso_a3)
            if country_info:
                # Select specific columns if requested
                if country_cols is not None:
                    for col in country_cols:
                        if col in country_info:
                            country_data[f"country_{col}"] = country_info[col]
                else:
                    # Include all country info with country_ prefix
                    for key, value in country_info.items():
                        if key != "iso_a3":  # Skip iso_a3 as it's already the key
                            country_data[f"country_{key}"] = value

            # Get admin1 information
            if include_admin1 and self.admin1_gdf is not None:
                admin1_regions = self.admin1_gdf[self.admin1_gdf["iso3_code"] == iso_a3]

                if not admin1_regions.empty:
                    # Create a list of admin1 regions
                    admin1_list = []
                    for _, admin1 in admin1_regions.iterrows():
                        admin1_dict = {}

                        # Select specific columns if requested
                        if admin1_cols is not None:
                            for col in admin1_cols:
                                if col in admin1:
                                    admin1_dict[col] = admin1[col]
                        else:
                            # Include all admin1 info
                            for key, value in admin1.items():
                                if (
                                    key != "iso3_code"
                                ):  # Skip iso3_code as it's already known
                                    admin1_dict[key] = value

                        admin1_list.append(admin1_dict)

                    country_data["admin1_regions"] = admin1_list
                    country_data["admin1_count"] = len(admin1_list)

            # Get admin2 information
            if include_admin2 and self.admin2_gdf is not None:
                admin2_regions = self.admin2_gdf[self.admin2_gdf["iso3_code"] == iso_a3]

                if not admin2_regions.empty:
                    # Create a list of admin2 regions
                    admin2_list = []
                    for _, admin2 in admin2_regions.iterrows():
                        admin2_dict = {}

                        # Select specific columns if requested
                        if admin2_cols is not None:
                            for col in admin2_cols:
                                if col in admin2:
                                    admin2_dict[col] = admin2[col]
                        else:
                            # Include all admin2 info
                            for key, value in admin2.items():
                                if (
                                    key != "iso3_code"
                                ):  # Skip iso3_code as it's already known
                                    admin2_dict[key] = value

                        admin2_list.append(admin2_dict)

                    country_data["admin2_regions"] = admin2_list
                    country_data["admin2_count"] = len(admin2_list)

            batch_data[iso_a3] = country_data

        return batch_data

    def add_country_info_to_dataframe(
        self, df, iso_a3_col="iso_a3", name_col="country_name", additional_cols=None
    ):
        """
        Add basic country information to a DataFrame based on ISO A3 codes.

        Parameters:
            df (pd.DataFrame): Input DataFrame containing ISO A3 codes
            iso_a3_col (str): Name of the column containing ISO A3 codes
            name_col (str): Name of the column to create for country names
            additional_cols (list): Additional country columns to include

        Returns:
            pd.DataFrame: DataFrame with added country information
        """
        # Create a copy to avoid modifying the original DataFrame
        result_df = df.copy()

        # Get unique ISO A3 codes to process
        unique_iso_a3 = df[iso_a3_col].unique()
        logger.info(
            f"Processing {len(unique_iso_a3)} unique ISO A3 codes for country names"
        )

        # Create a mapping of ISO A3 to country name
        iso_to_name = {}
        iso_to_additional = {col: {} for col in additional_cols or []}

        for iso_a3 in unique_iso_a3:
            # Skip empty or invalid codes
            if pd.isna(iso_a3) or not isinstance(iso_a3, str) or len(iso_a3) != 3:
                iso_to_name[iso_a3] = None
                for col in iso_to_additional:
                    iso_to_additional[col][iso_a3] = None
                continue

            country_info = self.find_country_by_iso_a3(iso_a3)
            if country_info:
                iso_to_name[iso_a3] = country_info.get("country_name")

                # Add additional columns if requested
                for col in iso_to_additional:
                    iso_to_additional[col][iso_a3] = country_info.get(col)
            else:
                iso_to_name[iso_a3] = None
                for col in iso_to_additional:
                    iso_to_additional[col][iso_a3] = None

        # Add the country names to the DataFrame
        result_df[name_col] = result_df[iso_a3_col].map(iso_to_name)

        # Add additional columns if requested
        for col in iso_to_additional:
            result_df[f"country_{col}"] = result_df[iso_a3_col].map(
                iso_to_additional[col]
            )

        logger.info(f"Added country information to DataFrame")
        return result_df


# Global default mapper
_DEFAULT_MAPPER = None


def set_default_mapper():
    """
    Set the default PriogridCountryMapper instance to be used by SpatialEntity classes.

    This function creates a global default mapper that will be automatically used
    by Point, Priogrid, and Country classes when no explicit mapper is provided.

    Returns:
        PriogridCountryMapper: The created default mapper instance
    """
    global _DEFAULT_MAPPER
    _DEFAULT_MAPPER = PriogridCountryMapper()
    return _DEFAULT_MAPPER


def get_default_mapper():
    """
    Get the default PriogridCountryMapper instance.

    Returns:
        PriogridCountryMapper: The default mapper instance

    Raises:
        ValueError: If no default mapper has been set
    """
    if _DEFAULT_MAPPER is None:
        raise ValueError("No default mapper set. Call set_default_mapper() first.")
    return _DEFAULT_MAPPER


# Set default mapper
set_default_mapper()
