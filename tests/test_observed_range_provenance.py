"""#297: the artifact must say what boundary it clipped against.

CRAF'd received July 2026 as history. The month was real but ~1% reported — six
cells of 64,742 — and the producer's *inferred* boundary (a month counts as
observed once its slice sums above zero) therefore declared it observed. The clip
kept it, correctly, by its own contract.

Establishing that took a day, because the delivered artifact could not answer the
one question a partner asks afterwards: *observed through when, and decided against
what?* The boundary was only recoverable at all because July's six cells happened to
land in ``ged_ns``/``ged_os`` rather than ``ged_sb``, leaving a non-zero trace. Had
they landed in ``ged_sb``, the data would have been mute.

So the boundary is stamped, and stamped **unconditionally**. The degrade-open case —
boundary unreadable, clip skipped, unobserved months may be present — is the case that
most needs recording, and it is exactly the case an "omit when absent" field would drop.

Two layers, as the repo tests every other delivery invariant: the rule on primitives,
and the wiring as declaration checks (constructing a manager needs pipeline-core, a
views-models path manager and a live Appwrite environment — C-40).
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from tests.conftest import PARTNER_PACKAGES
from views_postprocessing.delivery.provenance import (
    DESCRIPTION_MAX,
    UNREAD,
    build_provenance,
    compact_description,
)

_REPO = Path(__file__).resolve().parent.parent


def _prov(**over):
    base = dict(
        lookup_version="gaul-2024a",
        region="land_gaul",
        expected_cell_count=64742,
        actual_cell_count=64742,
        unmapped_count=0,
        observed_through=559,
    )
    base.update(over)
    return build_provenance(**base)


# ── the rule ───────────────────────────────────────────────────────────────


def test_the_boundary_the_clip_used_is_stamped():
    assert _prov(observed_through=559)["observed_through"] == 559


def test_a_skipped_clip_is_stamped_as_null_rather_than_omitted():
    """The #297 property. An absent key is indistinguishable from an artifact
    built before this field existed; an explicit null says "the boundary could
    not be read, so this delivery was NOT clipped"."""
    prov = _prov(observed_through=None)
    assert "observed_through" in prov
    assert prov["observed_through"] is None
    assert json.loads(compact_description(prov))["observed_through"] is None


def test_building_provenance_without_reading_the_boundary_refuses():
    """UNREAD is a call-order bug, not a delivery condition. It must not
    silently become null — that would report "clip skipped" for a run whose
    clip in fact ran."""
    with pytest.raises(ValueError, match="never read"):
        _prov(observed_through=UNREAD)


def test_unread_is_distinct_from_none():
    assert UNREAD is not None
    assert not isinstance(None, type(UNREAD))


def test_the_boundary_survives_the_compaction_fallback():
    """``compact_description`` drops non-essential keys when the 255-char carrier
    overflows. A boundary that vanishes precisely when the description is long is
    a guard that disappears when it is needed, so it belongs in the essential set."""
    # The padding must overflow the full dict while leaving the essential set inside
    # the limit. Measured 2026-08-25: the fallback triggers from 104 chars and the
    # essential set still fits to ~117. Both assertions below fail loudly if that
    # window ever moves, so the constant cannot drift silently into a vacuous test.
    prov = _prov(lookup_version="g" * 110, fill_count=3)
    text = compact_description(prov)
    assert len(text) <= DESCRIPTION_MAX
    round_trip = json.loads(text)
    assert "fill_count" not in round_trip, "the fallback did not trigger; test is vacuous"
    assert round_trip["observed_through"] == 559


# ── the wiring ─────────────────────────────────────────────────────────────


def _manager_source(partner: str) -> str:
    return (_REPO / "views_postprocessing" / partner / "managers" / f"{partner}.py").read_text()


def _func(source: str, name: str) -> ast.FunctionDef:
    return next(
        n for n in ast.walk(ast.parse(source))
        if isinstance(n, ast.FunctionDef) and n.name == name
    )


@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_the_manager_initialises_the_boundary_as_unread(partner):
    init = _func(_manager_source(partner), "__init__")
    assigns = [
        n for n in ast.walk(init)
        if isinstance(n, ast.Assign)
        and any(
            isinstance(t, ast.Attribute) and t.attr == "_observed_through"
            for t in n.targets
        )
    ]
    assert assigns, f"{partner}: __init__ does not initialise _observed_through"
    src = ast.unparse(assigns[0].value)
    assert "UNREAD" in src, (
        f"{partner}: _observed_through initialises to {src!r}, not UNREAD. "
        "Initialising to None makes 'never read' indistinguishable from 'read and "
        "unavailable' — the exact conflation #297 exists to prevent."
    )


@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_the_boundary_is_recorded_before_the_degrade_open_return(partner):
    """The assignment must precede the ``if lv is None: return`` early exit.

    Placed after it, the degrade-open path — the one that most needs recording —
    would leave the attribute UNREAD and the delivery would raise at provenance
    time instead of reporting that it did not clip.
    """
    read = _func(_manager_source(partner), "_read_historical_frame")
    assigns = [
        n for n in ast.walk(read)
        if isinstance(n, ast.Assign)
        and any(
            isinstance(t, ast.Attribute) and t.attr == "_observed_through"
            for t in n.targets
        )
    ]
    assert assigns, f"{partner}: _read_historical_frame never records the boundary"

    returns = [n for n in ast.walk(read) if isinstance(n, ast.Return)]
    assert returns, f"{partner}: expected an early return in _read_historical_frame"
    first_return = min(n.lineno for n in returns)
    assert min(a.lineno for a in assigns) < first_return, (
        f"{partner}: _observed_through is assigned at or after the early return, so "
        "the degrade-open path would never record that the clip was skipped."
    )


@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_the_manager_passes_the_boundary_into_provenance(partner):
    desc = _func(_manager_source(partner), "_historical_frame_description")
    kwargs = {
        kw.arg
        for c in ast.walk(desc)
        if isinstance(c, ast.Call)
        for kw in c.keywords
        if kw.arg
    }
    assert "observed_through" in kwargs, (
        f"{partner}: _historical_frame_description builds provenance without the "
        "boundary. build_provenance requires it, so this would raise at delivery."
    )


def test_both_partners_carry_it_identically():
    """#297 was filed as a CRAF'd defect; the two managers are deliberate clones
    and the UN-FAO side has an external partner. A fix in one only is half a fix."""
    counts = {
        p: _manager_source(p).count("_observed_through") for p in PARTNER_PACKAGES
    }
    assert len(set(counts.values())) == 1, (
        f"the partners diverge on the boundary stamp: {counts}"
    )
    assert all(v >= 3 for v in counts.values()), counts
