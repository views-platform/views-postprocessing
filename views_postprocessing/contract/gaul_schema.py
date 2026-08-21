"""Single source of truth for the GAUL enrichment schema and PRIO-GRID geometry.

Shared by the delivery's artifact builders and the build/diff tooling
(scripts/) so the 9-column contract, the datafactory->contract rename map, and
the PRIO-GRID coordinate formula are defined exactly once.

The 9 contract columns are the wire's declared geography vocabulary: written into
the §5 sidecar and the historical artifact here, and hard-validated by the consumer
(views-faoapi `handlers.py`, `FAO_PGMDataset._METADATA_COLS`).

**The column contract is declared as DATA (register C-70, #153).** One list used to
carry three independent meanings at once — which columns exist, **what order they
appear in on the wire** (ADR-013 §5.1 declares column order normative and the §10
golden fixture pins it), and which the null-gate covers — while its comment named
only the first. The dtype policy was then re-derived positionally by `if col in
CODE_COLS` in three separate modules, so "a code column is float64 on the wire" was
scattered rather than stated.

`COLUMNS` below states each column's role and wire dtype once; everything else is
derived from it. Reordering `COLUMNS` **is a wire change** and will fail the §10
byte-parity fixture — which is the intended consequence, not an accident.

**Before proposing integer code columns, read ADR-013 §5.1a.** The partner has asked
twice (#278, #272), and will ask again; the reason recorded here until 2026-08-17 was
not a good one. "Codes are always float64" is *not* because an integer column cannot
hold a missing value — parquet and arrow carry nullable integers natively, and the
lookup this module describes stores all three code columns as `int64` with zero
nulls. The float is introduced by the builders below, not by the data.

The rule survives on a different, measured ground: an int64 parquet column reads back
as `int64` under a default pandas read when it holds no null, and as `float64` when it
holds one, so nullable int64 would move the dtype instability from our writer to the
consumer's reader and make it depend on what a given run contained. §5.1a carries the
measurement, the consumer-side evidence, and the one useful consequence — that because
the delivered region excludes the GAUL-uncovered cells, no delivered code is ever
missing (`tests/test_gaul_lookup_fidelity.py::test_lookup_has_no_nulls`), so a
consumer's `astype("int64")` on read is lossless for this product.
"""

from __future__ import annotations

# ── The 9-column contract, declared once (name, role, wire dtype) ──────────
#
# ORDER IS NORMATIVE (ADR-013 §5.1) — this sequence is the sidecar's and the
# historical artifact's column order, byte-pinned by the §10 golden fixture.
#
# Roles: "coord" cell-centre degrees · "code" GAUL numeric id · "name" GAUL label.
# Wire dtypes are the §5.1 ruling: codes are ALWAYS float64 (one stable schema
# regardless of whether a run contains a missing code), names are plain strings
# (never dictionary-encoded), coords float64.
COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("pg_xcoord",         "coord", "float64"),
    ("pg_ycoord",         "coord", "float64"),
    ("country_iso_a3",    "name",  "string"),
    ("admin1_gaul1_code", "code",  "float64"),
    ("admin1_gaul1_name", "name",  "string"),
    ("admin1_gaul0_code", "code",  "float64"),
    ("admin1_gaul0_name", "name",  "string"),
    ("admin2_gaul2_code", "code",  "float64"),
    ("admin2_gaul2_name", "name",  "string"),
)

#: All nine, in normative wire order. Derived — do not hand-edit.
METADATA_COLS = [name for name, _, _ in COLUMNS]

#: By role. Derived — do not hand-edit.
CODE_COLS = [name for name, role, _ in COLUMNS if role == "code"]
NAME_COLS = [name for name, role, _ in COLUMNS if role == "name"]
COORD_COLS = [name for name, role, _ in COLUMNS if role == "coord"]

#: column -> declared wire dtype, for the builders that cast.
WIRE_DTYPE: dict[str, str] = {name: dtype for name, _, dtype in COLUMNS}

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
