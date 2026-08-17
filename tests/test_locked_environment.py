"""The environment the suite runs in is the environment the lockfile describes (C-104).

**Why this exists.** On 2026-08-16 a `pytest` run in this repository reported 25
failures across five modules. None was a defect. The virtualenv held
`views-pipeline-core 2.3.0` and `pyarrow 23.0.1` while `poetry.lock` pinned `3.0.1`
and `16.1.0`, and the two majors of drift produced:

* `ModuleNotFoundError: views_pipeline_core.modules.dataloaders.datafactory_contract`
  wherever a test imports a manager — which is every test that constructs or inspects
  one, i.e. the only coverage the two largest modules in the package have;
* five byte-parity failures against the ADR-013 §10 golden fixture, because parquet
  bytes are not stable across pyarrow majors (C-72).

Neither is distinguishable, from the failure output, from a real regression. A
contributor reading that wall has no way to tell "your venv is stale" from "you broke
the wire contract", and the second reading is the one that costs an afternoon.

**These are ordinary test failures, not collection errors** — the manager tests import
lazily (`tests/test_framework_contract.py:50`), so the session runs to completion.
Measured 2026-08-17 in the drifted venv: 26 failed, 441 passed, **0 errors**. That
distinction is not pedantry: a collection error would interrupt the session and this
diagnostic would never get to run in the scenario it was written for.

**What this does not do.** It does not fix the drift and it does not skip. It replaces
a wall of misleading failures with one that names the packages, both versions, and the
command. The others stay until `poetry install` runs — they are the *symptom*, this is
the *diagnosis*, and the repo's position (ADR-014 §1) is that a diagnosis belongs in a
check rather than in a register entry nobody reads at the moment it would help.

**Scope: the unconditional runtime dependencies declared in `pyproject.toml`**, read
from there rather than hardcoded — a literal list goes stale the first time a
dependency is added, which is the failure `tests/conftest.py::PARTNER_PACKAGES` exists
to prevent one level up. Dependencies gated by `optional`, `python` or `markers` are
skipped: they are legitimately absent from some environments, and reporting one as
"NOT INSTALLED — run `poetry install`" would be advice that cannot work. Dev-group
tools are out too: `ruff`'s reported version varies with how it was installed, and the
thing that actually broke CI on 2026-08-03 was its *rule set*, which `pyproject.toml`
already pins explicitly.

CI runs `poetry install` before `pytest`, so this passes there by construction. It is
aimed squarely at the developer machine, which is the seat that had the problem.
"""

from __future__ import annotations

import re
import tomllib
from importlib import metadata
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_PYPROJECT = _REPO / "pyproject.toml"
_LOCK = _REPO / "poetry.lock"

#: Spec keys that make a dependency conditional, so its absence is not drift.
_CONDITIONAL = ("optional", "python", "markers")


def _normalize(name: str) -> str:
    """PEP 503 normalization.

    `poetry.lock` stores normalized names; `pyproject.toml` stores whatever the author
    typed. `PyYAML` and `views_frames` are both legal declarations that would never
    match a lock entry compared raw — and the failure would read "absent from
    poetry.lock, run `poetry lock`", which would fix nothing because the lock is fine.
    """
    return re.sub(r"[-_.]+", "-", name).lower()


def _declared_runtime_dependencies() -> list[str]:
    """Unconditional runtime dependency names, normalized."""
    project = tomllib.loads(_PYPROJECT.read_text())
    try:
        deps = project["tool"]["poetry"]["dependencies"]
    except KeyError:
        pytest.fail(
            "pyproject.toml no longer declares [tool.poetry.dependencies] in the form "
            "this guard reads — a PEP 621 [project] migration would do this. Teach the "
            "test the new form; do not delete it, or nothing compares the environment "
            "to the lock again (C-104). Same treatment as tests/test_release_version.py."
        )
    return [
        _normalize(name)
        for name, spec in deps.items()
        if name != "python"
        and not (isinstance(spec, dict) and any(k in spec for k in _CONDITIONAL))
    ]


def _locked_versions() -> dict[str, str]:
    packages = tomllib.loads(_LOCK.read_text())["package"]
    return {_normalize(p["name"]): p["version"] for p in packages}


def test_every_declared_dependency_is_in_the_lockfile():
    """A declared dependency absent from the lock means the lock was never regenerated.

    Owned here rather than by the version check below, which skips names it cannot
    find — otherwise the same omission is reported twice, once correctly as a stale
    lock and once misleadingly as "installed X, locked None, run `poetry install`".
    """
    locked = _locked_versions()
    missing = sorted(set(_declared_runtime_dependencies()) - set(locked))
    assert not missing, (
        f"declared in pyproject.toml but absent from poetry.lock: {missing}. The lock "
        "is stale with respect to the declaration — run `poetry lock` and commit it. "
        "This is not a virtualenv problem and `poetry install` will not fix it."
    )


def test_the_installed_runtime_dependencies_match_the_lockfile():
    """One honest failure instead of a wall of misleading ones (C-104)."""
    locked = _locked_versions()
    drift = []
    for name in _declared_runtime_dependencies():
        expected = locked.get(name)
        if expected is None:
            continue  # not locked at all — the test above owns that, and says so better
        try:
            installed = metadata.version(name)
        except metadata.PackageNotFoundError:
            installed = None
        if installed != expected:
            drift.append((name, installed, expected))

    if not drift:
        return

    table = "\n".join(
        f"    {name:24} installed={installed or 'NOT INSTALLED':<12} locked={expected}"
        for name, installed, expected in drift
    )

    # Say what THIS drift causes, not what some remembered drift once caused. The 2026
    # incident was pipeline-core and pyarrow; a future one will not be, and a diagnosis
    # that describes the wrong packages is the failure this file exists to remove.
    drifted = {name for name, _, _ in drift}
    consequences = []
    if "views-pipeline-core" in drifted:
        consequences.append(
            "  - views-pipeline-core: the managers import "
            "`modules.dataloaders.datafactory_contract` at module scope, so every test "
            "that imports a manager fails. Those are ordinary failures, not collection "
            "errors — the whole suite still runs."
        )
    if "pyarrow" in drifted:
        consequences.append(
            "  - pyarrow: emitted parquet bytes are not stable across majors, so the "
            "ADR-013 §10 byte-parity fixture fails (C-72)."
        )
    detail = (
        "Known consequences of the packages above:\n" + "\n".join(consequences) + "\n\n"
        if consequences
        else ""
    )

    pytest.fail(
        "this virtualenv is not the one poetry.lock describes:\n"
        f"{table}\n\n"
        "Run `poetry install`.\n\n"
        f"{detail}"
        "Other failures in this run are likely consequences of the drift above rather "
        "than defects. Fix the environment before reading them as bugs.\n\n"
        "If the drift is deliberate — trialling an upgrade — this test is telling you "
        "the truth, and the rest of the suite is not testing the locked contract."
    )
