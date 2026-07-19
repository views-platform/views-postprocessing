"""Guards born from the falsification audit of "ADR-013 §5 is sufficient and
unambiguous" (audit 2026-07-19, FALSIFIED — 2 hard, 4 soft; all fixed same day).

Each test now enforces one fixed gap in §5 permanently.

"""

import re
from pathlib import Path


_ADR = Path(__file__).resolve().parent.parent / "docs" / "ADRs" / "013_sampled_forecast_wire_contract.md"


def _s5() -> str:
    text = _ADR.read_text()
    return re.sub(r"\s+", " ", text.split("## §5 GAUL")[1].split("## §6 The no-collapse")[0])


def test_s5_priogrid_id_is_a_column():
    assert re.search(r"priogrid_id.{0,140}(first column|a column|10 columns|ten columns)", _s5(), re.I)


def test_s5_code_dtype_stable():
    assert re.search(r"(always float64|float64 always|float64 regardless)", _s5(), re.I)


def test_s5_names_data_source():
    assert re.search(r"(gaul_lookup|ADR-011|datafactory)", _s5(), re.I)


def test_s5_null_representation():
    assert re.search(r"string[^.]{0,120}(null|None)|(null|None)[^.]{0,120}string", _s5())


def test_s5_c146_glossed():
    assert re.search(r"C-146[^.]{0,200}(drop|parity|aggregation)", _s5())


def test_s5_no_present_tense_overclaim():
    assert re.search(r"(extend|extension)\w*[^.]{0,140}(#91|to be built|future|at implementation|not yet)", _s5(), re.I)


def test_s5_column_and_row_order():
    assert re.search(r"(column order|ascending)[^.]{0,160}(pinned|normative|priogrid_id|fixture|§10)", _s5(), re.I)
