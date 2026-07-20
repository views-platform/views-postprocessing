"""§5 sidecar builder (wire/sidecar.py) — byte parity with the fixture sidecar via
an injected synthetic lookup, plus pinned-schema property tests against the real
ADR-011 lookup. Toolchain pin as in test_wire_shard (fail loud, never skip)."""

import hashlib
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from views_postprocessing.unfao.gaul_schema import CODE_COLS, METADATA_COLS
from views_postprocessing.unfao.wire import sidecar

_FIX = Path(__file__).resolve().parent / "fixtures" / "wire_contract"
_GIDS = [100001, 100002, 100003, 100004, 100005, 100006]


def _synthetic_lookup() -> pa.Table:
    """The fixture sidecar's content, shaped like the REAL lookup (priogrid_gid key,
    int64 codes with nulls, dictionary-encoded strings) — proving the builder's
    casts, not echoing its output."""
    return pa.table(
        {
            "priogrid_gid": pa.array(_GIDS, pa.int64()),
            "pg_xcoord": pa.array([10.25, 10.75, 11.25, 11.75, 12.25, 12.75], pa.float64()),
            "pg_ycoord": pa.array([5.25, 5.25, 5.25, 5.75, 5.75, 5.75], pa.float64()),
            "country_iso_a3": pa.array(["AAA", "AAA", "AAA", "BBB", "BBB", None]).dictionary_encode(),
            "admin1_gaul1_code": pa.array([11, 11, 12, 21, 21, None], pa.int64()),
            "admin1_gaul1_name": pa.array(["A-one", "A-one", "A-two", "B-one", "B-one", None]).dictionary_encode(),
            "admin1_gaul0_code": pa.array([1, 1, 1, 2, 2, None], pa.int64()),
            "admin1_gaul0_name": pa.array(["Aland", "Aland", "Aland", "Bland", "Bland", None]).dictionary_encode(),
            "admin2_gaul2_code": pa.array([111, 112, 121, 211, 212, None], pa.int64()),
            "admin2_gaul2_name": pa.array(["A-1-1", "A-1-2", "A-2-1", "B-1-1", "B-1-2", None]).dictionary_encode(),
        }
    )


def test_byte_parity_with_the_fixture_sidecar(tmp_path):
    name, sha = sidecar.write_sidecar(
        _synthetic_lookup(), _GIDS, run_id="fixture_run_0", directory=tmp_path
    )
    canonical = (_FIX / "fixture_run_0__sidecar.parquet").read_bytes()
    assert name == "fixture_run_0__sidecar.parquet"
    assert (tmp_path / name).read_bytes() == canonical
    assert sha == hashlib.sha256(canonical).hexdigest()


def test_missing_forecast_gid_fails_loud():
    with pytest.raises(sidecar.SidecarError, match="absent from the GAUL lookup"):
        sidecar.build_sidecar(_synthetic_lookup(), [*_GIDS, 999999])


def test_rows_restricted_to_declared_gids_and_ascending():
    table = sidecar.build_sidecar(_synthetic_lookup(), [100003, 100001])
    got = table.column("priogrid_id").to_pylist()
    assert got == [100001, 100003]  # subset only, ascending


def test_real_lookup_produces_the_pinned_schema():
    lookup = pq.read_table(
        Path(__file__).resolve().parents[1] / "views_postprocessing" / "data" / "gaul_lookup.parquet"
    )
    some_gids = lookup.column("priogrid_gid").to_pylist()[:50]
    table = sidecar.build_sidecar(lookup, some_gids)
    assert table.column_names == ["priogrid_id"] + METADATA_COLS
    for col in CODE_COLS:
        assert table.schema.field(col).type == pa.float64()  # ALWAYS float64 (§5.1)
    for col in ("country_iso_a3", "admin1_gaul1_name"):
        assert table.schema.field(col).type == pa.string()  # plain, not dictionary
    assert table.num_rows == 50
