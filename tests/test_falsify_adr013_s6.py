"""Guards born from the falsification audit of "ADR-013 §6 is sufficient and
unambiguous" (audit 2026-07-19, CONTESTED — 0 hard, 2 soft; both fixed same day).

First section of the series to survive without a hard finding: the four rules match
delivery/draws.py exactly. Each test enforces one fixed soft gap permanently.
"""

import re
from pathlib import Path

_ADR = Path(__file__).resolve().parent.parent / "docs" / "ADRs" / "013_sampled_forecast_wire_contract.md"


def _s6() -> str:
    text = _ADR.read_text()
    return re.sub(r"\s+", " ", text.split("## §6 The no-collapse")[1].split("## §7 Prerequisites")[0])


def test_s6_nan_semantics_stated():
    assert re.search(r"NaN[^.]{0,200}(non-degenerate|varied|null gate)", _s6())


def test_s6_wiring_status_honest():
    assert re.search(r"(#91|not yet built|PR #98)", _s6())
