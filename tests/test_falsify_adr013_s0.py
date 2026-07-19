"""Falsification stubs for the claim "ADR-013 §0 alone suffices to understand the
flow" (audit 2026-07-19, verdict FALSIFIED — 2 hard, 5 soft).

Each xfail documents one gap in §0 as probed; a stub starts XPASSing when its gap
is fixed (non-strict by design — these record findings, they are not tripwires).
"""

import re
from pathlib import Path

import pytest

_ADR = Path(__file__).resolve().parent.parent / "docs" / "ADRs" / "013_sampled_forecast_wire_contract.md"


def _s0() -> str:
    text = _ADR.read_text()
    return text.split("## §0 Status and provenance")[1].split("## §1 ")[0]


@pytest.mark.xfail(reason="P4: §0 carries no dated current-execution-status statement", strict=False)
def test_s0_states_current_execution_status():
    assert re.search(r"[Ss]tatus of execution|operates today|not yet (live|built|deployed)", _s0())


@pytest.mark.xfail(reason="P2: torn-run / complete-or-invisible semantics absent from §0", strict=False)
def test_s0_mentions_commit_marker_semantics():
    assert "commit marker" in _s0() or "complete-or-invisible" in _s0()


@pytest.mark.xfail(reason="P1b/P3: PFE, Hop A/B, no-collapse used in §0 without definition or explicit Vocabulary pointer", strict=False)
def test_s0_anchors_its_jargon():
    s0 = _s0()
    pfe_anchored = "PFE (" in s0 or re.search(r"PFE[^.\n]{0,60}Vocabulary", s0)
    hops_anchored = re.search(r"Hop [AB][^.\n]{0,80}(Vocabulary|defined|§1)", s0)
    assert pfe_anchored and hops_anchored


@pytest.mark.xfail(reason="P6: the historical artifact's bypass of both hops is absent from §0", strict=False)
def test_s0_mentions_historical_bypass():
    assert "historical" in _s0().lower()


@pytest.mark.xfail(reason="P5-bonus: undated 'today' in the §0 table legend (dated-snapshot rule violated)", strict=False)
def test_s0_has_no_undated_today():
    assert "today" not in _s0() or re.search(r"today \(", _s0())
