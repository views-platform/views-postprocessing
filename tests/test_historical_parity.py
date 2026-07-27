"""Reader-level parity oracle for the historical artifact (#126, Feathers
amendment): the characterization golden captures what the LEGACY pandas chain
produced from a real 2-month × 200-cell slice, and every future builder must
yield the same frame AS SEEN THROUGH FAOAPI'S READER — not the same bytes.

Reader semantics mirrored from views-faoapi (`dataset_service.py:255-334`,
`handlers.py:1365-1417`): read parquet; if no MultiIndex, set
``["month_id", "priogrid_id"|"priogrid_gid"]``; require the 9 metadata columns
present and non-null; historical targets = every remaining column.

Captured truth worth naming: the legacy chain would have shipped two junk
columns (``row``, ``col`` — datafactory grid coordinates) which faoapi's
auto-detect would have served as bogus "targets". The frame-native builder
drops them deliberately; the parity comparison is therefore over the REAL
targets + metadata, and a dedicated test pins the junk exclusion.
"""

from pathlib import Path

import pyarrow.parquet as pq

from views_postprocessing.unfao.gaul_schema import METADATA_COLS

GOLDEN = Path(__file__).resolve().parent / "fixtures" / "historical_golden" / "legacy_historical_slice.parquet"
REAL_TARGETS = ["lr_ged_sb", "lr_ged_ns", "lr_ged_os"]
_INDEX_CANDIDATES = ("priogrid_id", "priogrid_gid")


def reader_view(path) -> dict:
    """faoapi's reader semantics, pandas-free: returns {(month, gid): {col: value}}
    for target+metadata columns, plus the detected target list."""
    table = pq.read_table(path)
    names = set(table.column_names)
    id_col = next((c for c in _INDEX_CANDIDATES if c in names), None)
    assert "month_id" in names and id_col, f"index columns missing: {sorted(names)}"
    missing = [c for c in METADATA_COLS if c not in names]
    assert not missing, f"metadata columns missing: {missing}"
    targets = [c for c in table.column_names if c not in {"month_id", *_INDEX_CANDIDATES, *METADATA_COLS}]
    rows = table.to_pylist()
    view = {
        (r["month_id"], r[id_col]): {c: r[c] for c in (*targets, *METADATA_COLS)}
        for r in rows
    }
    return {"targets": targets, "rows": view}


def test_golden_passes_reader_semantics():
    view = reader_view(GOLDEN)
    assert len(view["rows"]) == 400  # 2 months × 200 cells
    # the legacy chain's auto-detected targets include the junk row/col columns —
    # the captured hazard the frame-native builder must NOT reproduce
    assert set(view["targets"]) == {*REAL_TARGETS, "row", "col"}


def test_golden_metadata_is_complete_and_nonnull():
    view = reader_view(GOLDEN)
    for key, cols in view["rows"].items():
        for meta in METADATA_COLS:
            assert cols[meta] is not None and cols[meta] == cols[meta], (key, meta)


def test_golden_carries_real_values():
    view = reader_view(GOLDEN)
    # spot sanity: coordinates are real half-degree grid values
    some = next(iter(view["rows"].values()))
    assert isinstance(some["pg_xcoord"], float) and abs(some["pg_xcoord"]) <= 180.0
