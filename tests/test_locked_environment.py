"""The environment the suite runs in is the environment the lockfile describes (C-104).

**Why this exists.** On 2026-08-16 a `pytest` run in this repository reported 25
failures across five modules. None was a defect. The virtualenv held
`views-pipeline-core 2.3.0` and `pyarrow 23.0.1` while `poetry.lock` pinned `3.0.1`
and `16.1.0`, and the two majors of drift produced:

* `ModuleNotFoundError: views_pipeline_core.modules.dataloaders.datafactory_contract`
  at the import of both managers — which takes out **every** test that constructs or
  inspects one, i.e. the only coverage the two largest modules in the package have;
* five byte-parity failures against the ADR-013 §10 golden fixture, because parquet
  bytes are not stable across pyarrow majors (C-72).

Neither is distinguishable, from the failure output, from a real regression. A
contributor reading that wall has no way to tell "your venv is stale" from "you broke
the wire contract", and the second reading is the one that costs an afternoon.

**What this does not do.** It does not fix the drift and it does not skip. It replaces
25 misleading failures with one that names the packages, the two versions, and the
command. The other 25 stay until `poetry install` runs — they are the *symptom*, this
is the *diagnosis*, and the repo's position (ADR-014 §1) is that a diagnosis belongs in
a check rather than in a register entry nobody reads at the moment it would help.

**Scope: the declared runtime dependencies, read from `pyproject.toml`.** Not a
hardcoded list — that would go stale the first time a dependency is added, which is
the failure mode `tests/conftest.py::PARTNER_PACKAGES` exists to prevent one level up.
Dev-group tools are deliberately out: `ruff`'s version genuinely varies by how it was
installed, and its *rule set* — the thing that actually broke CI on 2026-08-03 — is
already pinned explicitly in `pyproject.toml`.

CI runs `poetry install` before `pytest`, so this passes there by construction. It is
aimed squarely at the developer machine, which is the seat that had the problem.
"""

from __future__ import annotations

import tomllib
from importlib import metadata
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_PYPROJECT = _REPO / "pyproject.toml"
_LOCK = _REPO / "poetry.lock"


def _declared_runtime_dependencies() -> list[str]:
    """The distributions `pyproject.toml` declares this package needs at runtime."""
    project = tomllib.loads(_PYPROJECT.read_text())
    deps = project["tool"]["poetry"]["dependencies"]
    return [name for name in deps if name != "python"]


def _locked_versions() -> dict[str, str]:
    return {p["name"]: p["version"] for p in tomllib.loads(_LOCK.read_text())["package"]}


def test_the_lockfile_and_pyproject_agree_on_what_is_declared():
    """A declared dependency absent from the lock means the lock was never regenerated.

    Checked before the version comparison below, because that comparison would
    otherwise report a missing package as "installed X, locked None" and send the
    reader looking at their virtualenv rather than at `poetry lock`.
    """
    locked = _locked_versions()
    missing = [name for name in _declared_runtime_dependencies() if name not in locked]
    assert not missing, (
        f"declared in pyproject.toml but absent from poetry.lock: {missing}. The lock "
        "is stale with respect to the declaration — run `poetry lock` and commit it."
    )


def test_the_installed_runtime_dependencies_match_the_lockfile():
    """One honest failure instead of twenty-five misleading ones (C-104)."""
    locked = _locked_versions()
    drift = []
    for name in _declared_runtime_dependencies():
        try:
            installed = metadata.version(name)
        except metadata.PackageNotFoundError:
            installed = None
        expected = locked.get(name)
        if installed != expected:
            drift.append((name, installed, expected))

    if not drift:
        return

    table = "\n".join(
        f"    {name:24} installed={installed or 'NOT INSTALLED':<12} locked={expected}"
        for name, installed, expected in drift
    )
    pytest.fail(
        "this virtualenv is not the one poetry.lock describes:\n"
        f"{table}\n\n"
        "Run `poetry install`.\n\n"
        "Any OTHER failures in this run are most likely consequences of the drift "
        "above, not defects. Two majors of views-pipeline-core remove "
        "`modules.dataloaders.datafactory_contract`, which both managers import at "
        "module scope — so every test that touches a manager dies at collection. A "
        "pyarrow major changes emitted parquet bytes, which fails the ADR-013 §10 "
        "byte-parity fixture (C-72). Fix the environment before reading them as bugs.\n\n"
        "If the drift is deliberate — trialling an upgrade — this test is telling you "
        "the truth and the rest of the suite is not testing the locked contract."
    )
