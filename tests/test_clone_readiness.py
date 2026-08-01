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
everything would still work *for FAO*. It would only break for views-crafdapi and
views-productionapi, in a repository nobody had cut yet. Register C-69's fix is
one-shot; this is what makes it hold.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent

#: Every partner-neutral module a clone is expected to reuse as-is.
_MACHINERY = (
    "views_postprocessing.delivery.coverage",
    "views_postprocessing.delivery.draws",
    "views_postprocessing.delivery.parity",
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


def _import_in_subprocess(modules: tuple[str, ...], forbidden_prefix: str) -> subprocess.CompletedProcess:
    """Import ``modules`` in a fresh interpreter; report any ``forbidden_prefix`` arrivals."""
    script = textwrap.dedent(f"""
        import sys
        for name in {list(modules)!r}:
            __import__(name)
        leaked = sorted(m for m in sys.modules if m.startswith({forbidden_prefix!r}))
        print("LEAKED:" + ",".join(leaked))
    """)
    return subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, cwd=_REPO, timeout=120,
    )


def test_the_machinery_imports_without_the_partner():
    """The load-bearing assertion of the whole epic.

    A clone must be able to take `delivery/` and `contract/` and get a working
    ADR-013 delivery without inheriting FAO's product, FAO's store coordinates, or
    FAO's manager.
    """
    result = _import_in_subprocess(_MACHINERY, "views_postprocessing.unfao")
    assert result.returncode == 0, (
        f"the machinery failed to import on its own:\n{result.stderr}"
    )
    leaked = [m for m in result.stdout.split("LEAKED:")[-1].strip().split(",") if m]
    assert not leaked, (
        f"importing the partner-neutral machinery pulled in the partner: {leaked}. "
        "A clone (views-crafdapi, views-productionapi) would inherit FAO's product "
        "through this path — see register C-69 and views_postprocessing/contract/__init__.py."
    )


def test_the_machinery_does_not_pull_in_pipeline_core():
    """`views_pipeline_core` is imported by exactly one module — the manager.

    Pinned while it is true. A clone writes its own manager against its own
    framework seam; if the machinery started dragging pipeline-core in, that choice
    would be made for it, and register C-40's blast radius would widen from one file
    to the whole package.

    ADR-013 §11.4-adjacent: þing-02 **S24(5)** makes this binding for the clone — it
    must not import `views_pipeline_core.modules.{appwrite,datastore}`, because this
    repo's own import of those is how a two-repo defect became three.
    """
    result = _import_in_subprocess(_MACHINERY, "views_pipeline_core")
    assert result.returncode == 0, result.stderr
    leaked = [m for m in result.stdout.split("LEAKED:")[-1].strip().split(",") if m]
    assert not leaked, (
        f"the machinery pulled in views_pipeline_core: {leaked}. It is imported by "
        "exactly one module (the manager) and that is what keeps C-40 bounded."
    )


def test_the_guard_would_actually_catch_a_violation():
    """A purity test that cannot fail is decoration.

    Imports the *partner* deliberately and asserts the detector sees it — so a future
    reader knows the two tests above are load-bearing rather than vacuously passing
    because the subprocess silently did nothing.
    """
    result = _import_in_subprocess(
        ("views_postprocessing.unfao.product",), "views_postprocessing.unfao"
    )
    assert result.returncode == 0, result.stderr
    leaked = [m for m in result.stdout.split("LEAKED:")[-1].strip().split(",") if m]
    assert leaked, "the detector reported nothing while importing the partner directly"


@pytest.mark.parametrize("doc", ["docs/CLONING.md"])
def test_the_cloning_guide_exists_and_names_what_must_be_supplied(doc):
    """The guide is the human half of this proof; the tests are the machine half."""
    text = (_REPO / doc).read_text()
    for required in ("product", "appwrite_env", "manager", "views_pipeline_core"):
        assert required in text, f"docs/CLONING.md does not mention {required!r}"
