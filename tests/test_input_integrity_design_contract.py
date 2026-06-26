"""Design-contract falsification stubs for the FAO input-integrity sprint (#51).

Surfaced by `/falsify` (2026-06-26), adjusted after review. The recommended
direction ("representation-agnostic invariants over primitives, fed by a thin
extraction adapter") only ALIGNS with the maintainer's SOLID + component +
screaming rubric if the implementation honours three tightenings:

  ① TWO homes, not one:
       views_postprocessing/delivery/        -> representation-free invariants +
                                                 constants (partner-agnostic, reusable)
       views_postprocessing/unfao/extraction.py -> the pandas->primitives seam
                                                 (FAO-local, representation-specific)
  ② Primitives are the abstraction (DIP); extraction isolated in one module (OCP).
       No premature Extractor Protocol (YAGNI/ISP) — a migration, not a coexistence.
  ③ Guards are CALLED by the manager, never METHODS of it — so C-40's eventual
       de-inheritance does not touch them. Manager LSP/SDP/SAP is DEFERRED to C-40.

Plus housekeeping: no "frame" name overload (DataFrame vs views_frames), and the
dead unfao/mapping/ husk removed.

All xfail(strict=True): GREEN while the gap exists; each PASSES the moment the
design is implemented correctly, which flips the strict-xfail RED and forces the
marker to be removed (the contract becomes a real assertion).
"""

import importlib.util
import re
from pathlib import Path

import pytest

_IMPORTS_PANDAS = re.compile(r"^\s*(?:import\s+pandas|from\s+pandas\b)", re.MULTILINE)

_PKG = Path(__file__).resolve().parent.parent / "views_postprocessing"


def _spec(name: str):
    try:
        return importlib.util.find_spec(name)
    except ModuleNotFoundError:
        return None


# ① — two homes -------------------------------------------------------------
def test_delivery_contract_package_exists():
    assert _spec("views_postprocessing.delivery") is not None


def test_delivery_invariants_are_pandas_free():
    d = _PKG / "delivery"
    assert d.exists() and not any(_IMPORTS_PANDAS.search(f.read_text()) for f in d.glob("*.py"))


def test_extraction_seam_is_isolated_in_one_module():
    assert (_PKG / "unfao" / "extraction.py").exists()


# ③ — called, never inherited (deferred to C-40) ----------------------------
@pytest.mark.xfail(strict=True, reason="③/P2/LSP/SDP/SAP: manager is-a ForecastingModelManager — DEFERRED to C-40, not fixed by this sprint")
def test_manager_does_not_inherit_forecasting_model_manager():
    src = (_PKG / "unfao" / "managers" / "unfao.py").read_text()
    assert "ForecastingModelManager" not in src


# housekeeping --------------------------------------------------------------
def test_enrichment_does_not_call_a_dataframe_a_prediction_frame():
    src = (_PKG / "unfao" / "enrichment.py").read_text().lower()
    assert "prediction frame" not in src


def test_no_lingering_mapping_directory():
    assert not (_PKG / "unfao" / "mapping").exists()
