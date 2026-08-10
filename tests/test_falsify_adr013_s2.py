"""Guards born from the falsification audit of "ADR-013 §2 is sufficient and
unambiguous" (audit 2026-07-19, FALSIFIED — 2 hard, 3 soft; all fixed same day).

Each test now enforces one fixed gap in §2 permanently.

"""

import re
from pathlib import Path

import pytest


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


def test_s2_2a_is_not_secretly_in_force():
    """§2.2a defines a field that does NOT ship. Guard the "does not" (ADR-014 §1).

    Amendment A2 admits `provenance.status` and says plainly that it is not adopted and
    `contract_version` stays 1.5. That is a claim about the code, written in a document,
    and this repository has been caught three times this epic by prose describing work it
    had not done — here the risk runs the other way, which is worse: someone implements
    A2, ships 1.6, and leaves §2.2a still saying it is not in force. A reader planning
    the three-repo re-vendor would then believe it was still owed.

    So the guard is bidirectional. Either §2.2a says A2 is unadopted and the code agrees,
    or the section was rewritten on adoption and this test must be rewritten with it.
    """
    from views_postprocessing.contract.wire.header import _PROVENANCE_KEYS, CONTRACT_VERSION

    s2 = _s2()
    if "NOT YET IN FORCE" not in s2:
        pytest.skip(
            "§2.2a no longer declares itself unadopted — A2 was presumably adopted. "
            "Rewrite this test against whatever the section now claims; do not delete it."
        )

    assert CONTRACT_VERSION == "1.5", (
        f"§2.2a says `contract_version` remains 1.5; the header declares "
        f"{CONTRACT_VERSION}. If A2 (or anything else) was adopted, the ADR is now "
        "describing a contract that is not the one shipping."
    )
    assert "status" not in _PROVENANCE_KEYS, (
        "§2.2a says A2 is not in force, but `status` is in the closed provenance keyset. "
        "The field shipped and the amendment was never marked adopted — which leaves the "
        "§10 golden fixture, three repos' vendored copies, and this document disagreeing."
    )


def test_e3s_claim_about_unreleased_behaviour_is_still_true():
    """Erratum E3 says a pipeline-core fix is in no released version. That expires.

    E3 lifts §2.2's `pipeline_core_version` caveat in two halves. The second — that an
    editable install reports ``"unknown"`` rather than a stale number — landed in
    pipeline-core on 2026-08-04, a day and a half *after* 3.0.0 was uploaded to PyPI. So
    the erratum states plainly that **no released version contains it**, and that it
    becomes true of producers at the next release.

    That is a dated claim about someone else's release history, in the document that
    punishes those hardest. It stops being true the moment pipeline-core publishes again,
    and nothing about this repository would change to signal it.

    So: if the pipeline-core we are running is a **released distribution** (not an
    editable checkout) and its version is past 3.0.0, the next release has happened and
    E3's wording is stale. CI installs from PyPI, so this is live there even though a
    maintainer's editable environment leaves it inert — which is stated rather than
    discovered, because a guard that only ever runs in one place is half a guard.
    """
    pytest.importorskip("views_pipeline_core", reason="a declared dependency")
    from importlib.metadata import PackageNotFoundError, version as dist_version

    import views_pipeline_core

    source = Path(views_pipeline_core.__file__).resolve()
    if "site-packages" not in str(source):
        pytest.skip(
            "pipeline-core is an editable checkout here, so its recorded version says "
            "nothing about what has been released. This check is live in CI, which "
            "installs from PyPI."
        )
    try:
        installed = dist_version("views-pipeline-core")
    except PackageNotFoundError:  # pragma: no cover - not a distribution at all
        pytest.skip("pipeline-core is not installed as a distribution")

    parts = tuple(int(p) for p in installed.split(".")[:3] if p.isdigit())
    assert parts <= (3, 0, 0), (
        f"pipeline-core {installed} is released and past 3.0.0, so Erratum E3's claim "
        "that the editable-install fix is 'not yet in any released version' is out of "
        "date. Re-read E3 against that release: the second half of the lift is probably "
        "now in force, and the sentence saying it is not must go."
    )
