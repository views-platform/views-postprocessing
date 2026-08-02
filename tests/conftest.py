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

#: repo name -> the environment variable that overrides its location.
#: Declared, never derived from the name: ``views-datafactory`` → ``VIEWS_DATAFACTORY``
#: happens to be mechanical, but a future sibling need not follow the pattern and
#: guessing it would be the inference ADR-003 forbids.
SIBLING_ENV = {
    "views-datafactory": "VIEWS_DATAFACTORY",
    "views-appwrite": "VIEWS_APPWRITE",
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
