"""§4.2 run manifest builder (wire/run_manifest.py) — byte parity with the fixture."""

import hashlib
from pathlib import Path

import pytest

from views_postprocessing.unfao.wire import run_manifest

_FIX = Path(__file__).resolve().parent / "fixtures" / "wire_contract"


def _sha(name: str) -> str:
    return hashlib.sha256((_FIX / name).read_bytes()).hexdigest()


def _fixture_kwargs() -> dict:
    return dict(
        run_id="fixture_run_0",
        targets=["lr_ged_sb"],
        shard_records=[
            {
                "name": "fixture_run_0__lr_ged_sb__m000543.arrow.parquet",
                "target": "lr_ged_sb",
                "time_id": 543,
                "sha256": _sha("fixture_run_0__lr_ged_sb__m000543.arrow.parquet"),
            }
        ],
        expected_months=[543],
        expected_cell_count=6,
        sidecar_record={
            "name": "fixture_run_0__sidecar.parquet",
            "sha256": _sha("fixture_run_0__sidecar.parquet"),
        },
    )


def test_byte_parity_with_the_fixture_run_manifest():
    built = run_manifest.build_run_manifest(**_fixture_kwargs())
    assert built == (_FIX / "fixture_run_0__manifest.json").read_bytes()


def test_shard_record_with_extra_key_raises():
    kwargs = _fixture_kwargs()
    kwargs["shard_records"][0]["file_id"] = "nope"  # the field §3.2 corrected away
    with pytest.raises(run_manifest.RunManifestError, match="file_id"):
        run_manifest.build_run_manifest(**kwargs)


def test_sidecar_record_missing_hash_raises():
    kwargs = _fixture_kwargs()
    kwargs["sidecar_record"] = {"name": "x"}
    with pytest.raises(run_manifest.RunManifestError, match="sha256"):
        run_manifest.build_run_manifest(**kwargs)


def test_shard_record_key_order_is_pinned_regardless_of_input_order():
    kwargs = _fixture_kwargs()
    kwargs["shard_records"][0] = dict(reversed(list(kwargs["shard_records"][0].items())))
    built = run_manifest.build_run_manifest(**kwargs)
    assert built == (_FIX / "fixture_run_0__manifest.json").read_bytes()
