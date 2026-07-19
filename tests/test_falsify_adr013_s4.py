"""Falsification stubs for the claim "ADR-013 §4 (Hop B) is sufficient and
unambiguous" (audit 2026-07-19, verdict FALSIFIED — 4 hard, 2 soft).

Each xfail documents one gap in §4 as probed; a stub starts passing when its gap is
fixed (non-strict — findings, not tripwires).
"""

import re
from pathlib import Path

import pytest

_ADR = Path(__file__).resolve().parent.parent / "docs" / "ADRs" / "013_sampled_forecast_wire_contract.md"


def _s4() -> str:
    text = _ADR.read_text()
    return re.sub(r"\s+", " ", text.split("## §4 Hop B")[1].split("## §5 GAUL")[0])


@pytest.mark.xfail(reason="P1: run-manifest field names unpinned; sidecar is an object (name+sha256) not 'the sidecar hash'; per-shard target/time_id unmentioned", strict=False)
def test_s4_manifest_fields_match_fixture():
    s4 = _s4()
    assert "expected_months" in s4
    assert re.search(r"shards?[^.]{0,250}time_id", s4)
    assert re.search(r"sidecar[^.]{0,200}name[^.]{0,80}sha256", s4)


@pytest.mark.xfail(reason="P3: Hop-B file name templates absent; doc-field `name` vs file-name duality unexplained", strict=False)
def test_s4_names_hop_b_templates():
    s4 = _s4()
    assert ".arrow.parquet" in s4 and "__manifest.json" in s4 and "__sidecar.parquet" in s4


@pytest.mark.xfail(reason="P8: sidecar outside the commit-marker ordering — manifest-last must cover shards AND sidecar", strict=False)
def test_s4_sidecar_inside_commit_ordering():
    assert re.search(r"after[^.]{0,160}shards[^.]{0,120}sidecar|sidecar[^.]{0,120}before the manifest", _s4(), re.I)


@pytest.mark.xfail(reason="P6: 'C-71 approval fields present' names no fields and no values", strict=False)
def test_s4_c71_approval_fields_pinned():
    assert re.search(r"approval[^.]{0,200}`\w+`", _s4())


@pytest.mark.xfail(reason="P2: §4.2's expected cell count does not inherit §3.2's per-shard ruling explicitly", strict=False)
def test_s4_cell_count_ruling_inherited():
    assert re.search(r"cell.count[^.]{0,160}(§3\.2|per shard|each shard)", _s4(), re.I)


@pytest.mark.xfail(reason="P5: §4.5(b) omits that arrow.load discards the column — the check needs a separate raw-table read", strict=False)
def test_s4_ordering_check_mechanics():
    assert re.search(r"discard[^.]{0,200}(raw|separate|parquet table|read_table)", _s4(), re.I)
