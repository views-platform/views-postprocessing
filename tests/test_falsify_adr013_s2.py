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


def test_e3_does_not_still_say_the_fix_is_unreleased():
    """E3's expiry has fired and been discharged. This stops it coming back.

    The predecessor of this check was a tripwire: E3 claimed pipeline-core's
    editable-install fix was "not yet in any released version", which is a dated claim
    about someone else's release history, and it would go stale the moment pipeline-core
    published again. It did — **3.0.1, 2026-08-11 13:40 UTC** — and on 2026-08-13 the
    tripwire fired in CI and E3 was corrected. Verified at the tag: 3.0.0 returns
    ``version("views_pipeline_core")`` with no editable detection, 3.0.1 reads
    ``direct_url.json`` and returns ``"unknown"`` when ``dir_info.editable`` is set.

    What replaces it is deliberately smaller, because the thing it guarded is now stable.
    "In force for producers running 3.0.1 or later" is not a claim any future release can
    falsify, so there is no expiry left to watch and re-pointing the tripwire at 3.0.1
    would be inventing one. The only remaining failure is textual: a revert or a bad merge
    restoring the sentence that is now false.

    One thing the tripwire got wrong is worth keeping in view. It observed *our* installed
    distribution, so it could not see 3.0.1 until this repository's lockfile moved to it —
    it reported the release two days late. A guard on another repo's release history that
    watches our own pin is measuring the wrong thing; it caught this because the two
    happened to coincide.
    """
    # E3's own bullet, not the whole Post-adoption record: "Erratum E3" is also mentioned
    # in §5 and "Erratum E2" appears in the header above both, so splitting on the bare
    # names spans ~600 lines and would let either assertion be satisfied by unrelated text.
    entries = re.split(r"^- \*\*(?=\d{4}-)", _ADR.read_text(), flags=re.M)
    e3 = next((e for e in entries if e.startswith("2026-08-10 — Erratum E3")), None)
    assert e3 is not None, "Erratum E3's entry is no longer in the Post-adoption record"
    assert "not yet in any released version" not in e3, (
        "Erratum E3 has regained the wording that was false from 2026-08-11, when "
        "views-pipeline-core 3.0.1 shipped the editable-install fix. E3 was corrected on "
        "2026-08-13 to record that release; something has restored the superseded text."
    )
    assert "3.0.1" in e3, (
        "Erratum E3 no longer names the release that discharged it. The lift's second "
        "half is in force for producers running views-pipeline-core 3.0.1 or later, and "
        "E3 is where a consumer looks that up."
    )
