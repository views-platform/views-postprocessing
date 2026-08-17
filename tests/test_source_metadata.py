"""The producer-fact seam: what happens when the producer cannot be asked (C-103).

``contract/source_metadata.py`` is the single place this repository asks
views-datafactory for a data fact, and until 2026-08-17 it had **no tests at all** —
which is how the defect below survived: nothing described what the module should do
when the client is absent, so "return None like everything else" looked reasonable.

The distinction these tests pin is the whole point of the module:

* the producer publishes **no boundary** — a normal, older store. The caller degrades
  open and delivers unclipped (C-26, a recorded decision).
* the producer **cannot be asked at all** — a broken environment. Degrading open here
  ships the unobserved zero-padded tail as observed history, and does it with one
  WARNING in a log nobody reads.

Same shape as C-60, where a provenance stamp degraded to ``"unknown"`` on a bare
except and made every delivery untraceable in exactly the field it existed to answer.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from views_postprocessing.contract import source_metadata

_REPO = Path(__file__).resolve().parent.parent


def test_a_missing_client_raises_rather_than_reporting_no_boundary():
    """``datafactory_query`` is genuinely absent here, so this needs no simulation."""
    with pytest.raises(source_metadata.ProducerClientMissing):
        source_metadata.last_valid_month_id()


def test_the_refusal_names_the_package_and_why_it_is_not_None():
    with pytest.raises(source_metadata.ProducerClientMissing) as excinfo:
        source_metadata.last_valid_month_id()
    message = str(excinfo.value)
    assert "views-datafactory" in message, "the refusal must name the package to install"
    assert "datafactory_query" in message, "and the module that was actually missing"
    # The reader must be able to tell this apart from the degrade-open case.
    assert "observed" in message, (
        "the refusal must say what degrading open would have cost — unobserved months "
        "shipping as observed history — or it reads as a routine unavailability"
    )


def test_the_refusal_chains_the_original_importerror():
    """``raise ... from exc``: the traceback must still say what could not be imported."""
    with pytest.raises(source_metadata.ProducerClientMissing) as excinfo:
        source_metadata.last_valid_month_id()
    assert isinstance(excinfo.value.__cause__, ImportError)


def test_it_is_logged_as_well_as_raised(caplog):
    """ADR-008: a refusal on the delivery path is logged persistently AND raised."""
    with caplog.at_level("ERROR"), pytest.raises(source_metadata.ProducerClientMissing):
        source_metadata.last_valid_month_id()
    assert any(r.levelname == "ERROR" for r in caplog.records), (
        "the refusal was raised but never logged; a traceback that dies inside a "
        "scheduled run leaves no persistent record (ADR-008)"
    )


def test_the_producers_answer_passes_through_untouched(monkeypatch):
    """When the client IS present, this module reads and returns — it does not decide.

    Including ``None``: a store that predates the attribute reports no boundary, and
    that is the case the caller is entitled to degrade open on.
    """
    import types

    for answer in (137, None):
        fake = types.ModuleType("datafactory_query")
        defaults = types.ModuleType("datafactory_query.defaults")
        seen = {}

        def get_last_valid_month_id(zarr_url=None, _answer=answer):
            seen["zarr_url"] = zarr_url
            return _answer

        defaults.get_last_valid_month_id = get_last_valid_month_id
        fake.defaults = defaults
        monkeypatch.setitem(sys.modules, "datafactory_query", fake)
        monkeypatch.setitem(sys.modules, "datafactory_query.defaults", defaults)

        assert source_metadata.last_valid_month_id("zarr://declared") == answer
        assert seen["zarr_url"] == "zarr://declared", (
            "the declared store must be passed through; guessing the producer's "
            "default here would be the inference ADR-003 forbids"
        )


@pytest.mark.parametrize("partner", ("unfao", "crafd"))
def test_the_managers_do_not_swallow_the_refusal(partner):
    """The degrade-open must not re-absorb what this module just refused.

    A source check rather than a behavioural one, deliberately: constructing a manager
    needs pipeline-core, a path manager and an Appwrite environment (C-40), and the
    property worth pinning is one line — that ``ProducerClientMissing`` is re-raised
    *before* the broad ``except``. Someone tidying the two branches back into one is
    precisely how C-103 would return, and it would return silently.
    """
    source = (_REPO / "views_postprocessing" / partner / "managers" / f"{partner}.py").read_text()
    assert "except source_metadata.ProducerClientMissing:" in source, (
        f"{partner}'s manager no longer re-raises ProducerClientMissing, so a broken "
        "environment is once again indistinguishable from a producer that publishes "
        "no boundary — and the delivery ships fabricated months either way (C-103)."
    )
    refusal = source.index("except source_metadata.ProducerClientMissing:")
    broad = source.index("except Exception:", refusal - 2000 if refusal > 2000 else 0)
    assert refusal < broad, (
        f"{partner}'s manager catches Exception before ProducerClientMissing, so the "
        "narrow branch is unreachable"
    )
