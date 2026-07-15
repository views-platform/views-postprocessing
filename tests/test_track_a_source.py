"""The Hop-A source adapter against the §10 golden fixture — happy path from the
canonical bytes, tamper paths from surgically corrupted copies of them.

Every tamper case starts from the REAL fixture and breaks exactly one declared fact
(hash, member set, sample_count, dtype, major version, target, month set, cell count,
identifier length) — proving the adapter rejects precisely what the contract says it
must, not merely malformed junk.
"""

import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pytest

from views_postprocessing.unfao import track_a_source as tas

FIX = Path(__file__).resolve().parent / "fixtures" / "wire_contract"
SHARD = (FIX / "fixture_run_0__lr_ged_sb__m000543.tap.zip").read_bytes()
MANIFEST = json.loads((FIX / "fixture_run_0__lr_ged_sb__manifest.json").read_text())
SHARD_NAME = MANIFEST["shards"][0]["name"]
SHARD_SHA = MANIFEST["shards"][0]["sha256"]


def _retouched_shard(**member_overrides: bytes) -> bytes:
    """The fixture shard with named members replaced — everything else byte-identical."""
    with zipfile.ZipFile(io.BytesIO(SHARD)) as zf:
        members = {name: zf.read(name) for name in zf.namelist()}
    members.update(member_overrides)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return buf.getvalue()


def _header(**overrides) -> bytes:
    with zipfile.ZipFile(io.BytesIO(SHARD)) as zf:
        header = json.loads(zf.read("metadata.json"))
    header.update(overrides)
    return json.dumps(header).encode()


