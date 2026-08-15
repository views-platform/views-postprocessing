"""Refusals of the shared seam-registry reader (`tests/seam_registry.py`).

These moved out of `tests/test_env_declaration.py` on 2026-08-14 (issue #265). Their
subject is the *reader* — `registry_at`, `registry_current`, `rows` — not what this
package declares about its environment, and a 1503-line module that had become the home
for both was the clearest signal in the repo that a boundary was wrong.

What deliberately did **not** move with them: the coordinate-value scan. Its subject is
`_EXPECTED_NAMES`, derived from the partner declarations that are the substance of
`test_env_declaration.py`, and separating a guard from the declaration it guards to make
a filename read better trades a real coupling for a filing convenience. The reasoning is
in register C-89.

Every refusal here is a real failure someone hit: an empty pin, a commit this clone does
not have, a ref that is not a commit, a registry that will not parse, and a section whose
rows are scalars rather than tables (C-91).
"""

import subprocess
from pathlib import Path

import pytest

from tests.seam_registry import (
    REGISTRY_RELPATH,
    RegistryReadError,
    registry_at,
    registry_current,
    rows,
)


def _scratch_repo(tmp_path: Path):
    """A throwaway git repo whose registry differs on `main`, on `origin/main`, and on disk.

    `-c` rather than `git config`: a contributor's global `commit.gpgsign` or
    `core.hooksPath` would otherwise reach in and either fail opaquely or block on
    pinentry with no timeout.
    """
    def git(*args):
        return subprocess.run(
            ["git", "-C", str(tmp_path), "-c", "commit.gpgsign=false",
             "-c", "core.hooksPath=/dev/null", *args],
            capture_output=True, text=True, check=True, timeout=30,
        )

    target = tmp_path / REGISTRY_RELPATH
    target.parent.mkdir(parents=True)

    def edition(marker: str) -> str:
        return f'[meta]\nversion = "{marker}"\n\n[connection.X]\nclass = "connection"\n'

    git("init", "-q", "-b", "main")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    target.write_text(edition("on-main"))
    git("add", "-A")
    git("commit", "-q", "-m", "main")

    # a remote-tracking ref that is AHEAD of main, so preferring one over the other shows
    git("checkout", "-q", "-b", "upstream")
    target.write_text(edition("on-origin-main"))
    git("add", "-A")
    git("commit", "-q", "-m", "origin")
    git("update-ref", "refs/remotes/origin/main", "HEAD")
    git("checkout", "-q", "main")

    # and a dirty working tree, which is what #196 was about
    target.write_text(edition("in-the-working-tree"))
    return tmp_path


def test_registry_current_reads_origin_main_not_the_working_tree(tmp_path):
    """The reason `tests/seam_registry.py` exists, and until now the only untested part.

    A sibling clone sits on whatever branch its own agent last worked on. Comparing
    against that grades this repository on unreviewed content — issue #196, which cost a
    withdrawn pull request. Replacing this function with a working-tree or `HEAD` read
    used to leave the whole suite green.
    """
    repo = _scratch_repo(tmp_path)
    assert registry_current(repo)["meta"]["version"] == "on-origin-main", (
        "registry_current read something other than origin/main. A working-tree read is "
        "#196 verbatim; a bare `main` read misses that the sibling's remote has moved."
    )


def test_registry_current_refuses_a_repo_with_neither_ref(tmp_path):
    """No `origin/main` and no `main` must say so, not return an empty registry."""
    subprocess.run(["git", "init", "-q", str(tmp_path)],
                   capture_output=True, text=True, check=True, timeout=30)
    with pytest.raises(RegistryReadError, match="neither origin/main nor main"):
        registry_current(tmp_path)


def test_registry_at_refuses_a_commit_whose_registry_is_missing_or_unparseable(tmp_path):
    """`git show` failing, and a blob that is not TOML — two refusal branches nothing reached."""
    def git(*args):
        return subprocess.run(
            ["git", "-C", str(tmp_path), "-c", "commit.gpgsign=false",
             "-c", "core.hooksPath=/dev/null", *args],
            capture_output=True, text=True, check=True, timeout=30,
        )
    git("init", "-q", "-b", "main")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")

    (tmp_path / "unrelated.txt").write_text("no registry here\n")
    git("add", "-A")
    git("commit", "-q", "-m", "no registry")
    absent = git("rev-parse", "--short", "HEAD").stdout.strip()

    target = tmp_path / REGISTRY_RELPATH
    target.parent.mkdir(parents=True)
    target.write_text("this is not toml = = =\n")
    git("add", "-A")
    git("commit", "-q", "-m", "not toml")
    garbage = git("rev-parse", "--short", "HEAD").stdout.strip()

    with pytest.raises(RegistryReadError, match="cannot read the registry"):
        registry_at(tmp_path, absent)
    with pytest.raises(RegistryReadError, match="did not parse as TOML"):
        registry_at(tmp_path, garbage)


def test_rows_refuses_a_section_whose_entries_are_not_tables():
    """`[test_environment]` on the live registry is scalars, not sub-tables.

    Nothing breaks today because that table is IGNORED — but the partition check's own
    remediation message tells a maintainer to classify a new table CONSUMED, and doing
    that for one written this way used to return an `AttributeError` from a dict
    comprehension. Register C-91.
    """
    scalars = {"test_environment": {"status": "none", "fact": "a sentence"}}
    with pytest.raises(RegistryReadError, match=r"\[test_environment\]\.(status|fact) is a bare str"):
        rows(scalars, ("test_environment",))

    # and the ordinary shape still works, or the refusal above proves nothing
    tables = {"target": {"APPWRITE_X": {"class": "target", "value": "v"}}}
    assert rows(tables, ("target",)) == {"APPWRITE_X": ("target", "target", "v")}
