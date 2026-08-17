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
import types
from pathlib import Path

import pytest

from tests.conftest import PARTNER_PACKAGES
from views_postprocessing.contract import source_metadata

_REPO = Path(__file__).resolve().parent.parent

#: The numpy 1.x/2.x ABI break recorded in views-models
#: `postprocessors/un_fao/requirements.txt` on 2026-08-13, found by the pre-delivery
#: rehearsal. It is a `ValueError`, not an `ImportError` — which is why the guard
#: catches `Exception`.
_ABI_BREAK = (
    "numpy.dtype size changed, may indicate binary incompatibility. "
    "Expected 96 from C header, got 88"
)


@pytest.fixture
def absent_client(monkeypatch):
    """Make `datafactory_query` unimportable REGARDLESS of what is installed.

    The first draft of this module relied on the package happening to be absent in the
    developer venv, which meant four of these tests would have failed in the launcher
    prefix — the environment they describe. That is the C-30/C-46 shape again: a guard
    whose proof rests on an ambient property nothing declares.
    """
    monkeypatch.setitem(sys.modules, "datafactory_query", None)
    monkeypatch.setitem(sys.modules, "datafactory_query.defaults", None)


@pytest.fixture
def exploding_client(monkeypatch):
    """`datafactory_query` is INSTALLED and raises on load — the real-world case."""

    class _Exploding:
        __name__ = "datafactory_query.defaults"

        def __getattr__(self, name):
            raise ValueError(_ABI_BREAK)

    module = types.ModuleType("datafactory_query")
    defaults = _Exploding()
    module.defaults = defaults
    monkeypatch.setitem(sys.modules, "datafactory_query", module)
    monkeypatch.setitem(sys.modules, "datafactory_query.defaults", defaults)


def test_an_absent_client_raises_rather_than_reporting_no_boundary(absent_client):
    with pytest.raises(source_metadata.ProducerClientUnavailable):
        source_metadata.last_valid_month_id()


def test_an_absent_client_is_told_to_install_the_package(absent_client):
    with pytest.raises(source_metadata.ProducerClientUnavailable) as excinfo:
        source_metadata.last_valid_month_id()
    message = str(excinfo.value)
    assert "not installed" in message
    assert "views-datafactory" in message, "the refusal must name the package to install"
    # The reader must be able to tell this apart from the degrade-open case.
    assert "observed" in message, (
        "the refusal must say what degrading open would have cost — unobserved months "
        "shipping as observed history — or it reads as a routine unavailability"
    )


def test_a_client_that_raises_on_load_is_NOT_reported_as_missing(exploding_client):
    """The failure this environment actually had: a ValueError, not an ImportError.

    An `except ImportError` clause would let this reach the caller's degrade-open and
    ship the unobserved tail — the precise case the guard exists to separate.
    """
    with pytest.raises(source_metadata.ProducerClientUnavailable) as excinfo:
        source_metadata.last_valid_month_id()
    message = str(excinfo.value)
    assert "present but raised while loading" in message
    assert "ValueError" in message and "numpy.dtype size changed" in message, (
        "the refusal must quote what actually went wrong; the operator cannot act on "
        "'could not be loaded' alone"
    )
    assert "Do NOT reinstall" in message, (
        "reporting an installed-but-broken package as missing sends the operator to a "
        "fix they have already applied"
    )


def test_the_refusal_chains_the_original_exception(absent_client):
    """``raise ... from exc``: the traceback must still say what actually failed."""
    with pytest.raises(source_metadata.ProducerClientUnavailable) as excinfo:
        source_metadata.last_valid_month_id()
    assert isinstance(excinfo.value.__cause__, ImportError)


def test_it_is_logged_as_well_as_raised(caplog, absent_client):
    """ADR-008: a refusal on the delivery path is logged persistently AND raised."""
    with caplog.at_level("ERROR"), pytest.raises(source_metadata.ProducerClientUnavailable):
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


@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_the_managers_do_not_swallow_the_refusal(partner):
    """The degrade-open must not re-absorb what this module just refused.

    Parametrized over ``PARTNER_PACKAGES`` rather than a literal pair: eight guards
    once hardcoded ``"unfao"`` and all eight went on passing over ``crafd/`` when it
    landed (see ``tests/conftest.py``). A ninth would have been this one.

    A source check rather than a behavioural one, deliberately: constructing a manager
    needs pipeline-core, a path manager and an Appwrite environment (C-40), and the
    property worth pinning is one line — that ``ProducerClientUnavailable`` is re-raised
    *before* the broad ``except``. Someone tidying the two branches back into one is
    precisely how C-103 would return, and it would return silently.
    """
    source = (_REPO / "views_postprocessing" / partner / "managers" / f"{partner}.py").read_text()

    # Scope to `_read_historical_frame`. Comparing offsets across the whole file would
    # let a narrow branch on some unrelated `try` satisfy the ordering while the
    # boundary read's branch was gone.
    start = source.index("def _read_historical_frame")
    body = source[start:source.index("\n    def ", start)]

    narrow = body.count("except source_metadata.ProducerClientUnavailable:")
    broad = body.count("except Exception:")
    assert narrow == 1, (
        f"{partner}'s _read_historical_frame has {narrow} ProducerClientUnavailable "
        "branches, expected 1. Without it a broken environment is indistinguishable "
        "from a producer that publishes no boundary, and the delivery ships fabricated "
        "months either way (C-103)."
    )
    assert broad == 1, (
        f"{partner}'s _read_historical_frame has {broad} broad `except Exception:` "
        "branches, expected 1 (the C-26 degrade-open). If it is gone the refusal may "
        "be fine, but this check no longer describes the code — read it and rewrite it."
    )
    assert body.index("except source_metadata.ProducerClientUnavailable:") < body.index(
        "except Exception:"
    ), (
        f"{partner} catches Exception before ProducerClientUnavailable, so the narrow "
        "branch is unreachable"
    )
