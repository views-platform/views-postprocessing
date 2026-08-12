"""The workflow and the sibling declaration must agree — ADR-016.

**The failure this exists to prevent has already happened.** A comment in
`run_pytest.yml` stated that `views-appwrite` was private. It went public on 2026-08-08
and the comment did not, so seven cross-repository checks stayed dark in CI for no reason
at all — and the document written to justify a credential for them was drafted the next
day, against a fact that had already changed.

The fix is not a better comment. It is that **which siblings CI checks out is declared
once**, in `tests/conftest.py::SIBLINGS`, and this file fails when the workflow and that
declaration disagree — in either direction.

**Whether a sibling is public is not modelled here, and that is deliberate.** An earlier
version carried a `public` flag and a rule pairing it with the presence of a checkout
token. A review found the pair circular — the field was read by exactly one rule, and
that rule existed to protect the field's verifiability — so both were removed on
2026-08-10 without any change in behaviour. Visibility now lives in a sibling's `note`,
as prose, because nothing here could verify it in any case: no test in this suite touches
the network.

What still holds without the flag: a checkout of a repository CI cannot read simply fails
the build, because the default `GITHUB_TOKEN` is scoped to this repository. Rule G5 keeps
that failure loud.

**Why the rules run G1, G2, G4, G5, G6, G7 with two numbers missing.** G3 paired a
sibling's visibility against whether its checkout used a credential; G8 checked that a
recorded date was plausible. Both were deleted on 2026-08-10 after a review found them
circular — each existed to protect a field that existed to feed it. The survivors keep
their original names rather than being renumbered, so anything written about "G6"
elsewhere still means this G6. The gap is deliberate; nothing is missing.

**Two sections of this file have inverted failure semantics, and that trips people.**
Everything above `── the rules, against the real workflow ──` fails when *the workflow or
the declaration* is wrong. Everything below `── the rules, against synthetic mutants ──`
fails when **the rule itself** is wrong — those tests feed a deliberately broken world to
a rule and demand it complain. If one of those fails, do not go looking at
`run_pytest.yml`; the workflow is fine and the guard has stopped guarding.

**Every rule is a pure function of (workflow, siblings)**, so each can be run against a
synthetic mutant rather than only against the real file. A guard that can only be
demonstrated by editing CI is a guard nobody ever watches fail (ADR-014 §2) — this repo
already answers that three times over (`test_the_drift_check_would_catch_a_rename`,
`test_the_guard_would_actually_catch_a_violation`, `test_the_ban_actually_fires_on_a_living_doc`).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tests.conftest import SIBLINGS, Sibling

_WORKFLOWS = Path(__file__).resolve().parent.parent / ".github" / "workflows"
_TEST_WORKFLOW = _WORKFLOWS / "run_pytest.yml"

#: Where a sibling checkout must land. Not tidiness: `pyproject.toml` excludes
#: `_siblings` from ruff, and the Lint step reported 745 findings in views-crafdapi's own
#: test suite the first time a sibling was checked out anywhere else.
_SIBLING_PATH_PREFIX = "_siblings/"

#: The org every sibling belongs to. A `repository:` outside it is not a sibling.
_ORG = "views-platform/"


# ── parsing ──────────────────────────────────────────────────────────────────


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text()) or {}


def _steps(workflow: dict) -> list[dict]:
    """Every step of every job, flattened."""
    return [
        step
        for job in (workflow.get("jobs") or {}).values()
        for step in (job.get("steps") or [])
        if isinstance(step, dict)
    ]


def _sibling_steps(workflow: dict) -> list[dict]:
    """Checkout steps that fetch ANOTHER repository.

    Keyed on the presence of ``repository:``, not on ``uses: actions/checkout``. This
    repo's own checkout is an `actions/checkout` step with no ``repository:``, so a rule
    scoped to the action would fire on line one and be deleted the same day (ADR-014 §3).
    """
    return [
        step
        for step in _steps(workflow)
        if str(step.get("uses", "")).startswith("actions/checkout")
        and isinstance(step.get("with"), dict)
        and step["with"].get("repository")
    ]


def _repo_name(step: dict) -> str:
    """``views-platform/views-appwrite`` -> ``views-appwrite``."""
    return str(step["with"]["repository"]).removeprefix(_ORG)


def _pytest_step(workflow: dict) -> dict | None:
    """The step that actually runs the suite — where the env vars must land.

    Found by what it runs, not by its name. An `env:` block on the Lint step satisfies a
    naive "the variable is set somewhere" check while the tests see nothing.
    """
    for step in _steps(workflow):
        if "pytest" in str(step.get("run", "")):
            return step
    return None


# ── rules: pure functions, each returning the violations it found ────────────


def _g1_declared_checkouts_are_present_and_pointed_at(
    workflow: dict, siblings: dict[str, Sibling]
) -> list[str]:
    """Every ``ci_checkout=True`` sibling is checked out AND its env var points at it."""
    by_name = {_repo_name(s): s for s in _sibling_steps(workflow)}
    pytest_step = _pytest_step(workflow)
    env = (pytest_step or {}).get("env") or {}

    problems = []
    for name, sibling in siblings.items():
        if not sibling.ci_checkout:
            continue
        step = by_name.get(name)
        if step is None:
            problems.append(f"{name}: declared ci_checkout=True but no checkout step")
            continue
        expected = "${{ github.workspace }}/" + str(step["with"].get("path", ""))
        actual = env.get(sibling.env)
        if actual is None:
            problems.append(
                f"{name}: checked out, but {sibling.env} is not set on the step that "
                "runs pytest — the tests would look in the conventional location, find "
                "nothing, and skip"
            )
        elif str(actual).strip() != expected:
            problems.append(
                f"{name}: {sibling.env}={actual!r} does not match the checkout path "
                f"({expected!r})"
            )
    return problems


def _g2_every_checkout_is_declared(
    workflow: dict, siblings: dict[str, Sibling]
) -> list[str]:
    """No sibling is fetched in CI without being declared with ``ci_checkout=True``."""
    problems = []
    for step in _sibling_steps(workflow):
        name = _repo_name(step)
        sibling = siblings.get(name)
        if sibling is None:
            problems.append(
                f"{name}: checked out in CI but absent from SIBLINGS. A sibling nobody "
                "declared is one no rule below covers."
            )
        elif not sibling.ci_checkout:
            problems.append(
                f"{name}: checked out in CI but declared ci_checkout=False. One of the "
                "two is wrong, and the declaration is what the reader believes."
            )
    return problems


def _g4_every_note_names_a_record(
    workflow: dict, siblings: dict[str, Sibling]
) -> list[str]:
    """A sibling NOT checked out must say why, and **every** note must name a record.

    A deferral needs a trigger and an owner (ADR-014 §4). Requiring the note to cite a
    `C-nn` or an `ADR-nnn` is what makes the citation non-optional, so declared
    non-coverage stays attached to something a reader can follow.

    **Widened 2026-08-10 after external review.** The rule used to look only at siblings
    with ``ci_checkout=False``, which left a hole in exactly the place ADR-016 calls out:
    `views-crafdapi` was fetched *temporarily*, until the check it served moved to a
    registry read, and that fact lived in a note **no rule examined**. (That fetch is gone
    as of #248; the rule this incident produced is not.) A claim about
    another repository, in prose, that nothing can check — which is the failure ADR-016
    §3 diagnoses, reintroduced for the one download the document itself calls temporary.

    So the note requirement now follows the *note*, not the flag: whenever a sibling
    carries one, it must cite the record that owns it, whether it explains an exclusion
    or a temporary inclusion. Siblings with no note and `ci_checkout=True` are unaffected
    — a permanent, unremarkable fetch needs no justification.
    """
    problems = []
    for name, sibling in siblings.items():
        if not sibling.ci_checkout and not sibling.note.strip():
            problems.append(
                f"{name}: not checked out in CI and no note says why. Silent "
                "non-coverage reads as 'nothing to see here'."
            )
            continue
        if sibling.note.strip() and not any(
            token in sibling.note for token in ("C-", "ADR-", "#")
        ):
            problems.append(
                f"{name}: its note explains something but names no record. Cite the "
                "entry, ADR or issue that owns it — a note nothing points at is the "
                "prose this file exists to replace."
            )
    return problems


def _g5_no_step_swallows_its_own_failure(
    workflow: dict, siblings: dict[str, Sibling]
) -> list[str]:
    """No sibling checkout may carry ``continue-on-error``.

    One key and a failed fetch stops failing the build: the checks that sibling enables
    go back to skipping, silently, on a green run. That is the state this whole file
    exists to leave behind, and it is exactly the key someone reaches for while debugging
    a red CI.
    """
    return [
        f"{_repo_name(step)}: sibling checkout carries continue-on-error, so a failed "
        "fetch would not fail the build — and the checks it enables would skip silently"
        for step in _sibling_steps(workflow)
        if step.get("continue-on-error")
    ]


def _g6_siblings_land_under_the_excluded_path(
    workflow: dict, siblings: dict[str, Sibling]
) -> list[str]:
    """Sibling checkouts go under ``_siblings/`` — a real coupling to the ruff config."""
    return [
        f"{_repo_name(step)}: checked out to {step['with'].get('path')!r}, outside "
        f"{_SIBLING_PATH_PREFIX!r}. pyproject.toml excludes only that prefix from ruff, "
        "so the Lint step would start reporting another repository's code (it once "
        "reported 745 findings that way)."
        for step in _sibling_steps(workflow)
        if not str(step["with"].get("path", "")).startswith(_SIBLING_PATH_PREFIX)
    ]


def _g7_siblings_are_taken_from_main(
    workflow: dict, siblings: dict[str, Sibling]
) -> list[str]:
    """Every sibling checkout declares ``ref: main``.

    Without it `actions/checkout` takes the sibling's own default branch — which for
    views-appwrite is `development`. ADR-014 §3 makes `main` the authority for a claim
    about another repository, and `test_the_pinned_commit_is_reachable_from_the_contract_repos_main`
    already enforces that. Reading the working tree from `development` while demanding
    reachability from `main` is two guards in one file asking for different things.
    """
    return [
        f"{_repo_name(step)}: checkout does not declare `ref: main`, so it takes that "
        "repository's default branch — someone else's setting, and not the branch this "
        "repo treats as authoritative."
        for step in _sibling_steps(workflow)
        if str(step["with"].get("ref", "")) != "main"
    ]


_RULES = {
    "G1 declared checkouts are present and pointed at": _g1_declared_checkouts_are_present_and_pointed_at,
    "G2 every checkout is declared": _g2_every_checkout_is_declared,
    "G4 every note names a record": _g4_every_note_names_a_record,
    "G5 no step swallows its own failure": _g5_no_step_swallows_its_own_failure,
    "G6 siblings land under the excluded path": _g6_siblings_land_under_the_excluded_path,
    "G7 siblings are taken from main": _g7_siblings_are_taken_from_main,
}


# ── the inputs are real (ADR-014 §2) ─────────────────────────────────────────


def test_the_workflow_this_file_scans_actually_parses():
    """A YAML restructure would empty every scan below and report success.

    This is by far the most likely way this file becomes decoration: rename the job, nest
    `steps` differently, move the workflow, and every rule below finds nothing to complain
    about. So assert there is something to scan before trusting that there was nothing
    wrong.
    """
    assert _TEST_WORKFLOW.exists(), f"no workflow at {_TEST_WORKFLOW}"
    workflow = _load(_TEST_WORKFLOW)
    assert _steps(workflow), (
        "no steps parsed out of run_pytest.yml — the job or step structure moved, and "
        "every rule in this file is now scanning an empty list."
    )
    assert _pytest_step(workflow) is not None, (
        "no step in run_pytest.yml runs pytest. G1 checks the env vars on that step; "
        "without it, it checks nothing."
    )
    found = {_repo_name(s) for s in _sibling_steps(workflow)}
    assert found, (
        "no sibling checkout steps found. Either they were all removed — in which case "
        "the cross-repo checks are dark again — or the detection predicate no longer "
        "matches how they are written."
    )


def test_every_workflow_file_is_scanned_for_smuggled_siblings():
    """G2 must see ALL workflows, not just this one.

    A sibling checkout added to `codeql.yml` would be invisible to a rule scoped to
    `run_pytest.yml`. Nothing forbids one being added there; this makes it visible.
    """
    workflows = sorted(_WORKFLOWS.glob("*.yml"))
    assert workflows, (
        f"no workflow files under {_WORKFLOWS} — a glob over a moved directory finds "
        "nothing and reports success (register C-74)."
    )
    stray = []
    for path in workflows:
        stray += [
            f"{path.name}: {_repo_name(step)}"
            for step in _sibling_steps(_load(path))
            if _repo_name(step) not in SIBLINGS
        ]
    assert not stray, (
        f"sibling checkouts in workflow files that SIBLINGS does not declare: {stray}."
    )


def test_the_declared_siblings_are_the_ones_the_suite_resolves():
    """`SIBLINGS` is what every gated check resolves through; assert it is not empty."""
    assert SIBLINGS, "SIBLINGS is empty — every cross-repo check now skips permanently."
    assert all(s.env.startswith("VIEWS_") for s in SIBLINGS.values()), (
        "a declared override variable does not follow the VIEWS_* convention; "
        f"{ {n: s.env for n, s in SIBLINGS.items()} }"
    )


# ── the rules, against the real workflow ─────────────────────────────────────


@pytest.mark.parametrize("label", sorted(_RULES))
def test_the_workflow_agrees_with_the_declaration(label):
    """Each rule, run against the file that actually ships."""
    violations = _RULES[label](_load(_TEST_WORKFLOW), SIBLINGS)
    assert not violations, f"[{label}]\n  " + "\n  ".join(violations)


# ── the rules, against synthetic mutants (ADR-014 §2) ────────────────────────
#
# A rule that has only ever been run against a correct file has never been watched fail.
# Each case below is a minimal broken world; the rule must object AND name the sibling,
# because a violation nobody can locate is barely better than none.


def _workflow(**step_overrides) -> dict:
    """A minimal well-formed workflow with one sibling checkout, then mutated."""
    with_block = {
        "repository": "views-platform/views-appwrite",
        "ref": "main",
        "path": "_siblings/views-appwrite",
    }
    with_block.update(step_overrides.pop("with", {}))
    step = {"uses": "actions/checkout@v3", "with": with_block}
    step.update(step_overrides)
    return {
        "jobs": {
            "test": {
                "steps": [
                    {"uses": "actions/checkout@v3"},  # this repo's own — no `repository:`
                    step,
                    {
                        "run": "poetry run pytest tests/",
                        "env": {
                            "VIEWS_APPWRITE": "${{ github.workspace }}/_siblings/views-appwrite"
                        },
                    },
                ]
            }
        }
    }


_ONE = {"views-appwrite": SIBLINGS["views-appwrite"]}


def _replace(name: str, **changes) -> dict[str, Sibling]:
    from dataclasses import replace

    return {name: replace(SIBLINGS[name], **changes)}


#: ``(rule, broken workflow, broken declaration, the sibling the message must name, why)``
#:
#: **The offender is declared, not inferred.** It was briefly derived from the mutant's
#: own sibling map — which reads as principled and is wrong for `G2`, whose whole premise
#: is an EMPTY declaration: there is nothing in the map to derive from, so it fell back to
#: a hardcoded ``"views-appwrite"`` while the assertion message claimed it had not. For G2
#: the offender is a name in the *workflow*, and no amount of looking at the declaration
#: will find it. Writing it out is this repository's own rule (ADR-003): declare the fact,
#: do not let a helper guess it.
_MUTANTS = [
    ("G1 declared checkouts are present and pointed at",
     {"jobs": {"test": {"steps": [{"run": "poetry run pytest tests/", "env": {}}]}}},
     _ONE, "views-appwrite", "declared ci_checkout=True but the checkout step is gone"),
    ("G2 every checkout is declared",
     _workflow(), {}, "views-appwrite", "checked out but undeclared"),
    ("G4 every note names a record",
     _workflow(), _replace("views-appwrite", ci_checkout=False, note=""),
     "views-appwrite", "not checked out and no note"),
    ("G4 every note names a record",
     _workflow(), _replace("views-appwrite", ci_checkout=False, note="because reasons"),
     "views-appwrite", "note explains but names no record"),
    ("G5 no step swallows its own failure",
     _workflow(**{"continue-on-error": True}), _ONE,
     "views-appwrite", "a failed fetch would not fail the build"),
    ("G6 siblings land under the excluded path",
     _workflow(**{"with": {"path": "vendor/views-appwrite"}}), _ONE,
     "views-appwrite", "outside _siblings/, so ruff would lint it"),
    ("G7 siblings are taken from main",
     _workflow(**{"with": {"ref": "development"}}), _ONE,
     "views-appwrite", "takes a branch that is not the authority"),
]


def test_every_rule_has_a_mutant_that_proves_it_bites():
    """ADR-014 §2, applied to this file's own contents.

    Adding a rule to `_RULES` without a broken world to try it against is adding a rule
    nobody has watched fail. That is the definition of decoration, and it is easy to do
    by accident — the rule reads fine, the real workflow satisfies it, and the suite goes
    green forever.

    This is a cheap structural check, not a clever one: it cannot tell whether a mutant
    is a *good* one. It only refuses the case where there is none at all.
    """
    proven = {label for label, *_ in _MUTANTS}
    unproven = sorted(set(_RULES) - proven)
    assert not unproven, (
        f"rules with no mutant in _MUTANTS: {unproven}. Add a broken world that each one "
        "must object to, or the rule is untested against anything but a correct file."
    )


@pytest.mark.parametrize("label, workflow, siblings, offender, why", _MUTANTS)
def test_each_rule_bites_on_a_broken_world(label, workflow, siblings, offender, why):
    """Feed a rule a deliberately broken world and demand that it complains.

    **A failure here means the RULE is broken, not the workflow.** That inversion is the
    one thing about this file worth knowing before you debug it: `run_pytest.yml` is not
    involved, the world being fed in is a synthetic dict defined below, and a green real
    workflow is entirely consistent with this failing. A guard that no longer objects to
    a violation is a guard that has silently stopped working, which is the failure this
    whole file exists to make loud (ADR-014 §2).

    The second assertion is not pedantry: a rule that objects without naming which
    sibling is at fault leaves a maintainer grepping a workflow file by hand.
    """
    violations = _RULES[label](workflow, siblings)
    assert violations, (
        f"[{label}] did not object to a world that is deliberately broken: {why}. "
        "This means the RULE has stopped working — the real workflow is not involved "
        "and is probably fine. Fix the rule, not run_pytest.yml."
    )
    assert any(offender in v for v in violations), (
        f"[{label}] objected, but its message does not name the offending sibling "
        f"({offender!r}): {violations}. A maintainer reading only the failure would not "
        "know which repository to look at.\n\n"
        "Each mutant declares the name its rule must produce, in _MUTANTS. If you have "
        "changed which sibling a mutant breaks, change its declared offender in the same "
        "edit — under this file's inverted semantics, a stale one fails a rule that works."
    )


@pytest.mark.parametrize(
    "env, why",
    [
        ({}, "the env var is not set at all"),
        ({"VIEWS_APPWRITE": ""}, "set to empty — the CI misconfiguration that skips silently"),
        ({"VIEWS_APPWRITE": "${{ github.workspace }}/_siblings/appwrite"}, "points at the wrong path"),
    ],
)
def test_g1_bites_on_every_way_the_env_var_can_be_wrong(env, why):
    """The three shapes of "checked out, but the tests cannot see it"."""
    workflow = _workflow()
    workflow["jobs"]["test"]["steps"][2]["env"] = env
    violations = _g1_declared_checkouts_are_present_and_pointed_at(workflow, _ONE)
    assert violations, f"G1 did not object to: {why}"


def test_g1_looks_at_the_step_that_runs_pytest_and_not_merely_any_step():
    """Env on the Lint step satisfies "the variable is set somewhere" and nothing else."""
    workflow = _workflow()
    workflow["jobs"]["test"]["steps"][2]["env"] = {}
    workflow["jobs"]["test"]["steps"].insert(
        2, {"run": "poetry run ruff check .",
            "env": {"VIEWS_APPWRITE": "${{ github.workspace }}/_siblings/views-appwrite"}}
    )
    assert _g1_declared_checkouts_are_present_and_pointed_at(workflow, _ONE), (
        "G1 accepted an env var set on the Lint step — the tests would never see it"
    )


def test_the_repos_own_checkout_is_not_mistaken_for_a_sibling():
    """G2 must not fire on line one of every workflow ever written (ADR-014 §3)."""
    own_checkout_only = {"jobs": {"test": {"steps": [{"uses": "actions/checkout@v3"}]}}}
    assert not _g2_every_checkout_is_declared(own_checkout_only, SIBLINGS)
    assert not _sibling_steps(own_checkout_only)
