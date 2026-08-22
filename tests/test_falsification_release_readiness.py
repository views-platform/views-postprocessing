"""Failing stubs from the release-readiness falsification audit, 2026-08-21.

**DO NOT COMMIT THIS FILE AS-IS.** These tests fail by design, and this repository's
`protect_main` ruleset makes the `test` job a **required check with zero bypass
actors** — so committing red tests to `main` blocks every subsequent merge, including
the fix. That interaction is itself finding S1 below.

Claim audited: *"we're ready to set up a PR, bump the version, and run the review
ritual"* — i.e. cutting 1.2.0 from current `main` would ship a correct, installable
package with every release guard satisfied and nothing in the repo's governance
blocking the path.

Verdict: CONTESTED. No hard falsification; two soft ones, below.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent


@pytest.mark.xfail(reason="S1: unaddressed falsification — see the audit report", strict=True)
def test_the_release_path_survives_its_own_expiry_tripwire():
    """S1 (soft). From 2026-10-18 no release can be cut, and nothing says so.

    Measured 2026-08-21 against the live ruleset: `protect_main` is active, the `test`
    job is a REQUIRED status check, and `bypass_actors` is **empty** — which is C-86's
    finding, still true. `tests/test_credential_expiry.py` starts failing 30 days before
    2026-11-17, i.e. **2026-10-18**. From that date the required check is red, so no PR
    merges to `main` and no release can be tagged.

    The escape is reachable — a PR that sets `ACKNOWLEDGED_UNTIL` is green on its own
    branch (verified: 1 failed -> 6 passed) — which is why this is soft rather than
    hard. What is missing is that **nothing tells a releaser this**. There is no release
    runbook, and C-84 does not mention that its tripwire gates the release path.

    Fix: document the interaction where a releaser will meet it — a release runbook
    under `docs/operations/`, or a line in C-84 and C-86 cross-referencing each other.
    """
    runbook = list((_REPO / "docs" / "operations").glob("*release*"))
    assert runbook, (
        "no release runbook exists, so the 2026-10-18 block on the release path is "
        "recorded nowhere a releaser would look (C-84 x C-86)"
    )
    text = "\n".join(p.read_text() for p in runbook)
    assert "ACKNOWLEDGED_UNTIL" in text, (
        "the release runbook does not name the only in-repo way past the expiry "
        "tripwire once it fires"
    )


@pytest.mark.xfail(reason="S2: unaddressed falsification — see the audit report", strict=True)
def test_a_release_announces_delivery_failure_modes_it_adds():
    """S2 (soft). 1.2.0 can fail a delivery that 1.1.1 completed, and nothing says so.

    The shipped delta since tag 1.1.1 adds three exception types that can escape into a
    launcher: `DeliveryNotFindableError` and `FindabilityUnverifiedError` (C-94) and
    `ProducerClientUnavailable` (C-103). The first is the sharp one — a delivery whose
    artifacts land somewhere the consumer cannot see previously **succeeded silently**
    and now raises.

    That is the intended behaviour and the whole point of C-94. It is still a change a
    consumer must be told about, and the only signal they get is a MINOR version bump.
    This repository has no CHANGELOG, so views-models' launchers would take 1.2.0 with
    no notice that a previously-passing run can now fail.

    Fix: a CHANGELOG naming the new failure modes, or release notes on the tag. Either
    satisfies this; the assertion below is deliberately loose about which.
    """
    candidates = [
        _REPO / "CHANGELOG.md",
        _REPO / "docs" / "CHANGELOG.md",
        _REPO / "docs" / "operations" / "release_notes.md",
    ]
    present = [p for p in candidates if p.exists()]
    assert present, (
        "no changelog or release-notes file exists, so a consumer's only signal that "
        "1.2.0 can fail a delivery 1.1.1 completed is the version number itself"
    )
    text = "\n".join(p.read_text() for p in present)
    for failure_mode in ("DeliveryNotFindableError", "ProducerClientUnavailable"):
        assert failure_mode in text, (
            f"{failure_mode} can escape into a launcher and is not announced anywhere"
        )
