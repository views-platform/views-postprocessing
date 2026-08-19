"""The machinery imports without the partner — proven in a subprocess (S7 / #155).

**Why a subprocess.** An in-process check is worthless here: by the time pytest has
collected this file it has already imported the whole package, so
``"views_postprocessing.unfao" in sys.modules`` is true regardless of what
``contract/`` actually depends on. The only honest way to ask "does importing the
machinery drag in the partner?" is to start a fresh interpreter that imports *only*
the machinery and look at what arrived with it.

This is the mechanism views-pipeline-core uses to keep pandas out of its frame path
(their ``tests/test_import_purity.py``, #321), and þing-02 recorded it as the pattern
for turning a rule into a test rather than a promise.

**Why it exists at all.** #153 separated partner-neutral machinery (``contract/``)
from FAO's product (``unfao/``). Nothing then stops the next contributor adding one
convenient import back — and the boundary would be gone with no signal, because
everything would still work *for FAO*. Register C-69's fix is one-shot; this is what
makes it hold.

**Amended 2026-08-03 (#211): there are now two partners, and the guard was scoped to
one by name.** ``crafd/`` joined ``unfao/`` and every assertion here hardcoded the
string ``"views_postprocessing.unfao"``, so ``contract/`` could import ``crafd`` and
nothing objected — verified by adding exactly that import and watching the suite stay
green. The partners are now **declared** in ``_PARTNER_PACKAGES`` and checked against
the filesystem, because a guard that names its subject will miss the next subject
(register C-57's 2026-08-03 amendment, which is the same failure one file over).
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

# The partner and machinery package lists are declared once, in tests/conftest.py, and
# imported by every guard that needs them. Four guards each carrying their own copy of
# the string "unfao" is how `crafd` arrived unguarded — see that module's comment.
from tests.conftest import MACHINERY_PACKAGES as _MACHINERY_PACKAGES
from tests.conftest import PARTNER_PACKAGES as _PARTNER_PACKAGES

_REPO = Path(__file__).resolve().parent.parent
_PKG = _REPO / "views_postprocessing"

#: Every partner-neutral module a clone is expected to reuse as-is.
_MACHINERY = (
    "views_postprocessing.delivery.coverage",
    "views_postprocessing.delivery.draws",
    "views_postprocessing.delivery.parity",
    "views_postprocessing.delivery.findability",
    "views_postprocessing.delivery.observed_range",
    "views_postprocessing.delivery.provenance",
    "views_postprocessing.contract.wire.sink",
    "views_postprocessing.contract.wire.source_selection",
    "views_postprocessing.contract.wire.header",
    "views_postprocessing.contract.wire.shard",
    "views_postprocessing.contract.wire.sidecar",
    "views_postprocessing.contract.wire.run_manifest",
    "views_postprocessing.contract.wire.naming",
    "views_postprocessing.contract.frames",
    "views_postprocessing.contract.frame_extraction",
    "views_postprocessing.contract.track_a_source",
    "views_postprocessing.contract.historical",
    "views_postprocessing.contract.gaul_lookup",
    "views_postprocessing.contract.gaul_schema",
    "views_postprocessing.contract.launch_config",
    "views_postprocessing.contract.source_metadata",
    "views_postprocessing.contract.store_metadata",
)


def _import_in_subprocess(
    modules: tuple[str, ...], forbidden_prefixes: tuple[str, ...]
) -> subprocess.CompletedProcess:
    """Import ``modules`` in a fresh interpreter; report any ``forbidden_prefixes`` arrivals."""
    script = textwrap.dedent(f"""
        import sys
        for name in {list(modules)!r}:
            __import__(name)
        leaked = sorted(
            m for m in sys.modules
            if any(m.startswith(p) for p in {list(forbidden_prefixes)!r})
        )
        print("LEAKED:" + ",".join(leaked))
    """)
    return subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, cwd=_REPO, timeout=120,
    )


#: The subset of the above that is the bottom of the stack. ADR-002's chain is
#: ``<partner>/ -> contract/ -> delivery/``, and the arrow points one way: the
#: invariants must be usable without the machinery that calls them.
_INVARIANTS = tuple(
    m for m in _MACHINERY if m.startswith("views_postprocessing.delivery.")
)


def _partner_prefixes() -> tuple[str, ...]:
    return tuple(f"views_postprocessing.{name}" for name in _PARTNER_PACKAGES)


def _modules_on_disk(package: str) -> set[str]:
    return {
        "views_postprocessing." + f.relative_to(_PKG).with_suffix("").as_posix().replace("/", ".")
        for f in (_PKG / package).rglob("*.py")
        if f.name != "__init__.py"
    }


def test_the_machinery_list_is_the_whole_machinery():
    """Assert this guard's inputs are real — the clause it kept applying elsewhere.

    ``_MACHINERY`` is a hand-written tuple, and every purity check here iterates it. A
    machinery module missing from it is never imported in the subprocess, so it can
    depend on a partner and nothing objects.

    **That was not hypothetical.** ``contract/enrichment.py`` was absent, and nothing
    else in the package imports it, so it was never dragged in transitively either:
    verified 2026-08-03 that ``from ..crafd import product`` in that file left the whole
    suite green. This changeset added a completeness assertion to five other declared
    lists (ADR-014 §2) and missed the one in the file that argues for them.
    """
    declared = set(_MACHINERY)
    # Derived from the declared machinery list, not from two names written here. A
    # third machinery package added to MACHINERY_PACKAGES and forgotten here would
    # otherwise be exempt from every purity check — which is the defect this whole
    # changeset moved four other lists into conftest.py to prevent, reproduced inside
    # the test written to enforce it.
    on_disk = set().union(*(_modules_on_disk(p) for p in _MACHINERY_PACKAGES))

    assert not (on_disk - declared), (
        f"machinery modules absent from _MACHINERY: {sorted(on_disk - declared)}. Each "
        "is exempt from every purity check in this file — it may import a partner, and "
        "nothing here will notice."
    )
    assert not (declared - on_disk), (
        f"_MACHINERY names modules that no longer exist: {sorted(declared - on_disk)}. "
        "A subprocess that imports a vanished module fails confusingly; one that was "
        "quietly dropped from the list stops being checked."
    )


def test_the_invariants_import_without_the_machinery():
    """ADR-002's lower arrow, proven the way the upper one is.

    ``delivery/`` sits below ``contract/`` and must stay usable on its own — that is
    what makes the invariants *representation-free* rather than merely
    representation-light, and it is what lets a partner reuse them without the wire.

    **A regex was written for this first and was not enough.** It caught
    ``from views_postprocessing.contract import gaul_schema`` — the one form used to
    demonstrate the gap — while missing ``from ..contract import gaul_schema`` and
    ``from views_postprocessing import contract``, both plain module-level imports that
    execute on import. A fresh interpreter sees all of them, which is why this is the
    load-bearing half and the regex in ``test_doc_accuracy.py`` is the supplement that
    also covers imports hidden in function bodies.
    """
    result = _import_in_subprocess(
        _INVARIANTS, ("views_postprocessing.contract",) + _partner_prefixes()
    )
    assert result.returncode == 0, (
        f"the invariants failed to import on their own:\n{result.stderr}"
    )
    leaked = [m for m in result.stdout.split("LEAKED:")[-1].strip().split(",") if m]
    assert not leaked, (
        f"importing delivery/ pulled in the machinery above it: {leaked}. ADR-002's "
        "dependency arrow points one way; an invariant that needs the wire to load is "
        "no longer an invariant about primitives."
    )


def test_the_declared_partner_list_is_the_real_one():
    """Assert the guard's inputs are real (ADR-014 §2).

    Every other test here trusts ``_PARTNER_PACKAGES``. A partner package that exists
    on disk but is missing from that tuple is unguarded, and the suite stays green —
    which is exactly what happened to ``crafd`` on the day it landed. So the tuple is
    checked against the filesystem rather than believed.

    A new top-level package under ``views_postprocessing/`` is either a partner or
    machinery. If it is neither, this fails and someone decides which it is, on
    purpose, rather than by whichever guard happens not to mention it.

    **Why "contains a .py" and not "contains an ``__init__.py``".** The first draft
    asked for ``__init__.py`` — a criterion ``views_postprocessing/`` itself fails, since
    the distribution root has no ``__init__.py`` and is already a PEP 420 namespace
    package. A partner directory without one imports perfectly at runtime and was
    invisible here: verified 2026-08-03 by building a namespace partner carrying three
    real defects (``UPLOAD_ENABLED = True``, a wrong consumer name, a live
    ``load_dotenv``) and watching the full suite stay green, with one empty
    ``__init__.py`` the entire difference. Every other tree scan in this suite uses
    ``rglob("*.py")`` and would have seen it; this guard was the odd one out.

    **And ``rglob`` is why, not ``glob``.** The first correction used ``glob("*.py")``
    while its own comment claimed parity with the ``rglob`` scans — so a partner whose
    modules sit only in ``managers/`` (which is where a partner's manager actually
    lives) was *still* invisible. Verified: ``wfp/managers/wfp.py`` carrying a live
    ``load_dotenv`` passed this guard. Two drafts, the same mistake, caught the second
    time only because someone checked the sentence against the code.
    """
    on_disk = {
        p.name for p in _PKG.iterdir()
        if p.is_dir() and p.name != "__pycache__" and any(p.rglob("*.py"))
    }
    classified = set(_PARTNER_PACKAGES) | set(_MACHINERY_PACKAGES)

    for label, declared in (
        ("_PARTNER_PACKAGES", _PARTNER_PACKAGES),
        ("_MACHINERY_PACKAGES", _MACHINERY_PACKAGES),
    ):
        missing = sorted(p for p in declared if p not in on_disk)
        assert not missing, (
            f"{label} names packages that do not exist: {missing}. A guard whose "
            "declared scope has gone missing scans nothing and reports success — and a "
            "stale name here is worse than dead, because it pre-classifies any future "
            "package that happens to take it (register C-47: `reconciliation` was "
            "exactly such a phantom in this tree)."
        )

    unclassified = sorted(on_disk - classified)
    assert not unclassified, (
        f"new top-level package(s) {unclassified} are neither declared partners nor "
        "declared machinery. Add each to PARTNER_PACKAGES or MACHINERY_PACKAGES in "
        "tests/conftest.py — a partner left out of the first is silently exempt from "
        "every check below."
    )


def test_the_machinery_imports_without_any_partner():
    """The load-bearing assertion of the whole epic.

    A clone must be able to take `delivery/` and `contract/` and get a working
    ADR-013 delivery without inheriting any partner's product, store coordinates, or
    manager. "Any" is the operative word since #211: the machinery serves two
    partners now, and being neutral toward one of them is not neutrality.
    """
    result = _import_in_subprocess(_MACHINERY, _partner_prefixes())
    assert result.returncode == 0, (
        f"the machinery failed to import on its own:\n{result.stderr}"
    )
    leaked = [m for m in result.stdout.split("LEAKED:")[-1].strip().split(",") if m]
    assert not leaked, (
        f"importing the partner-neutral machinery pulled in a partner: {leaked}. "
        "The next partner would inherit that one's product through this path — see "
        "register C-69 and views_postprocessing/contract/__init__.py."
    )


def test_the_machinery_does_not_pull_in_pipeline_core():
    """`views_pipeline_core` is imported only by the partner managers.

    Pinned while it is true. Each partner's manager is written against its own
    framework seam; if the machinery started dragging pipeline-core in, that choice
    would be made for every partner at once, and register C-40's blast radius would
    widen from two files to the whole package.

    ADR-013 §11.4-adjacent: þing-02 **S24(5)** binds *the cloned repositories* —
    `un-crafdapi` and `views-productionapi`, cut from views-faoapi — not to import
    `views_pipeline_core.modules.{appwrite,datastore}`. It does not reach an in-repo
    partner package of the producer, which is why `crafd/managers/crafd.py` may import
    them and `docs/CLONING.md` was corrected. What this test defends is the narrower
    and repo-owned rule: the *machinery* stays free of them regardless.
    """
    result = _import_in_subprocess(_MACHINERY, ("views_pipeline_core",))
    assert result.returncode == 0, result.stderr
    leaked = [m for m in result.stdout.split("LEAKED:")[-1].strip().split(",") if m]
    assert not leaked, (
        f"the machinery pulled in views_pipeline_core: {leaked}. It is imported only "
        "by the partner managers, and that is what keeps C-40 bounded."
    )


@pytest.mark.parametrize("partner", _PARTNER_PACKAGES)
def test_the_guard_would_actually_catch_a_violation(partner):
    """A purity test that cannot fail is decoration.

    Imports each *partner* deliberately and asserts the detector sees it — so a
    future reader knows the tests above are load-bearing rather than vacuously
    passing because the subprocess silently did nothing. Parametrised, because a
    detector proven against one partner is not proven against the other.
    """
    result = _import_in_subprocess(
        (f"views_postprocessing.{partner}.product",), _partner_prefixes()
    )
    assert result.returncode == 0, result.stderr
    leaked = [m for m in result.stdout.split("LEAKED:")[-1].strip().split(",") if m]
    assert leaked, f"the detector reported nothing while importing {partner} directly"


@pytest.mark.parametrize("doc", ["docs/CLONING.md"])
def test_the_cloning_guide_exists_and_names_what_must_be_supplied(doc):
    """The guide is the human half of this proof; the tests are the machine half."""
    text = (_REPO / doc).read_text()
    for required in ("product", "appwrite_env", "manager", "views_pipeline_core"):
        assert required in text, f"docs/CLONING.md does not mention {required!r}"
