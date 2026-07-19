"""Falsification stubs for the claim "ADR-013 §3 (Hop A) is sufficient and
unambiguous" (audit 2026-07-19, verdict FALSIFIED — 2 hard, 4 soft).

Each xfail documents one gap in §3 as probed; a stub starts passing when its gap is
fixed (non-strict — findings, not tripwires).
"""

import re
from pathlib import Path

import pytest

_ADR = Path(__file__).resolve().parent.parent / "docs" / "ADRs" / "013_sampled_forecast_wire_contract.md"


def _s3() -> str:
    text = _ADR.read_text()
    return re.sub(r"\s+", " ", text.split("## §3 Hop A")[1].split("## §4 Hop B")[0])


@pytest.mark.xfail(reason="P1: §3.2 claims 'store file-ids' the fixture manifest does not carry, and pins no manifest field names", strict=False)
def test_s3_manifest_fields_match_fixture():
    s3 = _s3()
    assert "file-ids" not in s3  # the fixture manifest has name+sha256, no file-id
    assert "expected_months" in s3 and "expected_cell_count" in s3 and "sha256" in s3


@pytest.mark.xfail(reason="P6: expected_cell_count scope (per shard vs per (run,target) total) undecidable from §3", strict=False)
def test_s3_cell_count_scope_defined():
    assert re.search(r"cell.count[^.]{0,160}(per shard|each shard|every shard|per month|one month)", _s3(), re.I)


@pytest.mark.xfail(reason="P2: identifiers.npz member names (time.npy/unit.npy) and int64 dtypes unpinned", strict=False)
def test_s3_npz_members_pinned():
    s3 = _s3()
    assert "time.npy" in s3 and "unit.npy" in s3 and "int64" in s3


@pytest.mark.xfail(reason="P3: hash algorithm and coverage (SHA-256 of the whole zip bytes) unstated", strict=False)
def test_s3_hash_algorithm_and_coverage():
    assert re.search(r"SHA-?256[^.]{0,120}(zip|archive|whole|entire|bytes)", _s3(), re.I)


@pytest.mark.xfail(reason="P5: the manifest's own store-document fields (category/name/targets/loa) unspecified", strict=False)
def test_s3_manifest_store_document_fields():
    assert re.search(r"manifest[^.]{0,250}category", _s3(), re.I)


@pytest.mark.xfail(reason="P7: '.tap' never expanded (Track A Package)", strict=False)
def test_s3_tap_explained():
    assert re.search(r"tap[^.]{0,80}(Track.?A|package)", _s3(), re.I)
