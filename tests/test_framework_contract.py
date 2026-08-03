"""What this repo actually needs from views-pipeline-core, asserted (C-44, C-40).

**Why this file exists: the rest of the suite proves nothing about the framework.**
Measured during the 3.0.0 bump with a plugin over the whole run — `views_pipeline_core`
was imported **zero** times. Every manager test here is a source scan (the managers need
Appwrite env and a views-models path manager to instantiate), and
`tests/test_clone_readiness.py` imports pipeline-core in a subprocess only to prove the
machinery does *not*. So 362 green tests were entirely orthogonal to a major framework
release, and "the suite passes" was not evidence about it.

That gap matters more here than in most repos. The managers subclass **two concrete**
pipeline-core base classes (register C-40) and override four lifecycle hooks. If a hook's
signature changes, or an inherited attribute disappears, nothing in a source scan notices
— and the first thing that does is a production FAO delivery.

**What this file checks, and what it deliberately does not.** It asserts the *contract*:
the hooks we override exist upstream with matching signatures, the classes are
instantiable, and every inherited attribute we reference resolves. It does **not**
instantiate a manager — that needs a real views-models tree and a full Appwrite
environment, so it would be a different kind of test with a different failure mode. This
is the cheap half, and the cheap half is the half that was missing.
"""

from __future__ import annotations

import ast
import inspect
import textwrap
from pathlib import Path

import pytest

from tests.conftest import PARTNER_PACKAGES

_PKG = Path(__file__).resolve().parent.parent / "views_postprocessing"

#: Inherited attributes the managers reference on `self`. Derived from the source below
#: and asserted against the real classes, so a base-class rename fails here rather than
#: at delivery time.
_INHERITED_ATTRS = ("configs", "_model_path", "_data_loader", "_initialize_data_loader")


def _manager_class(partner: str):
    """Import the partner's manager class. Requires views-pipeline-core installed."""
    pytest.importorskip(
        "views_pipeline_core",
        reason="the framework contract cannot be checked without the framework; "
        "it is a declared dependency, so this skip means a broken environment",
    )
    module = __import__(
        f"views_postprocessing.{partner}.managers", fromlist=["*"]
    )
    classes = [
        obj for name, obj in vars(module).items()
        if inspect.isclass(obj) and name.endswith("PostProcessorManager")
    ]
    assert len(classes) == 1, (
        f"expected exactly one manager class exported from {partner}/managers, "
        f"found {[c.__name__ for c in classes]}"
    )
    return classes[0]


def _overridden_hooks(partner: str) -> dict[str, ast.FunctionDef]:
    source = (_PKG / partner / "managers" / f"{partner}.py").read_text()
    cls = next(
        n for n in ast.walk(ast.parse(source))
        if isinstance(n, ast.ClassDef) and n.name.endswith("PostProcessorManager")
    )
    return {n.name: n for n in cls.body if isinstance(n, ast.FunctionDef)}


@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_every_lifecycle_hook_we_override_matches_the_base_signature(partner):
    """A Template Method subclass whose hook signature drifts is called wrong, silently.

    The framework calls these; we do not. So a base class that adds a parameter gets a
    `TypeError` at delivery time, in someone else's code, on the partner's run.
    """
    manager = _manager_class(partner)
    ours = _overridden_hooks(partner)

    checked = []
    mismatched = {}
    for name, node in ours.items():
        base = next(
            (getattr(c, name) for c in manager.__mro__[1:] if name in vars(c)), None
        )
        if base is None or not inspect.isfunction(base):
            continue  # ours alone — not an override
        expected = list(inspect.signature(base).parameters)
        actual = [a.arg for a in node.args.args]
        checked.append(name)
        if expected != actual:
            mismatched[name] = {"base": expected, "ours": actual}

    assert checked, (
        f"{partner}'s manager overrides no inherited hook — either the class stopped "
        "subclassing the framework or this check stopped finding them. Either way it is "
        "no longer verifying anything (ADR-014 §2)."
    )
    assert not mismatched, (
        f"[{partner}] lifecycle hook signatures diverged from views-pipeline-core: "
        f"{mismatched}. The framework calls these — a mismatch is a TypeError on the "
        "delivery run, not a test failure."
    )


