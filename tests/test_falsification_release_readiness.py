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


# ─────────────────────────────────────────────────────────────────────────────
# Third audit, 2026-08-26. Claim: *"nothing more to do here now; no pressing GH
# issues or registered risk; no repos upstream or downstream blocked by this repo."*
#
# Verdict: FALSIFIED. Both of its stubs are disposed of here rather than carried:
#
# **S5 DISCHARGED 2026-08-26.** It asserted that neither product names a precondition
# that has already been satisfied. Both did — `unfao` cited faoapi's C-161 closure
# notice (delivered 2026-07-20), `crafd` cited the views-crafdapi selection guard
# (views-crafdapi#53, closed 2026-08-12). Both docstrings now name the gate that
# actually holds, views-appwrite#171. Removed by hand rather than left to XPASS.
#
# **S6 WITHDRAWN 2026-08-26 — it was not a guard that could fire.** It asserted the
# "step 4 is incomplete" banner disappears from `docs/operations/correction_procedure.md`.
# That banner cannot come down until FAO answers Pre-Release Note 07 Decision B.1, which
# is not an action available in this repository at any effort. A test that can only go
# green on an external party's reply is decoration (C-102), and **#292 already tracks the
# item with more precision than an assertion can carry** — including the part the audit
# got wrong: the nine mislabelled cells (views-datafactory#387) **were** disclosed to FAO
# as Note 07 Topic G on 2026-08-21. The audit reported that disclosure as missing. It
# was not.
#
# Two further findings from that audit are facts about the issue tracker, not the tree,
# and are recorded in the sprint rather than as assertions: views-faoapi is blocked
# downstream (#294), and #272's second question is unanswered.
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
# Fourth audit, 2026-09-29. Claim: *"we are ready for a new full (40-lesson) run."*
#
# Verdict: FALSIFIED — two hard, two soft. Only ONE is assertable in this repo and
# it is below. The others are facts about other repositories' state, and a test
# here that reached for them would be a guard that cannot fire in CI (C-102):
#
#   HARD 1 — views-models still pins VIEWS_POSTPROCESSING_PIN="1.1.1", so a run
#            launched now installs the build whose guard checks 2 of 110 artefacts.
#            Lives on views-models#439. Not assertable here: views-models is not in
#            this repo's CI sibling checkout (ADR-016), so the assertion would pass
#            vacuously. This is C-112's whole subject.
#   HARD 2 — a fresh launcher environment is unbuildable (views-models#516, open):
#            xarray is unpinned in the launcher requirements and datafactory's
#            `>=2024.1,<2026` cap permits 2025.12.0, which needs pandas>=2.1 against
#            the platform's pandas 1.5.3. Not ours and not assertable here.
#   SOFT  4 — ADR-013 §4.6's capacity inequality is an open maintainer item and
#            40 lessons raises the assembled-run figure ~11%. Needs the run's S,
#            which this seat does not know. Recorded, not tested.
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.xfail(reason="S7: unaddressed falsification — see the audit report", strict=True)
def test_the_selection_check_does_not_depend_on_an_order_nothing_guarantees():
    """S7 (soft). The per-object half stopped depending on document order in #314.
    The SELECTION half still does, through a guarantee that does not exist.

    `verify`'s legs loop calls the port's `latest_file_id`, which is pipeline-core's
    `get_latest_file_id`. That function DOCUMENTS *"the file ID of the newest matching
    file based on creation timestamp"* and implements `files_list[0]` over the result of
    `search_files_by_metadata`, which appends only `Query.equal` per filter and never an
    `order_desc`/`order_asc` (`modules/appwrite/file.py:1045-1050`).

    So the check that decides whether the consumer's selection lands on THIS run takes
    an arbitrary element of every `category="forecast"` document ever written, and
    compares it against this run's manifest id. It has held since August, which means
    the order has been favourable rather than guaranteed — and the set it indexes into
    grows by ~110 documents per run, ~120 at 40 lessons.

    The failure is a **false** `DeliveryNotFindableError` on a healthy delivery, which
    is the direction this module exists to avoid.

    Fails until either the selection half is made order-independent here, or
    pipeline-core's sort lands and the pin moves. Filed upstream after the #312
    re-review; the fix is not ours and the dependency is.
    """
    source = (_REPO / "views_postprocessing" / "delivery" / "findability.py").read_text()
    legs_loop = source[source.index("for category, expected in legs.items():"):]
    assert "resolve_latest(" not in legs_loop.split("assert_all_findable")[0], (
        "the selection check still resolves through `latest_file_id`, i.e. through "
        "pipeline-core's unsorted `files_list[0]`"
    )
