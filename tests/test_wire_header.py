"""§2 header builder (wire/header.py) — byte parity with both fixture envelopes."""

import json
import zipfile
from pathlib import Path

import pytest
from views_frames.io import arrow as vf_arrow

from views_postprocessing.contract.wire import header

_FIX = Path(__file__).resolve().parent / "fixtures" / "wire_contract"

_FIXTURE_KWARGS = dict(
    sample_count=4,
    dtype="float32",
    target="lr_ged_sb",
    time_id=543,
    run_id="fixture_run_0",
    generated_at="2026-07-15T00:00:00Z",
    provenance={
        "ensemble": "fixture_ensemble",
        "pipeline_core_version": "0.0.0-fixture",
        "reconciled": False,
    },
    sharding_index=0,
    sharding_count=1,
)


def test_byte_parity_with_the_track_a_header():
    with zipfile.ZipFile(_FIX / "fixture_run_0__lr_ged_sb__m000543.tap.zip") as zf:
        canonical = zf.read("metadata.json")
    built = json.dumps(header.build_header(**_FIXTURE_KWARGS), indent=2).encode()
    assert built == canonical  # ONE header, byte-for-byte (§2 key-order rule)


def test_equals_the_arrow_shard_embedded_header():
    state = vf_arrow.load(_FIX / "fixture_run_0__lr_ged_sb__m000543.arrow.parquet")
    assert header.build_header(**_FIXTURE_KWARGS) == state["metadata"]


def test_extra_provenance_key_raises():
    kwargs = dict(_FIXTURE_KWARGS)
    kwargs["provenance"] = {**kwargs["provenance"], "git_sha": "abc"}
    with pytest.raises(header.HeaderError, match="git_sha"):
        header.build_header(**kwargs)


def test_missing_provenance_key_raises():
    kwargs = dict(_FIXTURE_KWARGS)
    kwargs["provenance"] = {"ensemble": "e"}
    with pytest.raises(header.HeaderError, match="missing"):
        header.build_header(**kwargs)


def test_provenance_key_order_is_pinned_regardless_of_input_order():
    kwargs = dict(_FIXTURE_KWARGS)
    kwargs["provenance"] = dict(reversed(list(kwargs["provenance"].items())))
    built = json.dumps(header.build_header(**kwargs), indent=2).encode()
    with zipfile.ZipFile(_FIX / "fixture_run_0__lr_ged_sb__m000543.tap.zip") as zf:
        assert built == zf.read("metadata.json")


def test_contract_version_matches_the_canonical_manifest():
    manifest = json.loads((_FIX / "fixture_run_0__lr_ged_sb__manifest.json").read_text())
    assert manifest["contract_version"] == header.CONTRACT_VERSION
