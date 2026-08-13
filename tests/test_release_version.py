"""The package version and the git tag that installs it must agree.

Consumers install this package by tag — `views-models`' launchers do exactly that — and
then read `importlib.metadata.version(...)` to decide what the installed build can do
(views-models#294). So the number in `pyproject.toml` is what a consumer *believes* it
installed, and the tag is what it *actually* installed. Nothing compared them.

Measured 2026-08-13: tag `1.1.0` was cut at `main` while `pyproject.toml` still said
`1.0.0`, so an install from that tag reported the previous release. Caught before any
consumer pinned. Third time in this arc a version has been declared twice with a guard on
one copy (register C-80, C-82).
"""

import re
import subprocess
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent


def _declared_version() -> str:
    text = (_REPO / "pyproject.toml").read_text()
    match = re.search(r'^version = "([^"]+)"', text, re.M)
    assert match, (
        "pyproject.toml no longer declares a version in the form this guard reads. If the "
        "packaging changed, teach this test the new form — do not delete it, or the number "
        "a consumer installs goes unchecked again."
    )
    return match.group(1)


def _tags_at(commit: str) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(_REPO), "tag", "--points-at", commit],
        capture_output=True, text=True, check=False, timeout=30,
    )
    return sorted(t for t in out.stdout.split() if re.fullmatch(r"\d+\.\d+\.\d+", t))


def test_a_release_tag_declares_the_version_the_package_declares():
    """If HEAD carries a release tag, `pyproject.toml` must say the same number.

    Silent off a tagged commit — most commits are not releases, and firing on them would
    be the false alarm that gets a guard deleted (ADR-014 §3).
    """
    tags = _tags_at("HEAD")
    if not tags:
        pytest.skip("HEAD carries no release tag; nothing to compare")

    declared = _declared_version()
    assert tags == [declared], (
        f"HEAD is tagged {tags} but pyproject.toml declares {declared!r}. A consumer "
        "installing by tag would read the wrong version from importlib.metadata, which is "
        "what views-models#294's capability assert reads. Bump the file and re-point the "
        "tag, or tag a commit that already carries the right number."
    )


def test_the_newest_release_tag_is_not_ahead_of_the_declared_version():
    """A tag newer than the file means a release was cut without bumping.

    This is the direction that actually bit: the tag moved, the file did not. Runs on
    every commit, not only tagged ones, so the gap is visible the moment it opens.
    """
    out = subprocess.run(
        ["git", "-C", str(_REPO), "tag", "-l", "--sort=-v:refname"],
        capture_output=True, text=True, check=False, timeout=30,
    )
    releases = [t for t in out.stdout.split() if re.fullmatch(r"\d+\.\d+\.\d+", t)]
    if not releases:
        pytest.skip("no release tags in this checkout (a shallow clone, or none cut yet)")

    newest, declared = releases[0], _declared_version()
    as_tuple = lambda v: tuple(int(p) for p in v.split("."))  # noqa: E731
    assert as_tuple(newest) <= as_tuple(declared), (
        f"the newest release tag is {newest} but pyproject.toml declares {declared}. A "
        "release was cut without bumping the file, so an install from that tag reports a "
        "version older than itself."
    )
