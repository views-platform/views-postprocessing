"""Single source of truth for the GAUL enrichment schema and PRIO-GRID geometry.

Shared by the production enricher (enrichment.py) and the build/diff tooling
(scripts/) so the 9-column contract, the datafactory->contract rename map, and
the PRIO-GRID coordinate formula are defined exactly once.

The 9 contract columns are hard-validated at unfao.py (_append_metadata /
_validate) and at views-faoapi handlers.py (FAO_PGMDataset._METADATA_COLS).
"""

from __future__ import annotations

# ── The 9-column contract (manager selection order) ────────────────────────
METADATA_COLS = [
    "pg_xcoord", "pg_ycoord", "country_iso_a3",
    "admin1_gaul1_code", "admin1_gaul1_name",
    "admin1_gaul0_code", "admin1_gaul0_name",
    "admin2_gaul2_code", "admin2_gaul2_name",
]

CODE_COLS = ["admin1_gaul1_code", "admin1_gaul0_code", "admin2_gaul2_code"]
NAME_COLS = ["country_iso_a3", "admin1_gaul1_name", "admin1_gaul0_name",
             "admin2_gaul2_name"]
COORD_COLS = ["pg_xcoord", "pg_ycoord"]

# ── datafactory (gid, value) parquet  ->  contract column ──────────────────
# gaul0/gaul1 land under the admin1_ prefix, gaul2 under admin2_, iso3 becomes
# country_iso_a3 (mirrors the mapper's _process_pg_batch prefixing).
SOURCE_RENAME = {
    "gaul0_code": "admin1_gaul0_code",
    "gaul0_name": "admin1_gaul0_name",
    "gaul1_code": "admin1_gaul1_code",
    "gaul1_name": "admin1_gaul1_name",
    "gaul2_code": "admin2_gaul2_code",
    "gaul2_name": "admin2_gaul2_name",
    "iso3_code": "country_iso_a3",
}

# ── PRIO-GRID geometry (fixed 0.5-degree global grid, 720 cols x 360 rows) ──
PRIOGRID_NCOL = 720
CELL_SIZE = 0.5
HALF_CELL = 0.25


def xcoord(gid: int) -> float:
    """Cell-centre longitude for a PRIO-GRID gid."""
    return -180.0 + ((gid - 1) % PRIOGRID_NCOL) * CELL_SIZE + HALF_CELL


def ycoord(gid: int) -> float:
    """Cell-centre latitude for a PRIO-GRID gid."""
    return -90.0 + ((gid - 1) // PRIOGRID_NCOL) * CELL_SIZE + HALF_CELL


def colrow(gid: int) -> tuple[int, int]:
    """Zero-based (col, row) of a PRIO-GRID gid."""
    return (gid - 1) % PRIOGRID_NCOL, (gid - 1) // PRIOGRID_NCOL
