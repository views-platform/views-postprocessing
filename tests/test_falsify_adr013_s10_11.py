"""Guards born from the falsification audit of ADR-013 §10/§11
(audit 2026-07-19: both CONTESTED — 0 hard, 2 soft each; all fixed same day).

Each test enforces one fixed gap permanently.
"""

import re
from pathlib import Path

_ADR = Path(__file__).resolve().parent.parent / "docs" / "ADRs" / "013_sampled_forecast_wire_contract.md"


def _sec(start: str, end: str) -> str:
    text = _ADR.read_text()
    return re.sub(r"\s+", " ", text.split(start)[1].split(end)[0])


def test_s10_root_hash_mechanism_defined():
    s10 = _sec("## §10 Golden fixture", "## §11 Sequencing")
    assert "wire_contract" in s10  # the fixture's actual path is named
    assert re.search(r"root hash.{0,200}SHA256SUMS", s10, re.I)


def test_s11_two_vehicles_distinguished():
    s11 = _sec("## §11 Sequencing", "## Post-adoption record")
    assert re.search(r"S=8.{0,300}S=4|S=4.{0,300}S=8", s11)


def test_s11_guards_shipped_tense():
    s11 = _sec("## §11 Sequencing", "## Post-adoption record")
    assert re.search(r"merged 2026-07-15", s11)
