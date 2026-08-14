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

from views_postprocessing.contract import track_a_source as tas

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
    frame, headers = tas.frames_for_target(MANIFEST, {SHARD_NAME: SHARD}.__getitem__)
    assert frame.n_rows == 6 and frame.sample_count == 4
    # headers ride along in manifest shard order (provenance pass-through, §10.2)
    assert [h["time_id"] for h in headers] == [543]
    assert headers[0]["provenance"]["ensemble"] == "fixture_ensemble"


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
        tas.frames_for_target(MANIFEST, {}.__getitem__)


def test_shard_target_disagreeing_with_manifest_rejected():
    bad = _retouched_shard(**{"metadata.json": _header(target="lr_ged_ns")})
    manifest = {**MANIFEST, "shards": [{"name": SHARD_NAME, "sha256": _sha(bad)}]}
    with pytest.raises(tas.TrackASourceError, match="target"):
        tas.frames_for_target(manifest, {SHARD_NAME: bad}.__getitem__)


def test_wrong_month_coverage_rejected():
    manifest = {**MANIFEST, "expected_months": [543, 544]}
    with pytest.raises(tas.TrackASourceError, match="not provided"):
        # month 544's shard is absent entirely — caught at the bytes gate
        tas.frames_for_target(
            {**manifest, "shards": MANIFEST["shards"] + [{"name": "m544", "sha256": "0" * 64}]},
            {SHARD_NAME: SHARD}.__getitem__,
        )
    bad = _retouched_shard(**{"metadata.json": _header(time_id=999)})
    manifest = {**MANIFEST, "shards": [{"name": SHARD_NAME, "sha256": _sha(bad)}]}
    with pytest.raises(tas.TrackASourceError, match="months covered"):
        tas.frames_for_target(manifest, {SHARD_NAME: bad}.__getitem__)


def test_wrong_cell_count_rejected():
    manifest = {**MANIFEST, "expected_cell_count": 7}
    with pytest.raises(tas.TrackASourceError, match="cells"):
        tas.frames_for_target(manifest, {SHARD_NAME: SHARD}.__getitem__)


def test_manifest_missing_required_field_rejected():
    truncated = {k: v for k, v in MANIFEST.items() if k != "expected_months"}
    with pytest.raises(tas.TrackASourceError, match="expected_months"):
        tas.read_manifest(json.dumps(truncated).encode())


def test_shards_are_fetched_one_at_a_time_not_all_up_front(monkeypatch):
    """The bound this function's memory shape depends on — register C-101.

    ``frames_for_target`` took a filled dict until 2026-08-14, so every shard of a
    target was resident before the first was decoded. Measured at 36 shards, that plus
    stacking with ``np.concatenate`` put peak at **3.06x the delivered frame**, in three
    roughly equal thirds: the raw bytes, the per-shard frames, and the concatenated
    copy. Fetching per shard and filling a manifest-sized buffer took it to **1.13x**.

    This asserts the *interleaving*, not a byte count, and deliberately so: a memory
    threshold in a test is a flake on a busy machine, whereas "fetch, decode, fetch,
    decode" is the property that actually bounds the peak and it is exactly observable.
    Reverting to a pre-built dict makes the sequence fetch-fetch-decode-decode and this
    fails; nothing else in the suite would notice.
    """
    manifest = {
        **MANIFEST,
        "shards": [{"name": f"shard-{i}", "sha256": SHARD_SHA} for i in range(3)],
        "expected_months": [543, 543, 543],
    }
    events = []
    real_read_shard = tas.read_shard

    def spy(shard_bytes, *, expected_sha256):
        events.append("decode")
        return real_read_shard(shard_bytes, expected_sha256=expected_sha256)

    monkeypatch.setattr(tas, "read_shard", spy)

    def fetch(name):
        events.append("fetch")
        return SHARD

    tas.frames_for_target(manifest, fetch)

    assert events == ["fetch", "decode"] * 3, (
        f"shards are not being fetched one at a time: {events}. Every 'fetch' that "
        "precedes another 'fetch' is a shard's bytes held while the next is downloaded "
        "— at 36 shards that was a third of the peak."
    )


def test_shards_with_different_draw_counts_are_refused_in_our_own_words():
    """A run whose shards disagree on S is not one forecast — say so, do not let numpy.

    The assembly buffer's width is fixed by the first shard, which makes a draw-count
    disagreement this function's constraint rather than an incidental one. Left to the
    assignment it surfaces as ``could not broadcast input array from shape (6,2) into
    shape (12,4)`` — no shard named, no mention of draws, three frames from anything a
    reader recognises. The stacking it replaced was no better, only wordier; neither is
    a refusal, which is the whole of C-99's lesson applied before it could bite again.
    """
    narrow_values = io.BytesIO()
    np.save(narrow_values, np.zeros((6, 2), dtype=np.float32))
    narrow = _retouched_shard(**{
        "y_pred.npy": narrow_values.getvalue(),
        "metadata.json": _header(sample_count=2, time_id=544),
    })
    manifest = {
        **MANIFEST,
        "shards": [
            {"name": SHARD_NAME, "sha256": SHARD_SHA},
            {"name": "narrow", "sha256": _sha(narrow)},
        ],
        "expected_months": [543, 544],
    }
    with pytest.raises(tas.TrackASourceError, match="draws per cell"):
        tas.frames_for_target(manifest, {SHARD_NAME: SHARD, "narrow": narrow}.__getitem__)
