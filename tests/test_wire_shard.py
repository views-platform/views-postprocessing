"""Hop-B shard writer (wire/shard.py) — byte parity with the fixture arrow shard.

The byte tests assert the pinned toolchain (fixture README: pyarrow 16.1.0, matching
`_PINNED_PYARROW` below and the `>=16.1.0,<17.0.0` constraint) and
FAIL LOUD on drift — never skip-silent: a quiet skip would read as conformance.
"""

import hashlib
import zipfile
from pathlib import Path

import pyarrow
import pytest

from views_postprocessing.contract import track_a_source
from views_postprocessing.contract.frame_extraction import month_slice
from views_postprocessing.contract.wire import header as wire_header
from views_postprocessing.contract.wire import shard as wire_shard

_FIX = Path(__file__).resolve().parent / "fixtures" / "wire_contract"
_PINNED_PYARROW = "16.1.0"


def _fixture_frame_and_header():
    manifest_bytes = (_FIX / "fixture_run_0__lr_ged_sb__manifest.json").read_bytes()
    manifest = track_a_source.read_manifest(manifest_bytes)
    shard_bytes = (_FIX / manifest["shards"][0]["name"]).read_bytes()
    return track_a_source.read_shard(
        shard_bytes, expected_sha256=manifest["shards"][0]["sha256"]
    )


def test_toolchain_is_pinned():
    assert pyarrow.__version__ == _PINNED_PYARROW, (
        f"pinned toolchain violated: byte-parity oracle requires pyarrow "
        f"{_PINNED_PYARROW}, found {pyarrow.__version__} — re-pin the environment "
        f"or regenerate the fixture (a contract change, §10)."
    )


def test_byte_parity_with_the_fixture_arrow_shard(tmp_path):
    frame, track_a_header = _fixture_frame_and_header()
    values, time, unit = month_slice(frame, 543)
    built_header = wire_header.build_header(
        sample_count=track_a_header["sample_count"],
        dtype=track_a_header["dtype"],
        target=track_a_header["target"],
        time_id=track_a_header["time_id"],
        run_id=track_a_header["run_id"],
        generated_at=track_a_header["generated_at"],
        provenance=track_a_header["provenance"],
        sharding_index=track_a_header["sharding"]["index"],
        sharding_count=track_a_header["sharding"]["count"],
    )
    name, sha = wire_shard.write_shard(
        values, time, unit, header=built_header, directory=tmp_path
    )
    assert name == "fixture_run_0__lr_ged_sb__m000543.arrow.parquet"
    canonical = (_FIX / name).read_bytes()
    assert (tmp_path / name).read_bytes() == canonical
    assert sha == hashlib.sha256(canonical).hexdigest()


def test_sha_matches_sha256sums(tmp_path):
    frame, track_a_header = _fixture_frame_and_header()
    values, time, unit = month_slice(frame, 543)
    _, sha = wire_shard.write_shard(
        values, time, unit, header=track_a_header, directory=tmp_path
    )
    sums = (_FIX / "SHA256SUMS").read_text()
    assert f"{sha}  fixture_run_0__lr_ged_sb__m000543.arrow.parquet" in sums


def test_month_slice_missing_month_fails_loud():
    frame, _ = _fixture_frame_and_header()
    with pytest.raises(ValueError, match="month 999"):
        month_slice(frame, 999)


def test_header_passthrough_survives_roundtrip(tmp_path):
    # The embedded metadata equals the Track-A header — one header, both envelopes.
    from views_frames.io import arrow as vf_arrow

    frame, track_a_header = _fixture_frame_and_header()
    values, time, unit = month_slice(frame, 543)
    name, _ = wire_shard.write_shard(
        values, time, unit, header=track_a_header, directory=tmp_path
    )
    with zipfile.ZipFile(_FIX / "fixture_run_0__lr_ged_sb__m000543.tap.zip") as zf:
        assert zf.read("metadata.json")  # fixture sanity
    assert vf_arrow.load(tmp_path / name)["metadata"] == track_a_header
