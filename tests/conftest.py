"""Shared test fixtures — currently just one: how to find a sibling repository.

**Why this exists (S6 / #187, S7 / #188; register C-46, C-57).** Three places needed a
views-platform sibling checkout and each found it differently:

- ``scripts/build_gaul_lookup.py`` resolved ``$VIEWS_DATAFACTORY``, then the sibling
  directory, with a ``--datafactory`` override and a fail-loud message naming both —
  the shape that has been working in production for weeks;
- ``tests/test_gaul_lookup_fidelity.py`` had its own ``skipif``;
- ``tests/test_datafactory_deploy_readiness.py`` hardcoded an **absolute path to one
  developer's laptop**, so the only cross-repo release gate in the repo has never run
  anywhere else — register **C-46**.

This is the second incident, which is this repo's named trigger for extracting. The
shape is not guessed: it is the one the build script already runs.

**Deliberately not a package import.** The siblings are separate repositories, not
dependencies — this repo declares three (`views-pipeline-core`, `views-frames`,
`pyarrow`) and none of them is a sibling checkout. What is being located is a
*working copy on disk*, for tests that compare this repo against another repo's
current state. If that ever becomes a runtime need, it is a different problem with a
different answer (a published artifact, not a path).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent

#: The partner packages under ``views_postprocessing/``, DECLARED (ADR-003) — and
#: declared **once**, because the alternative is what #211 exposed.
#:
#: **Eight** separate guards named ``"unfao"``, and when ``crafd/`` landed all eight
#: went on passing over a package they did not cover:
#:
#:   the import-purity subprocess · the ADR-002 direction check · the manager line
#:   budget · the coordinate-drift check · the þing-01 dotenv guard · and the three
#:   product pins (``TARGETS``, ``S_MIN``, ``UPLOAD_ENABLED``)
#:
#: So ``contract/`` could import ``crafd``; the second manager had no budget; a registry
#: pin two editions stale failed nothing; the retired ``load_dotenv`` borrow could be
#: reintroduced in the new manager; and nothing asserted the new partner's consumer
#: document name — the one field whose failure mode is a delivery nobody can find.
#:
#: A partner list per guard is eight places to forget the next partner; this is one.
#: (An earlier version of this comment said four. It was written by counting the guards
#: that had already been fixed.)
#:
#: ``tests/test_clone_readiness.py::test_the_declared_partner_list_is_the_real_one``
#: checks this against the filesystem, so the declaration cannot quietly go stale
#: either — ADR-014 §2: where a guard's inputs are declared, assert they are real.
PARTNER_PACKAGES = ("unfao", "crafd")

#: The partner-neutral packages. The split is two-sided: a new top-level package is
#: either a partner or machinery, and the same test refuses to let it be neither.
MACHINERY_PACKAGES = ("contract", "delivery")

#: repo name -> the environment variable that overrides its location.
#: Declared, never derived from the name: ``views-datafactory`` → ``VIEWS_DATAFACTORY``
#: happens to be mechanical, but a future sibling need not follow the pattern and
#: guessing it would be the inference ADR-003 forbids.
SIBLING_ENV = {
    "views-datafactory": "VIEWS_DATAFACTORY",
    "views-appwrite": "VIEWS_APPWRITE",
    "views-faoapi": "VIEWS_FAOAPI",
    "views-crafdapi": "VIEWS_CRAFDAPI",
}

#: partner package -> the repository that CONSUMES its delivery.
#:
#: Declared, never derived. ``unfao`` → ``views-faoapi`` and ``crafd`` →
#: ``views-crafdapi`` are not a pattern a rule could produce, and the þing records call
#: the second one ``un-crafdapi`` while the repository on disk is ``views-crafdapi`` —
#: exactly the kind of near-miss that makes guessing expensive.
#:
#: This exists so the consumer-document-name pin can be checked **across the seam**
#: rather than asserted locally. A name this repo declares and the consumer filters on
#: is a fact this repo does not own; declaring it here is right, but only the sibling
#: checkout can confirm it still matches (ADR-014 §1 — the guarantee needs a check).
CONSUMER_REPO = {
    "unfao": "views-faoapi",
    "crafd": "views-crafdapi",
}


def sibling_repo(name: str) -> Path | None:
    """The checkout of ``name``, or ``None`` if it is not resolvable.

    Order: the declared environment variable, then the conventional sibling directory
    **relative to this repository** — never an absolute path to a particular machine.

    Returns ``None`` rather than raising so callers can skip; a missing sibling is a
    normal condition in CI, where only this repo is checked out.
    """
    if name not in SIBLING_ENV:
        raise KeyError(
            f"no environment variable declared for sibling {name!r}; add it to "
            f"SIBLING_ENV rather than guessing one from the name"
        )
    override = os.environ.get(SIBLING_ENV[name])
    candidate = Path(override) if override else _REPO.parent / name
    return candidate if candidate.exists() else None


def broken_sibling_overrides() -> dict[str, str]:
    """Declared sibling variables that are SET but point at nothing.

    A typo'd override is an operator error, not a normal absence: someone set the
    variable because they meant to run those checks, and returning ``None`` turns the
    typo into permanent, invisible non-coverage of every cross-repo assertion this repo
    has. ``test_no_sibling_override_points_at_a_missing_path`` fails on it.

    **This is deliberately not a raise inside ``sibling_repo``.** It was, for about an
    hour. Three modules resolve a sibling at import time (``test_delivery_coverage``,
    ``test_datafactory_deploy_readiness``, ``test_gaul_lookup_fidelity``), so raising
    there turned a one-character typo in ``VIEWS_DATAFACTORY`` into
    ``Interrupted: 3 errors during collection`` and **zero tests run** — trading silent
    under-coverage for total loss of the suite. One clean failure says the same thing
    and lets the other 360 tests report.
    """
    return {
        var: value
        for var in SIBLING_ENV.values()
        for value in [os.environ.get(var)]
        if value and not Path(value).exists()
    }


def require_sibling(name: str) -> Path:
    """``sibling_repo`` or skip, with a message naming what to set.

    A skip that says only "checkout not present" tells a contributor nothing. This one
    tells them the variable and the conventional location, so the test is runnable
    rather than merely skippable.
    """
    path = sibling_repo(name)
    if path is None:
        pytest.skip(
            f"{name} checkout not found — set {SIBLING_ENV[name]}=/path/to/{name}, "
            f"or place it alongside this repo at {(_REPO.parent / name)}"
        )
    return path


def git_output(repo: Path, *args: str) -> str:
    """Run a read-only git command in ``repo``; empty string on any failure."""
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, check=False, timeout=30,
    )
    return result.stdout.strip()


def commit_is_on_main(repo: Path, commit: str) -> bool:
    """Is ``commit`` an ancestor of ``origin/main`` (falling back to ``main``)?

    **Existence is not reachability, and that distinction cost a PR** (#196). S3 pinned
    the Appwrite Seam Contract at a commit resolved with ``rev-parse HEAD`` on a
    checkout that happened to be sitting on an unmerged feature branch. The commit
    existed, both cited files existed at it, and every check anyone had written passed
    — but it had never reached ``main`` and was withdrawn days later.

    A pin is a claim about what the contract *says*. Only reachability from ``main``
    supports that claim.
    """
    for ref in ("origin/main", "main"):
        if not git_output(repo, "rev-parse", "--verify", "--quiet", ref):
            continue
        result = subprocess.run(
            ["git", "-C", str(repo), "merge-base", "--is-ancestor", commit, ref],
            capture_output=True, check=False, timeout=30,
        )
        return result.returncode == 0
    return False