def _sha(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


# --- happy path: the golden fixture is the oracle -----------------------------------


def test_read_manifest_accepts_the_fixture_manifest():
    manifest = tas.read_manifest((FIX / "fixture_run_0__lr_ged_sb__manifest.json").read_bytes())
    assert manifest["run_id"] == "fixture_run_0"
    assert manifest["sidecar_sha256"] is None  # Erratum E1


def test_read_shard_round_trips_the_fixture():
    frame, header = tas.read_shard(SHARD, expected_sha256=SHARD_SHA)
    assert frame.n_rows == 6 and frame.sample_count == 4
    assert frame.values.dtype == np.float32
    np.testing.assert_array_equal(np.asarray(frame.index.unit), np.arange(100001, 100007))
    np.testing.assert_array_equal(np.asarray(frame.index.time), np.full(6, 543))
    assert header["contract_version"] == "1.5" and header["target"] == "lr_ged_sb"


def test_frames_for_target_assembles_the_run():
    frame = tas.frames_for_target(MANIFEST, {SHARD_NAME: SHARD})
    assert frame.n_rows == 6 and frame.sample_count == 4


# --- §3.2 hash verification -----------------------------------------------------------


def test_tampered_bytes_rejected():
    with pytest.raises(tas.TrackASourceError, match="sha256 mismatch"):
        tas.read_shard(SHARD + b"\x00", expected_sha256=SHARD_SHA)


# --- §3.1 member set -------------------------------------------------------------------


def test_missing_member_rejected():
    with zipfile.ZipFile(io.BytesIO(SHARD)) as zf:
        members = {n: zf.read(n) for n in zf.namelist() if n != "identifiers.npz"}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    bad = buf.getvalue()
    with pytest.raises(tas.TrackASourceError, match="archive members"):
        tas.read_shard(bad, expected_sha256=_sha(bad))


# --- header-vs-payload (per-hop ingest asserts) ----------------------------------------


def test_header_lying_about_sample_count_rejected():
    bad = _retouched_shard(**{"metadata.json": _header(sample_count=1024)})
    with pytest.raises(tas.TrackASourceError, match="sample_count=1024"):
        tas.read_shard(bad, expected_sha256=_sha(bad))


def test_header_lying_about_dtype_rejected():
    bad = _retouched_shard(**{"metadata.json": _header(dtype="float64")})
    with pytest.raises(tas.TrackASourceError, match="dtype"):
        tas.read_shard(bad, expected_sha256=_sha(bad))


def test_identifier_length_mismatch_rejected():
    with zipfile.ZipFile(io.BytesIO(SHARD)) as zf:
        with zipfile.ZipFile(io.BytesIO(zf.read("identifiers.npz"))) as ids:
            time = np.load(io.BytesIO(ids.read("time.npy")))
            unit = np.load(io.BytesIO(ids.read("unit.npy")))
    short_ids = io.BytesIO()
    with zipfile.ZipFile(short_ids, "w", zipfile.ZIP_STORED) as zf:
        for name, arr in (("time.npy", time[:-1]), ("unit.npy", unit)):
            buf = io.BytesIO()
            np.save(buf, arr)
            zf.writestr(name, buf.getvalue())
    bad = _retouched_shard(**{"identifiers.npz": short_ids.getvalue()})
    with pytest.raises(tas.TrackASourceError, match="identifier lengths"):
        tas.read_shard(bad, expected_sha256=_sha(bad))


# --- §2.1 versioning -------------------------------------------------------------------


def test_major_version_bump_rejected_in_shard_header():
    bad = _retouched_shard(**{"metadata.json": _header(contract_version="2.0")})
    with pytest.raises(tas.TrackASourceError, match="major"):
        tas.read_shard(bad, expected_sha256=_sha(bad))


def test_major_version_bump_rejected_in_manifest():
    with pytest.raises(tas.TrackASourceError, match="major"):
        tas.read_manifest(json.dumps({**MANIFEST, "contract_version": "2.0"}).encode())


def test_minor_version_drift_accepted():
    bumped = _retouched_shard(**{"metadata.json": _header(contract_version="1.9")})
    frame, header = tas.read_shard(bumped, expected_sha256=_sha(bumped))
    assert header["contract_version"] == "1.9" and frame.n_rows == 6


# --- run assembly (§3.2 completeness; §3.3 manifest-is-identity) ----------------------


def test_missing_shard_bytes_rejected():
    with pytest.raises(tas.TrackASourceError, match="not provided"):
        tas.frames_for_target(MANIFEST, {})


def test_shard_target_disagreeing_with_manifest_rejected():
    bad = _retouched_shard(**{"metadata.json": _header(target="lr_ged_ns")})
    manifest = {**MANIFEST, "shards": [{"name": SHARD_NAME, "sha256": _sha(bad)}]}
    with pytest.raises(tas.TrackASourceError, match="target"):
        tas.frames_for_target(manifest, {SHARD_NAME: bad})


def test_wrong_month_coverage_rejected():
    manifest = {**MANIFEST, "expected_months": [543, 544]}
    with pytest.raises(tas.TrackASourceError, match="not provided"):
        # month 544's shard is absent entirely — caught at the bytes gate
        tas.frames_for_target(
            {**manifest, "shards": MANIFEST["shards"] + [{"name": "m544", "sha256": "0" * 64}]},
            {SHARD_NAME: SHARD},
        )
    bad = _retouched_shard(**{"metadata.json": _header(time_id=999)})
    manifest = {**MANIFEST, "shards": [{"name": SHARD_NAME, "sha256": _sha(bad)}]}
    with pytest.raises(tas.TrackASourceError, match="months covered"):
        tas.frames_for_target(manifest, {SHARD_NAME: bad})


def test_wrong_cell_count_rejected():
    manifest = {**MANIFEST, "expected_cell_count": 7}
    with pytest.raises(tas.TrackASourceError, match="cells"):
        tas.frames_for_target(manifest, {SHARD_NAME: SHARD})


def test_manifest_missing_required_field_rejected():
    truncated = {k: v for k, v in MANIFEST.items() if k != "expected_months"}
    with pytest.raises(tas.TrackASourceError, match="expected_months"):
        tas.read_manifest(json.dumps(truncated).encode())
