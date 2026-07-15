"""Conformance tests over the ADR-013 §10 golden fixture — the executable spec.

These are the canonical-source-side checks: integrity (hashes), the Track-A shard's
round-trip, the arrow shard's header + ordering oracle, the sidecar's pinned schema
(incl. the NaN-preserved rule), both manifests' consistency, and Erratum E1. The other
repos vendor these bytes and run their own side (§10.1).
"""

import hashlib
import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
from views_frames.io import arrow as vf_arrow

from views_postprocessing.delivery.draws import assert_draws_uncollapsed

FIX = Path(__file__).resolve().parent / "fixtures" / "wire_contract"
SHARD_A = FIX / "fixture_run_0__lr_ged_sb__m000543.tap.zip"
MANIFEST_A = FIX / "fixture_run_0__lr_ged_sb__manifest.json"
SHARD_B = FIX / "fixture_run_0__lr_ged_sb__m000543.arrow.parquet"
SIDECAR = FIX / "fixture_run_0__sidecar.parquet"
MANIFEST_B = FIX / "fixture_run_0__manifest.json"

_SIDECAR_COLS = [
    "pg_xcoord", "pg_ycoord", "country_iso_a3",
    "admin1_gaul1_code", "admin1_gaul1_name",
    "admin1_gaul0_code", "admin1_gaul0_name",
    "admin2_gaul2_code", "admin2_gaul2_name",
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- §10.1 integrity ---------------------------------------------------------------


def test_sha256sums_matches_every_file():
    for line in (FIX / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split()
        assert _sha256(FIX / name) == digest, f"fixture drift: {name}"


# --- §3.1 Track-A shard ------------------------------------------------------------


def test_track_a_shard_round_trips():
    with zipfile.ZipFile(SHARD_A) as zf:
        assert sorted(zf.namelist()) == ["identifiers.npz", "metadata.json", "y_pred.npy"]
        values = np.load(io.BytesIO(zf.read("y_pred.npy")))
        header = json.loads(zf.read("metadata.json"))
        with zipfile.ZipFile(io.BytesIO(zf.read("identifiers.npz"))) as ids:
            time = np.load(io.BytesIO(ids.read("time.npy")))
            unit = np.load(io.BytesIO(ids.read("unit.npy")))
    assert values.shape == (6, 4) and values.dtype == np.float32
    assert time.shape == unit.shape == (6,)
    assert header["contract_version"] == "1.5"
    assert header["target"] == "lr_ged_sb"  # §7a vocabulary
    assert header["id_semantics"] == {"time": "views_month_id", "unit": "priogrid_id"}
    # the payload satisfies the §6 policy gate against its own declared header
    assert_draws_uncollapsed(values, header["sample_count"], s_min=2) is None


# --- §4.1 / §4.5 arrow shard -------------------------------------------------------


def test_arrow_shard_header_and_values_match_track_a():
    state = vf_arrow.load(SHARD_B)
    with zipfile.ZipFile(SHARD_A) as zf:
        a_values = np.load(io.BytesIO(zf.read("y_pred.npy")))
        a_header = json.loads(zf.read("metadata.json"))
    np.testing.assert_array_equal(np.asarray(state["values"], dtype=np.float32), a_values)
    assert state["metadata"] == a_header  # ONE header, both envelopes — byte-level parity


def test_arrow_shard_sample_column_is_the_ordering_oracle():
    # §4.5(b): consumers must verify this before positional reshape.
    table = pq.read_table(SHARD_B)
    sample = table.column("sample").to_numpy()
    np.testing.assert_array_equal(sample, np.tile(np.arange(4, dtype=np.int32), 6))


# --- §5.1 sidecar -------------------------------------------------------------------


def test_sidecar_schema_pinned_and_nan_row_preserved():
    table = pq.read_table(SIDECAR)
    assert table.column_names == ["priogrid_id"] + _SIDECAR_COLS
    last = {c: table.column(c)[-1].as_py() for c in _SIDECAR_COLS}
    assert last["country_iso_a3"] is None  # the NaN-GAUL row EXISTS — never pre-dropped
    assert last["admin1_gaul0_code"] != last["admin1_gaul0_code"]  # NaN
    assert table.num_rows == 6  # gid-set matches the forecast gid-set (§5.2)


# --- §3.2 / §4.2 manifests ----------------------------------------------------------


def test_hop_a_manifest_consistent_and_erratum_e1():
    m = json.loads(MANIFEST_A.read_text())
    assert m["sidecar_sha256"] is None  # Erratum E1: no sidecar hash at Hop A
    assert m["shards"][0]["sha256"] == _sha256(SHARD_A)
    assert m["expected_months"] == [543] and m["expected_cell_count"] == 6


def test_hop_b_run_manifest_is_the_commit_marker():
    m = json.loads(MANIFEST_B.read_text())
    assert m["targets"] == ["lr_ged_sb"]  # one manifest per run, spanning targets (§4.2)
    assert m["shards"][0]["sha256"] == _sha256(SHARD_B)
    assert m["sidecar"]["sha256"] == _sha256(SIDECAR)  # the E1 home of the sidecar hash
    assert m["expected_months"] == [543] and m["expected_cell_count"] == 6