@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_the_manager_is_instantiable_under_the_pinned_framework(partner):
    """No unimplemented abstract methods, and the MRO is the one C-40 describes.

    Not the same as "constructing one works" — that needs an environment. This catches
    the cheaper failure: a base class that grew an abstract method we do not implement,
    which makes the class uninstantiable the moment anything tries.
    """
    manager = _manager_class(partner)
    unimplemented = sorted(getattr(manager, "__abstractmethods__", frozenset()))
    assert not unimplemented, (
        f"[{partner}] {manager.__name__} cannot be instantiated under the pinned "
        f"views-pipeline-core: unimplemented abstract methods {unimplemented}. The "
        "framework added a hook this repo does not provide."
    )

    bases = [c.__name__ for c in manager.__mro__[1:3]]
    assert bases == ["PostprocessorManager", "ForecastingModelManager"], (
        f"[{partner}] the double inheritance register C-40 describes has changed: "
        f"{bases}. That entry's blast-radius argument is written against the old shape."
    )


@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_every_inherited_attribute_the_manager_uses_still_exists(partner):
    """`self.configs`, `self._model_path` and friends come from the framework.

    A rename upstream turns each into an `AttributeError` deep inside a delivery. The
    source scan that guards everything else about these files cannot see it, because the
    attribute is spelled identically whether or not it resolves.
    """
    manager = _manager_class(partner)

    def resolves(attr: str) -> bool:
        # Class attributes and methods are visible on the class...
        if any(attr in vars(c) or hasattr(c, attr) for c in manager.__mro__[1:]):
            return True
        # ...but `self._model_path = ...` in a base `__init__` is an INSTANCE attribute
        # and is not, so read the framework's own source for the assignment. A first
        # draft used `hasattr` alone and reported two live attributes as missing —
        # the guard was wrong, not the code.
        for base in manager.__mro__[1:]:
            try:
                src = inspect.getsource(base)
            except (OSError, TypeError):
                continue
            for node in ast.walk(ast.parse(textwrap.dedent(src))):
                if (
                    isinstance(node, ast.Attribute)
                    and isinstance(node.ctx, ast.Store)
                    and isinstance(node.value, ast.Name)
                    and node.value.id == "self"
                    and node.attr == attr
                ):
                    return True
        return False

    missing = [attr for attr in _INHERITED_ATTRS if not resolves(attr)]
    assert not missing, (
        f"[{partner}] inherited attribute(s) {missing} no longer exist on any base "
        "class. views-pipeline-core renamed or removed them; the manager references "
        "them by name and will raise AttributeError mid-delivery."
    )


@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_the_declared_inherited_attributes_are_the_ones_actually_used(partner):
    """Assert this guard's own inputs are real (ADR-014 §2).

    `_INHERITED_ATTRS` is hand-written and the check above trusts it. If the manager
    starts using a fifth inherited attribute and nobody adds it here, that attribute is
    unguarded — and the suite stays green, which is how every scoped guard in this
    repository has failed at least once.
    """
    source = (_PKG / partner / "managers" / f"{partner}.py").read_text()
    cls = next(
        n for n in ast.walk(ast.parse(source))
        if isinstance(n, ast.ClassDef) and n.name.endswith("PostProcessorManager")
    )
    defined = {n.name for n in cls.body if isinstance(n, ast.FunctionDef)}
    defined |= {
        t.attr for t in ast.walk(cls)
        if isinstance(t, ast.Attribute)
        and isinstance(t.value, ast.Name) and t.value.id == "self"
        and isinstance(t.ctx, ast.Store)
    }
    used = {
        t.attr for t in ast.walk(cls)
        if isinstance(t, ast.Attribute)
        and isinstance(t.value, ast.Name) and t.value.id == "self"
    }
    inherited_in_use = {a for a in used - defined if not a.startswith("__")}

    unguarded = sorted(inherited_in_use - set(_INHERITED_ATTRS))
    assert not unguarded, (
        f"[{partner}] the manager uses inherited attribute(s) {unguarded} that "
        "_INHERITED_ATTRS does not declare, so nothing checks they still exist. Add "
        "them there."
    )
