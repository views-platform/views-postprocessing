"""Guards born from the batched falsification audit of ADR-013 §1/§7/§8/§9
(audit 2026-07-19: §1 and §9 SURVIVED; §7 CONTESTED — 2 soft; §8 CONTESTED —
1 soft; all fixed same day).

Each test enforces one fixed gap permanently.
"""

import re
from pathlib import Path

_ADR = Path(__file__).resolve().parent.parent / "docs" / "ADRs" / "013_sampled_forecast_wire_contract.md"


def _sec(start: str, end: str) -> str:
    text = _ADR.read_text()
    return re.sub(r"\s+", " ", text.split(start)[1].split(end)[0])


def test_s7_env_fix_status_dated():
    s7 = _sec("## §7 Prerequisites", "## §8 Non-goals")
    assert re.search(r"230-A.{0,400}(2026-07-19|re-verified)", s7)


def test_s7_retitle_marked_done():
    s7 = _sec("## §7 Prerequisites", "## §8 Non-goals")
    assert re.search(r"retitled[^.]{0,140}(done|ADR-013)", s7)


def test_s8_mmap_intent_has_tracking_issue():
    s8 = _sec("## §8 Non-goals", "## §9 Corrections")
    assert re.search(r"(mmap|hardening)[^.]{0,200}#\d+", s8, re.I)


def test_s9_fix_shipped_marker():
    s9 = _sec("## §9 Corrections", "## §10 Golden")
    assert re.search(r"#269[^.]{0,160}(shipped|Post-adoption)", s9)
