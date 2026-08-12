"""Reading the platform coordinate registry, and refusing to read it badly.

The registry is a TOML file in **views-appwrite** declaring every cross-repository
coordinate on the delivery seam. This repository never copies it — it is referenced, and
read from a sibling checkout when one is present.

**Why this is its own module.** Two test modules now need it: `test_env_declaration.py`
for the coordinate sections, `test_product.py` for the `[contract.*]` delivery labels.
It began as one reader, was hand-copied into the second, and the copies immediately
disagreed — one read the sibling's `main`, the other whatever branch the clone sat on,
which is the very defect a review had just caught in the first. That is the second
incident, which is this repository's stated trigger for extracting (WET before DRY: two
copies that are understood beat one abstraction that is guessed — until the second copy
proves the shape).

It is deliberately **not** in `conftest.py`. That file already holds four unrelated
groups and register **C-88**'s trigger is a fifth arriving.

**What this module refuses, and why each refusal exists.** Every one is a real accident
that a silent read would have turned into a permanently green test:

- a ref that does not resolve, or resolves to something that is not a commit;
- a ref whose resolved sha does not begin with it — an annotated **tag**, which git peels
  silently and which yields a 404 from the blob URL these modules publish;
- an **empty** file: `tomllib.loads("")` is `{}`, and an empty registry compared against
  an empty projection passes forever;
- a file that parses but carries no `meta.version` and no `connection` rows, i.e. is not
  the registry;
- a parse error, wrapped rather than raised raw — a helper whose justification is failing
  legibly must not hand back a bare traceback.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

#: The registry, relative to a views-appwrite checkout.
REGISTRY_RELPATH = Path("docs") / "ADRs" / "platform" / "coordinate_registry.toml"

#: A row that carries no value at all — distinct from any string a registry could hold.
ABSENT = object()


class RegistryReadError(RuntimeError):
    """The registry could not be read — never a silently empty dict."""


def registry_at(repo: Path, ref: str) -> dict:
    """The registry as it stood at ``ref``. Raises rather than returning ``{}``.

    ``ref`` must name a **frozen commit**, and that has no exceptions. An empty ref reads
    the git index; a branch name reads a moving tip. Either makes a pin-versus-current
    comparison compare the registry to itself and report green against every future
    edition — which is the trap this module exists for, so an exemption "just for the
    caller that needs a branch" reopens it. Callers wanting `main` resolve it to a sha
    first; :func:`registry_current` does exactly that.
    """
    tomllib = pytest.importorskip("tomllib", reason="stdlib from 3.11; pyproject requires it")

    resolved = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
        capture_output=True, text=True, check=False, timeout=30,
    )
    if resolved.returncode != 0 or not resolved.stdout.strip():
        # Two conditions used to share this message, and they have different remedies.
        # A ref this clone has never heard of is an environment problem — a shallow or
        # `--single-branch` clone, or one made before the pin. A ref that resolves to
        # something that is not a commit is a pin defect. Only the second is this
        # repository's fault; only the first is fixed by fetching (register C-91).
        if not ref.strip():
            raise RegistryReadError(
                "the pin is empty, and an empty ref does not resolve to a commit — "
                "`git show ':<path>'` reads the INDEX, so a blanked pin would compare "
                "the registry to itself and report green against every future edition. "
                "This is a defect in the pin, not in the checkout."
            )
        known = subprocess.run(
            ["git", "-C", str(repo), "cat-file", "-e", f"{ref}^{{object}}"],
            capture_output=True, text=True, check=False, timeout=30,
        ).returncode == 0
        if not known:
            raise RegistryReadError(
                f"{repo} has no object {ref!r}. This is almost always a clone that is "
                "shallow, `--single-branch`, or simply older than the pin — run "
                f"`git -C {repo} fetch --tags origin` and try again. It is not a defect "
                "in the pin: nothing here can tell whether that commit is good until "
                "this checkout can see it."
            )
        raise RegistryReadError(
            f"{ref!r} exists in {repo} but does not resolve to a commit. A pin must name "
            "a frozen commit: an empty ref reads the index and a branch reads a moving "
            "tip, and either would make the comparison compare the registry to itself."
        )
    if not resolved.stdout.strip().startswith(ref):
        raise RegistryReadError(
            f"{ref!r} resolves to commit {resolved.stdout.strip()[:12]}, which does not "
            "start with it — that is what an annotated TAG looks like. git peels tags "
            "silently, so every check here would pass while the blob URL these modules "
            "publish returns 404. Pin the commit."
        )

    result = subprocess.run(
        ["git", "-C", str(repo), "show", f"{ref}:{REGISTRY_RELPATH.as_posix()}"],
        capture_output=True, text=True, check=False, timeout=30,
    )
    if result.returncode != 0:
        raise RegistryReadError(
            f"cannot read the registry at {ref!r} in {repo}: git exited "
            f"{result.returncode} ({result.stderr.strip()[:200]}). A pinned commit that "
            "cannot be read is not a baseline — run `git fetch` in that checkout."
        )
    if not result.stdout.strip():
        raise RegistryReadError(
            f"the registry is EMPTY at {ref!r} in {repo}. Treating that as a registry "
            "with no coordinates would make every comparison against it pass."
        )
    try:
        registry = tomllib.loads(result.stdout)
    except Exception as exc:
        raise RegistryReadError(
            f"the registry at {ref!r} in {repo} did not parse as TOML: {exc}. This is "
            "what happens when the path names a directory, or the blob is not the file "
            "we think it is."
        ) from exc
    if not registry.get("meta", {}).get("version") or not registry.get("connection"):
        raise RegistryReadError(
            f"the registry at {ref!r} parsed but carries no meta.version or no connection "
            "rows. Every real edition has both, so this is not the file we think it is — "
            "refusing rather than comparing against it."
        )
    return registry


def registry_current(repo: Path) -> dict:
    """The registry as the sibling's ``main`` has it — never its working tree.

    A sibling clone normally sits on whatever branch its own agent last worked on.
    Comparing against that grades this repository on unreviewed content, or reddens it on
    a branch nobody merged — issue #196 verbatim, the case that cost this platform a
    withdrawn pull request. The `ref: main` discipline lived only inside the CI workflow;
    a developer running the suite locally had no such thing.

    Read errors propagate unchanged, so a registry that is corrupt or anchorless **on
    main** says so, rather than being reported as "neither ref resolves".
    """
    head = ""
    for ref in ("origin/main", "main"):
        resolved = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
            capture_output=True, text=True, check=False, timeout=30,
        )
        if resolved.returncode == 0 and resolved.stdout.strip():
            head = resolved.stdout.strip()
            break
    if not head:
        raise RegistryReadError(
            f"neither origin/main nor main resolves in {repo}. The comparison is against "
            "that repository's ratified content, so there is nothing to compare against "
            "— run `git fetch` there."
        )
    return registry_at(repo, head)


def rows(registry: dict, sections: tuple) -> dict[str, tuple]:
    """``name -> (section, class, value-or-ABSENT)`` across ``sections``.

    The one shared projection. Two hand-copied versions had already diverged on null
    handling — one raised ``AttributeError`` on a null section, the other did not.
    """
    out = {}
    for section in sections:
        for name, body in (registry.get(section) or {}).items():
            if not isinstance(body, dict):
                # `[test_environment]` on the live registry is exactly this — top-level
                # strings, not sub-tables. Reaching it means someone classified such a
                # table CONSUMED, which the partition check's own remediation message
                # invites. Refusing by name beats an AttributeError from a comprehension
                # in the module whose justification is failing legibly (register C-91).
                raise RegistryReadError(
                    f"[{section}].{name} is a bare {type(body).__name__}, not a table. "
                    "This section's rows are scalars, so it carries no class or value to "
                    "read — it cannot be CONSUMED. Classify it IGNORED with a reason, or "
                    "read it with something other than `rows()`."
                )
            out[name] = (section, body.get("class"), body.get("value", ABSENT))
    return out
