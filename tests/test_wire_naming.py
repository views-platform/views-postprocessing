"""Hop-B name templates (wire/naming.py) — golden-string tests against the §10
fixture's actual file names (the templates' executable pin)."""

from pathlib import Path

from views_postprocessing.contract.wire import naming

_FIX = Path(__file__).resolve().parent / "fixtures" / "wire_contract"


def test_shard_name_reproduces_the_fixture():
    name = naming.shard_name("fixture_run_0", "lr_ged_sb", 543)
    assert name == "fixture_run_0__lr_ged_sb__m000543.arrow.parquet"
    assert (_FIX / name).exists()


def test_run_manifest_name_reproduces_the_fixture():
    name = naming.run_manifest_name("fixture_run_0")
    assert name == "fixture_run_0__manifest.json"
    assert (_FIX / name).exists()


def test_sidecar_name_reproduces_the_fixture():
    name = naming.sidecar_name("fixture_run_0")
    assert name == "fixture_run_0__sidecar.parquet"
    assert (_FIX / name).exists()


def test_month_padding_is_six_digits():
    assert naming.shard_name("r", "t", 7).endswith("__m000007.arrow.parquet")


# ── the column contract is declared as data (C-70, #153) ──────────────────────
def test_column_contract_is_derived_from_one_declaration():
    """C-70: one list used to carry three meanings — membership, wire ORDER, and
    null-gate scope — while its comment named only the first, and the dtype policy
    was re-derived positionally in three modules.

    `COLUMNS` states each column's role and wire dtype once; these assertions pin
    that everything else is derived from it rather than maintained alongside it.
    """
    from views_postprocessing.contract import gaul_schema as g

    assert [name for name, _, _ in g.COLUMNS] == g.METADATA_COLS
    assert len(g.COLUMNS) == 9
    # roles partition the columns exactly — no column is unclassified or double-counted
    assert set(g.CODE_COLS) | set(g.NAME_COLS) | set(g.COORD_COLS) == set(g.METADATA_COLS)
    assert len(g.CODE_COLS) + len(g.NAME_COLS) + len(g.COORD_COLS) == 9
    # the §5.1 dtype ruling, stated once
    assert all(g.WIRE_DTYPE[c] == "float64" for c in g.CODE_COLS)
    assert all(g.WIRE_DTYPE[c] == "float64" for c in g.COORD_COLS)
    assert all(g.WIRE_DTYPE[c] == "string" for c in g.NAME_COLS)


def test_wire_column_order_is_normative_and_unchanged():
    """ADR-013 §5.1 declares column order normative; §10 byte-pins it.

    Written out literally so a reorder of `COLUMNS` fails HERE with a readable diff,
    rather than only as a byte mismatch in the fixture.
    """
    from views_postprocessing.contract.gaul_schema import METADATA_COLS

    assert METADATA_COLS == [
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
