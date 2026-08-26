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


# ─────────────────────────────────────────────────────────────────────────────
# Second audit, 2026-08-25. Claim: *"we are ready to bump the version, set up a
# PR to main, review, merge when review is good, then tag and publish."*
#
# Verdict: FALSIFIED — one hard, two soft.
#
# **H1 DISCHARGED 2026-08-26** (release 1.2.0). Its probe asserted that a release
# names what changed about failing for a consumer. `CHANGELOG.md` now exists and
# 1.2.0's entry names the three escaping exception types and the new provenance
# field, so the probe would XPASS and `strict=True` would turn that into a failure.
# Removed by hand rather than left to flip, per the S4 precedent (#200). Register
# C-111 is closed by the same change.
#
# **S2 DISCHARGED 2026-08-26** by the same change — and it is the same finding.
# S2 (2026-08-21) and H1 (2026-08-25) are one concern found twice by two audits,
# which is itself worth recording: the second audit did not read the first's stubs
# before designing probes. Both are C-111; both are closed by CHANGELOG.md.
#
# S1, S3 and S4 remain open and are below. The bump SIZE (minor,
# not patch) is recorded as an observation, not a falsification: nothing in the
# repo is wrong about it, it is a way the releaser could be.
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.xfail(reason="S3: unaddressed falsification — see the audit report", strict=True)
def test_tagging_actually_publishes():
    """S3 (soft). "Tag and publish" is not the mechanism this repo has.

    `.github/workflows/publish_package.yml` triggers on `release: published` and
    `workflow_dispatch` — **not** on tag push. Pushing a tag runs nothing.

    The evidence that this is a live trap rather than a technicality: tags `1.0.0`
    and `1.1.0` both exist and **neither has a GitHub Release**. Only `1.1.1` does,
    which is the only version this workflow has ever published.

    Fails until the workflow triggers on tag push, or until a release runbook states
    that cutting a GitHub Release — not tagging — is the publishing step.
    """
    wf = (_REPO / ".github/workflows/publish_package.yml").read_text()
    assert "tags:" in wf or "push:" in wf, (
        "publish triggers only on `release: published`; a plan that says 'tag, then "
        "publish' will tag and stop, and nothing will say so"
    )


@pytest.mark.xfail(reason="S4: unaddressed falsification — see the audit report", strict=True)
def test_the_publish_job_cannot_ship_untested_code():
    """S4 (soft). The publish job runs no tests and declares no dependency.

    `publish_package.yml` has no `needs:`, no pytest step, and one gate: that the
    version in `pyproject.toml` parses higher than the newest on PyPI. So a GitHub
    Release cut from any commit — a branch, a stale `main`, a commit whose `test`
    job failed — builds and uploads to PyPI unconditionally.

    Nothing has gone wrong yet because releases have been cut from a green `main`
    by hand. The guard is the habit, not the workflow, and habits are what C-86
    already showed this repo cannot rely on when one person holds them.

    Fails until the publish job depends on a passing test run, or refuses a ref
    whose checks are not green.
    """
    wf = (_REPO / ".github/workflows/publish_package.yml").read_text()
    assert "needs:" in wf or "pytest" in wf, (
        "publish validates only version-greater-than-PyPI; nothing establishes that "
        "the code being shipped passes its own suite"
    )
