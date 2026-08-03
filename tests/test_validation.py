"""The metadata null-gate, tested where it actually lives (S4 / #185, register C-03).

**What this file used to be, and why it had to change.** It opened with:

    Note: views-pipeline-core may not be installed in test environments, so we
    replicate the validation logic here rather than importing the manager class.
    The logic tested matches unfao.py:_validate() exactly.

Both halves stopped being true.

*The replica.* The file defined its own ``validate_dataframe`` and then tested that.
Forty-odd parametrised cases exercised a function declared twelve lines above them and
**no production code at all** — a closed loop that could not fail while the delivery
broke, and could not tell a reader anything about the system.

*The fidelity claim.* ``_validate`` stopped null-gating in #149. Its own docstring now
says so: *"Neither payload is null-gated here."* It asserts the read **resolved** and
calls ``_check_coverage``. The null gate moved to ``contract/historical`` and fires at
artifact-build time. So the file asserted equivalence with a method it no longer
resembled, and had done since 2026-07-31.

*The column list.* ``REQUIRED_METADATA_COLS`` was a nine-element literal — a hand copy
of the contract that register **C-70** was resolved to make single-source. It is now
imported.

**What this file is now.** Tests of ``historical.assert_metadata_complete`` — the code
that actually gates a delivery — plus source-scan pins that the gate stays at build time
rather than drifting back into ``_validate``. The original justification for the replica
no longer applies either: ``contract/`` is dependency-light and imports without
views-pipeline-core (``tests/test_clone_readiness.py`` proves it in a subprocess).

The behaviour C-01 fixed — a null in a required GAUL column must stop the delivery
rather than ship — is preserved in full. It is simply asserted against the function that
performs it.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pyarrow as pa
import pytest

from views_postprocessing.contract import historical
from views_postprocessing.contract.gaul_schema import CODE_COLS, COORD_COLS, METADATA_COLS

_MANAGER_SOURCE = (
    Path(__file__).resolve().parent.parent
    / "views_postprocessing" / "unfao" / "managers" / "unfao.py"
)
_HISTORICAL_SOURCE = (
    Path(__file__).resolve().parent.parent
    / "views_postprocessing" / "contract" / "historical.py"
)


def _artifact(n_rows: int = 5) -> pa.Table:
    """A minimal historical artifact shaped like ``build_historical_table``'s output.

    Columns and dtypes come from ``gaul_schema`` (C-70), so this helper cannot drift
    from the declared contract — a rename there breaks the import, not a later assert.
    """
    columns = {
        "month_id": pa.array(np.full(n_rows, 500, dtype=np.int64)),
        "priogrid_id": pa.array(np.arange(100_001, 100_001 + n_rows, dtype=np.int64)),
        "sb_best": pa.array(np.zeros(n_rows, dtype=np.float32)),
    }
    for col in METADATA_COLS:
        if col in CODE_COLS or col in COORD_COLS:
            columns[col] = pa.array(np.arange(n_rows, dtype=np.float64))
        else:
            columns[col] = pa.array([f"{col}-value"] * n_rows, type=pa.string())
    return pa.table(columns)


def _with_null(col: str, row: int = 0, n_rows: int = 5) -> pa.Table:
    """The artifact with one metadata value knocked out — the C-01 defect, reproduced."""
    table = _artifact(n_rows)
    values = table.column(col).to_pylist()
    values[row] = None
    idx = table.column_names.index(col)
    return table.set_column(idx, col, pa.array(values, type=table.column(col).type))


# ── the gate ────────────────────────────────────────────────────────────────

def test_a_complete_artifact_passes():
    historical.assert_metadata_complete(_artifact())  # must not raise


@pytest.mark.parametrize("col", METADATA_COLS)
def test_a_null_in_any_required_metadata_column_stops_the_delivery(col):
    """C-01: incomplete geographic metadata must never reach the UN FAO.

    Parametrised over the **imported** contract, not a copy — add a column to
    ``gaul_schema.COLUMNS`` and it is gated here automatically, which is the property
    C-70 was resolved to give us.
    """
    with pytest.raises(historical.HistoricalArtifactError):
        historical.assert_metadata_complete(_with_null(col))


def test_the_refusal_names_the_column_and_counts_the_nulls():
    """A refusal an operator cannot act on is barely better than no refusal."""
    with pytest.raises(historical.HistoricalArtifactError) as excinfo:
        historical.assert_metadata_complete(_with_null("country_iso_a3", n_rows=10))
    message = str(excinfo.value)
    assert "country_iso_a3" in message, "the refusal must name the offending column"
    assert "1/10" in message, "the refusal must say how much of the artifact is affected"


def test_every_declared_metadata_column_is_gated():
    """The gate iterates the declared contract; nothing is gated by coincidence.

    Reads the source on purpose — the parametrised test above proves each column *is*
    caught; this proves it is caught **because** the column is declared, rather than
    because someone happened to list it twice.
    """
    assert "for col in METADATA_COLS:" in _HISTORICAL_SOURCE.read_text(), (
        "assert_metadata_complete must iterate the declared METADATA_COLS. A hand-written "
        "column list here is register C-70 returning: one contract, two spellings."
    )


# ── where the gate lives, and where it must not drift back to ───────────────

def test_the_manager_does_not_null_gate_in_validate():
    """#149 moved the gate to build time. A silent move back would double-gate the
    historical leg while leaving the forecast leg — which is arrow, not pandas — with a
    gate written for a representation it no longer uses.

    Source-scan because the manager needs views-pipeline-core and Appwrite env to
    instantiate; this is the repo's standing pattern for manager-side facts.
    """
    source = _MANAGER_SOURCE.read_text()
    validate_body = source.split("def _validate(")[1].split("def _check_coverage(")[0]
    for token in ("isnull", "is_null", "null_count", "METADATA_COLS"):
        assert token not in validate_body, (
            f"_validate references {token!r} again. The metadata null-gate belongs at "
            "artifact build (historical.assert_metadata_complete), where the artifact "
            "exists; _validate asserts that the read resolved. See #149."
        )


def test_the_manager_still_calls_the_gate_on_the_built_artifact():
    """The other half: having moved, the gate must actually be invoked somewhere."""
    assert "historical.assert_metadata_complete(" in _MANAGER_SOURCE.read_text(), (
        "nothing calls the metadata null-gate — the historical artifact would ship with "
        "missing geography and no error signal (register C-01, C-43)."
    )
