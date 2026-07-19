"""Guards born from the falsification audit of "ADR-013 §2 is sufficient and
unambiguous" (audit 2026-07-19, FALSIFIED — 2 hard, 3 soft; all fixed same day).

Each test now enforces one fixed gap in §2 permanently.

"""

import re
from pathlib import Path


_ADR = Path(__file__).resolve().parent.parent / "docs" / "ADRs" / "013_sampled_forecast_wire_contract.md"


def _s2() -> str:
    text = _ADR.read_text()
    return text.split("## §2 Shared contract header")[1].split("## §3 ")[0]


def test_s2_defines_field_formats():
    s2 = _s2()
    assert "ISO" in s2  # generated_at format stated
    assert re.search(r"run_id[^.]{0,120}(unique|mint|format)", s2)
    assert re.search(r"index[^.]{0,80}(0-based|zero-based|position)", s2)
    assert re.search(r"time_id[^.]{0,120}(month of this shard|the shard's month|one month)", s2)


def test_s2_states_key_order_rule():
    assert re.search(r"(key )?order[^.]{0,120}(§10|fixture|byte)", _s2(), re.I)


def test_s2_resolves_open_vs_closed_provenance():
    assert re.search(r"provenance[^.]{0,200}(addition|extra key|unknown key|closed)", _s2(), re.I | re.S)


def test_s2_points_at_its_companions():
    s2 = _s2()
    assert "§10" in s2 and "§7" in s2


def test_s2_has_no_unexplained_gid_epic():
    s2 = re.sub(r"\s+", " ", _s2())  # markdown hard-wraps; compare on one line
    if "gid/id epic" in s2:
        # keeping the phrase requires an inline explanation of what that episode was
        assert re.search(r"gid/id epic[^.]{0,200}(identifier|meant|ambigu)", s2)
