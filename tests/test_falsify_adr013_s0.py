"""Guards born from the falsification audit of the claim "ADR-013 §0 alone suffices to understand the
flow" (audit 2026-07-19, verdict FALSIFIED — 2 hard, 5 soft; all findings fixed same day).

Each test now enforces one fixed gap in §0 permanently.

"""

import re
from pathlib import Path


_ADR = Path(__file__).resolve().parent.parent / "docs" / "ADRs" / "013_sampled_forecast_wire_contract.md"


def _s0() -> str:
    text = _ADR.read_text()
    return text.split("## §0 Status and provenance")[1].split("## §1 ")[0]


def test_s0_states_current_execution_status():
    assert re.search(r"[Ss]tatus of execution|operates today|not yet (live|built|deployed)", _s0())


def test_s0_mentions_commit_marker_semantics():
    assert "commit marker" in _s0() or "complete-or-invisible" in _s0()


def test_s0_anchors_its_jargon():
    s0 = _s0()
    pfe_anchored = "PFE (" in s0 or re.search(r"PFE[^.\n]{0,60}Vocabulary", s0)
    hops_anchored = re.search(r"Hop [AB][^.\n]{0,80}(Vocabulary|defined|§1)", s0)
    assert pfe_anchored and hops_anchored


def test_s0_mentions_historical_bypass():
    assert "historical" in _s0().lower()


def test_s0_has_no_undated_today():
    assert "today" not in _s0() or re.search(r"today \(", _s0())
