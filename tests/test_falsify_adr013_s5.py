"""Falsification stubs for the claim "ADR-013 §5 (GAUL sidecar) is sufficient and
unambiguous" (audit 2026-07-19, verdict FALSIFIED — 2 hard, 4 soft).

Each xfail documents one gap in §5 as probed; a stub starts passing when its gap is
fixed (non-strict — findings, not tripwires).
"""

import re
from pathlib import Path

import pytest

_ADR = Path(__file__).resolve().parent.parent / "docs" / "ADRs" / "013_sampled_forecast_wire_contract.md"


def _s5() -> str:
    text = _ADR.read_text()
    return re.sub(r"\s+", " ", text.split("## §5 GAUL")[1].split("## §6 The no-collapse")[0])


@pytest.mark.xfail(reason="P1: priogrid_id is the file's FIRST COLUMN (10 columns total), not an index — unstated", strict=False)
def test_s5_priogrid_id_is_a_column():
    assert re.search(r"priogrid_id.{0,140}(first column|a column|10 columns|ten columns)", _s5(), re.I)


@pytest.mark.xfail(reason="P2: code dtype is data-dependent (int64 vs float64) — schema instability; fixture pins float64", strict=False)
def test_s5_code_dtype_stable():
    assert re.search(r"(always float64|float64 always|float64 regardless)", _s5(), re.I)


@pytest.mark.xfail(reason="P3: the sidecar's data source (ADR-011 gaul_lookup / datafactory) never named", strict=False)
def test_s5_names_data_source():
    assert re.search(r"(gaul_lookup|ADR-011|datafactory)", _s5(), re.I)


@pytest.mark.xfail(reason="P4a: string columns carry null/None, not NaN — 'preserved with NaN' imprecise", strict=False)
def test_s5_null_representation():
    assert re.search(r"string[^.]{0,120}(null|None)|(null|None)[^.]{0,120}string", _s5())


@pytest.mark.xfail(reason="P4b: C-146 is a bare insider reference", strict=False)
def test_s5_c146_glossed():
    assert re.search(r"C-146[^.]{0,200}(drop|parity|aggregation)", _s5())


@pytest.mark.xfail(reason="P5: 'extended to the sidecar' is future #91 work stated as present fact", strict=False)
def test_s5_no_present_tense_overclaim():
    assert re.search(r"(extend|extension)\w*[^.]{0,140}(#91|to be built|future|at implementation|not yet)", _s5(), re.I)


@pytest.mark.xfail(reason="P6: column order and row order pinned by the fixture but not stated as normative", strict=False)
def test_s5_column_and_row_order():
    assert re.search(r"(column order|ascending)[^.]{0,160}(pinned|normative|priogrid_id|fixture|§10)", _s5(), re.I)
