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
from dataclasses import dataclass
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

@dataclass(frozen=True, kw_only=True)
class Sibling:
    """What this repository declares about one views-platform sibling (ADR-016).

    Two of these fields are different kinds of thing and the distinction is the point.
    ``public`` is a **fact about the world** that this repository does not control.
    ``ci_checkout`` is a **decision** this repository makes. Conflating them is how the
    workflow ended up asserting, in a comment, that ``views-appwrite`` was private for
    days after it went public — and how seven checks stayed dark in CI for no reason.

    ``public_checked`` is the date the fact was last verified, and it is not decoration:
    every measured claim in this repository carries one. A bare boolean is a fact with no
    expiry, which is precisely what went wrong.

    **Keyword-only and frozen, deliberately.** Two adjacent booleans are a one-token slip
    between "public, not checked out" and "private, checked out" — the second being the
    combination rule G3 exists to forbid. A plain dict would let a missing ``ci_checkout``
    read as ``None``, silently exempting that sibling from every guard; that is the
    failure mode this repository has registered more often than any other (C-47, C-57,
    #211). Here the omission is a ``TypeError`` at import.

    **No validation in ``__post_init__``.** See ``broken_sibling_overrides`` below for
    what raising at import time costs: one typo became three collection errors and zero
    tests run. The rules live in ``tests/test_ci_sibling_coverage.py``, where a violation
    is one clean failure and the other four hundred tests still report.
    """

    #: The environment variable that overrides this sibling's location. Declared, never
    #: derived: ``views-datafactory`` → ``VIEWS_DATAFACTORY`` happens to be mechanical,
    #: but a future sibling need not follow the pattern and guessing it would be the
    #: inference ADR-003 forbids.
    env: str
    #: Visibility on GitHub — a fact about the world, not a decision of ours.
    public: bool
    #: ISO date ``public`` was last verified. See the class docstring.
    public_checked: str
    #: Whether CI checks this sibling out. A decision, and the reason for it belongs in
    #: ``note`` whenever the answer is no.
    ci_checkout: bool
    #: Why this sibling is not checked out. Required when ``ci_checkout`` is False, and
    #: must name a record, so the non-coverage has an owner rather than a shrug.
    note: str = ""


#: The views-platform repositories whose current state this repository's tests read.
#:
#: `views-appwrite` was private until **2026-08-08**, when it was deliberately made
#: public (`views-appwrite@9d80b75`, "docs: record going public"). The workflow comment
#: here went on saying PRIVATE afterwards, which is the whole argument for declaring the
#: fact with a date instead of narrating it in prose.
SIBLINGS = {
    "views-datafactory": Sibling(
        env="VIEWS_DATAFACTORY",
        public=True,
        public_checked="2026-08-10",
        ci_checkout=False,
        note=(
            "public, but its checks need the producer's raw GAUL parquets "
            "(data/raw/gaul_admin/*.parquet), which are NOT in its git repository. "
            "Checking it out converts an honest skip into a FileNotFoundError — measured "
            "2026-08-03, tried and reverted. Closing this needs the data published "
            "somewhere fetchable, not an access grant. Register C-46."
        ),
    ),
    "views-appwrite": Sibling(
        env="VIEWS_APPWRITE",
        public=True,
        public_checked="2026-08-10",
        ci_checkout=True,
    ),
    "views-faoapi": Sibling(
        env="VIEWS_FAOAPI",
        public=False,
        public_checked="2026-08-10",
        ci_checkout=False,
        note=(
            "the only private sibling. Checking it out needs a credential, which is an "
            "operator decision deferred pending a request to FAO to make the repository "
            "public. One check is dark meanwhile — the consumer-name pin, whose failure "
            "mode is a delivery nobody can find. See ADR-016 and register C-81."
        ),
    ),
    "views-crafdapi": Sibling(
        env="VIEWS_CRAFDAPI",
        public=True,
        public_checked="2026-08-10",
        ci_checkout=True,
    ),
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
    if name not in SIBLINGS:
        raise KeyError(
            f"no environment variable declared for sibling {name!r}; add it to "
            f"SIBLINGS rather than guessing one from the name"
        )
    override = os.environ.get(SIBLINGS[name].env)
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

    **An EMPTY variable is the case this missed, and it is the one CI produces.** The
    filter was ``if value and ...``, so ``VIEWS_APPWRITE=""`` read as unset:
    ``sibling_repo`` fell through to the conventional ``../views-appwrite``, which does
    not exist in a CI workspace, and seven checks skipped on a green build. A YAML
    interpolation that resolves to nothing — ``${{ env.TYPO }}`` — produces exactly that
    empty string, so this is the *likely* misconfiguration in CI, not an exotic one.

    ``.strip()`` and not merely ``if value is not None`` because **``Path("").exists()``
    is ``True``** — it resolves to the current directory. Dropping the truthiness test
    without the strip would report an empty override as a perfectly good checkout, which
    is worse than the bug being fixed.
    """
    return {
        var: value
        for var in (s.env for s in SIBLINGS.values())
        for value in [os.environ.get(var)]
        if value is not None and (not value.strip() or not Path(value).exists())
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
            f"{name} checkout not found — set {SIBLINGS[name].env}=/path/to/{name}, "
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
