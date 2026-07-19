"""Falsification stubs for the claim "ADR-013 §2 (shared header) is sufficient and
unambiguous" (audit 2026-07-19, verdict FALSIFIED — 2 hard, 3 soft).

Each xfail documents one gap in §2 as probed; a stub starts passing when its gap is
fixed (non-strict — these record findings, they are not tripwires).
"""

import re
from pathlib import Path

import pytest

_ADR = Path(__file__).resolve().parent.parent / "docs" / "ADRs" / "013_sampled_forecast_wire_contract.md"


def _s2() -> str:
    text = _ADR.read_text()
    return text.split("## §2 Shared contract header")[1].split("## §3 ")[0]


@pytest.mark.xfail(reason="P1: run_id / generated_at / sharding / time_id / enums underdefined in §2", strict=False)
def test_s2_defines_field_formats():
    s2 = _s2()
    assert "ISO" in s2  # generated_at format stated
    assert re.search(r"run_id[^.]{0,120}(unique|mint|format)", s2)
    assert re.search(r"index[^.]{0,80}(0-based|zero-based|position)", s2)
    assert re.search(r"time_id[^.]{0,120}(month of this shard|the shard's month|one month)", s2)


@pytest.mark.xfail(reason="P2: key-order/byte-parity rule absent while §10 pins header bytes", strict=False)
def test_s2_states_key_order_rule():
    assert re.search(r"(key )?order[^.]{0,120}(§10|fixture|byte)", _s2(), re.I)


@pytest.mark.xfail(reason="P3: 'open to additions' vs provenance 'exactly the three keys' unresolved for nested keys", strict=False)
def test_s2_resolves_open_vs_closed_provenance():
    assert re.search(r"provenance[^.]{0,200}(addition|extra key|unknown key|closed)", _s2(), re.I | re.S)


@pytest.mark.xfail(reason="P5: §2 names neither §7a (target vocabulary) nor §10 (the fixture pinning these bytes)", strict=False)
def test_s2_points_at_its_companions():
    s2 = _s2()
    assert "§10" in s2 and "§7" in s2


@pytest.mark.xfail(reason="P6: 'the gid/id epic' is unexplained insider jargon", strict=False)
def test_s2_has_no_unexplained_gid_epic():
    s2 = re.sub(r"\s+", " ", _s2())  # markdown hard-wraps; compare on one line
    if "gid/id epic" in s2:
        # keeping the phrase requires an inline explanation of what that episode was
        assert re.search(r"gid/id epic[^.]{0,200}(identifier|meant|ambigu)", s2)
