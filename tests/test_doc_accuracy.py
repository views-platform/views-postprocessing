"""Doc-accuracy guardrail (epic #70 / S6).

The orientation docs went stale silently because nothing checked them against the code.
These tests keep the *living onboarding docs* honest:

1. they must not reference deleted symbols (the removed runtime mapper / shapefiles /
   caching) as if they were current;
2. their internal relative links must resolve.

Scope note: ADRs, CICs, and the historical reports (the falsification campaign, the
cross-repo report, the ADR-011 assessment) legitimately reference superseded designs as a
*record* — they are excluded from the deleted-symbol scan but still link-checked. A single
intentional historical mention in a living doc can be whitelisted with an inline
``legacy-ok`` marker on that line.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from tests.conftest import PARTNER_PACKAGES as _PARTNER_PACKAGES

_REPO = Path(__file__).resolve().parent.parent
_PKG = _REPO / "views_postprocessing"

# --- 1. deleted-symbol scan -------------------------------------------------------------

# Symbols naming code this repo has deleted. None should appear as *current* in a living
# onboarding doc.
#
# **This list must grow with every deletion, and that is the lesson of S11 (#197).** It
# carried only the ADR-011 / C-39 entries for six weeks while epic #148 deleted a whole
# delivery path (#149) and moved the machinery out of `unfao/` (#153). The guard kept
# passing over four documents describing methods and files that no longer existed —
# including `unfao/managers/README.md`, which documented the Template Method as
# `_transform → _append_metadata` and pointed readers at a deleted test file, sitting
# inside the package next to the code it misdescribed.
#
# The guard was not wrong. It was not updated. A deletion PR that does not extend this
# regex has not finished.
_BANNED = re.compile(
    "|".join((
        # ADR-011 / C-39 — the runtime mapper and its shapefile toolchain (June 2026)
        r"PriogridCountryMapper", r"mapping/README", r"use_disk_cache", r"cachetools",
        r"geopandas",
        # #149 — methods of the retired pandas delivery path (2026-07-31)
        r"_append_metadata", r"_delivery_description", r"_clip_observed_history",
        r"LEGACY_FORECAST_FILTERS", r"test_append_metadata",
        # #150 / #151 / #153 — modules retired or moved out of `unfao/` by epic #148
        r"delivery/identity", r"unfao/extraction", r"unfao/frames",
        r"unfao/historical", r"unfao/gaul_schema", r"unfao/wire",
        # #149 — pipeline-core's pandas container, no longer referenced by this repo.
        # Negative lookbehind: `FAO_PGMDataset` is views-faoapi's class and is live.
        # It inherits IGNORECASE, so `fao_PGMDataset` is spared too — no such spelling
        # exists, but the lookbehind is not case-exact and a reader should not assume it.
        r"(?<!FAO_)PGMDataset",
    )),
    re.IGNORECASE,
)


def _living_docs() -> list[Path]:
    """The onboarding surface that must stay current."""
    docs = [_REPO / "README.md"]
    docs += sorted((_REPO / "docs" / "architecture").glob("*.md"))
    docs += sorted((_REPO / "views_postprocessing").rglob("README.md"))
    return [d for d in docs if d.exists()]


def _label(doc: Path) -> str:
    """Repo-relative path where possible — three living docs are named ``README.md``,
    so a bare basename cannot say which one failed."""
    try:
        return doc.relative_to(_REPO).as_posix()
    except ValueError:
        return doc.name  # a doc injected from tmp_path by the guard's own tests


def _deleted_symbol_offenders(docs: list[Path]) -> list[str]:
    """Scan ``docs`` for banned symbols, honouring the line-scoped ``legacy-ok`` opt-out."""
    offenders = []
    for doc in docs:
        for i, line in enumerate(doc.read_text().splitlines(), start=1):
            if "legacy-ok" in line:  # explicit opt-out for an intentional historical mention
                continue
            if _BANNED.search(line):
                offenders.append(f"{_label(doc)}:{i}: {line.strip()}")
    return offenders


def test_living_docs_have_no_deleted_symbol_references():
    offenders = _deleted_symbol_offenders(_living_docs())
    assert not offenders, "deleted-symbol references in living docs:\n" + "\n".join(offenders)


# --- 2. internal link resolution --------------------------------------------------------

# [text](target) — capture the target; we filter out external/anchor links below.
_LINK = re.compile(r"\]\(([^)]+)\)")


def _link_checked_docs() -> list[Path]:
    """Every markdown doc whose internal links should resolve."""
    docs = [_REPO / "README.md"]
    docs += sorted((_REPO / "docs").rglob("*.md"))
    docs += sorted((_REPO / "views_postprocessing").rglob("README.md"))
    # de-dup while preserving order
    seen: set[Path] = set()
    out = []
    for d in docs:
        if d.exists() and d not in seen:
            seen.add(d)
            out.append(d)
    return out


def test_internal_doc_links_resolve():
    dead = []
    for doc in _link_checked_docs():
        for target in _LINK.findall(doc.read_text()):
            target = target.strip()
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path_part = target.split("#", 1)[0]  # strip any anchor fragment
            if not path_part:
                continue
            if not (doc.parent / path_part).exists():
                dead.append(f"{doc.relative_to(_REPO)} -> {target}")
    assert not dead, "dead internal doc links:\n" + "\n".join(dead)


# ── the ontology's load-bearing claims are checked, not asserted (C-67, #154) ──
#
# ADR-012 twice described an intended end state as if it were the code: it called the
# manager "thin" at 636 lines, and called extraction.py "the single pandas-aware
# module" while pandas lived in three. Both drifted the same way and neither was
# caught by reading. These make the claims fail CI instead.

#: Every partner's manager directory, derived from the one declared partner list.
#:
#: **This was a hardcoded 2-tuple until 2026-08-03 and it was the last such list in the
#: suite.** Fifteen guards parametrise over ``PARTNER_PACKAGES``; this one did not, so a
#: third partner with a **906-line** manager passed the budget while failing everything
#: else — and nothing in those failures named the list it was missing from. That is
#: register C-57's shape surviving inside the file that documents C-57's fix.
_MANAGER_DIRS = tuple((_PKG / p / "managers") for p in _PARTNER_PACKAGES)

#: epic #148's bound; 406 at close, 636 before #149. Applied to the manager *directory*,
#: not the manager file: an 800-line helper module beside a 406-line manager was
#: previously unbudgeted, which is the same regrowth wearing a different filename.
_MANAGER_LINE_BUDGET = 450


def _is_type_checking(test: ast.expr) -> bool:
    """`TYPE_CHECKING` or `typing.TYPE_CHECKING`, and nothing else.

    Substring-matching `ast.dump(test)` also matched `not TYPE_CHECKING`, which means
    the opposite. Polarity is the whole point of a guard.
    """
    if isinstance(test, ast.Name):
        return test.id == "TYPE_CHECKING"
    return isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"


def _classify_pandas_imports(source: str) -> list[tuple[str, ast.AST]]:
    """``[("runtime" | "type-only", node)]`` for every pandas import in ``source``.

    **Module-level on purpose.** Both the guard and the test that proves the guard
    bites call THIS function. An earlier draft had the meta-test define its own copy
    of this logic — so it asserted against a replica, and when the polarity bug was
    reintroduced into the real guard, all 16 tests still passed. That is the exact
    defect S4 of epic #181 retired from ``test_validation.py`` (43 tests against a
    function the file defined itself), committed again in the pull request whose
    message boasts about catching its cousin. One implementation, two callers.
    """
    tree = ast.parse(source)
    # BODY only, never `orelse`. Walking the whole `If` node classified a real runtime
    # `import pandas` sitting in the `else:` branch as type-only — the guard passed on
    # the exact thing it exists to catch. Reproduced before fixing.
    guarded = {
        id(n)
        for node in ast.walk(tree)
        if isinstance(node, ast.If) and _is_type_checking(node.test)
        for stmt in node.body
        for n in ast.walk(stmt)
    }
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        names = [getattr(node, "module", None) or a.name for a in node.names]
        if any((n or "").split(".")[0] == "pandas" for n in names):
            out.append(("type-only" if id(node) in guarded else "runtime", node))
    return out


def test_pandas_is_not_imported_at_runtime_anywhere_in_the_package():
    """ADR-012's 'Representation Seam' row — now a stronger claim than it was.

    It used to be *one* pandas-aware module (``contract/enrichment.py``). After S4
    (#89) that module's lookup side is numpy + pyarrow and its pandas import is
    **type-only**, under ``if TYPE_CHECKING``: pandas is in the enricher's interface
    (callers hand it DataFrames) but no longer in its implementation.

    So the assertion is now *zero runtime importers*, and it is checked by **AST**
    rather than by regex — a regex matching an indented ``import pandas`` cannot tell a
    real import from one inside a ``TYPE_CHECKING`` guard, and would have passed
    unchanged while the meaningful property changed underneath it.
    """
    runtime, type_only = [], []
    for source in sorted(_PKG.rglob("*.py")):
        for kind, node in _classify_pandas_imports(source.read_text()):
            # The FILE is the claim; the line number is not. Pinning a line means any
            # edit above it fails a test about imports, which is how a guard earns a
            # reputation for crying wolf (ADR-014 §3).
            where = source.relative_to(_PKG).as_posix()
            (type_only if kind == "type-only" else runtime).append(where)

    assert not runtime, (
        f"pandas is imported at RUNTIME in the package: {runtime}. The delivery path "
        "is numpy/pyarrow end to end (epic #85); a runtime pandas import re-materialises "
        "the representation the migration removed. If it is genuinely needed, put it "
        "behind `if TYPE_CHECKING` or say in ADR-012 why it is not."
    )
    assert type_only == ["contract/enrichment.py"], (
        f"the type-only pandas imports moved: {type_only}. Not necessarily wrong — but "
        "ADR-012 names the seam, so update it rather than letting the claim drift."
    )


def test_views_pipeline_core_is_confined_to_the_partner_managers():
    """ADR-012's 'Pipeline Manager' row, and C-40's blast-radius claim.

    This property is what makes the C-40 de-inheritance a bounded job rather than an
    open-ended one. If it spreads, that entry's scope changes and its narrative is wrong.
    """
    importers = sorted(
        f.relative_to(_PKG).as_posix()
        for f in _PKG.rglob("*.py")
        if "views_pipeline_core" in f.read_text()
    )
    assert importers == ["crafd/managers/crafd.py", "unfao/managers/unfao.py"], (
        f"views_pipeline_core is imported by {importers}. ADR-012 and register C-40 state it "
        "is confined to the per-partner manager seam — one file per delivery (unfao, crafd). "
        "An importer OUTSIDE those managers widens C-40's blast radius; a new partner manager "
        "is expected and joins this list."
    )


@pytest.mark.parametrize("managers_dir", _MANAGER_DIRS, ids=lambda p: p.parent.name)
def test_the_manager_stays_within_its_line_budget(managers_dir):
    """ADR-012 no longer calls the manager 'thin' — it states a number. Hold it.

    Counts every ``.py`` under the partner's ``managers/`` directory. The bound is on
    the *seam*, and a seam that stays at 406 lines by moving 800 into a sibling module
    has not stayed anywhere.
    """
    assert managers_dir.is_dir(), (
        f"no managers/ directory at {managers_dir.relative_to(_PKG.parent)}. A budget "
        "over a path that stopped existing counts nothing and reports success."
    )
    sources = sorted(managers_dir.rglob("*.py"))
    lines = sum(len(f.read_text().splitlines()) for f in sources)
    assert lines <= _MANAGER_LINE_BUDGET, (
        f"{managers_dir.parent.name}'s managers/ is {lines} lines across "
        f"{[f.name for f in sources]}, over epic #148's {_MANAGER_LINE_BUDGET} bound. "
        "It was 636 before #149 and is the repo's one known dumping ground — growth "
        "here is the regression that epic existed to reverse."
    )


def _imported_subpackages(source: str, module_path: Path) -> set[str]:
    """Every ``views_postprocessing.<X>`` this module imports — all four spellings.

    **Regexes were tried twice here and escaped twice.** A pattern that matched
    ``from views_postprocessing.contract import x`` missed ``from ..contract import x``;
    widened for that, it still missed ``from views_postprocessing import contract``,
    because the optional ``views_postprocessing.`` group requires the dot. Both are
    ordinary module-level imports. A third spelling, ``import views_postprocessing.x``,
    needed its own alternative. Meanwhile the pattern fired on a docstring that merely
    *spelled* a forbidden import — cry-wolf on prose while missing real code, which is
    the worst of both (ADR-014 §2, §3).

    The AST knows what an import is. It resolves relative levels, sees the bare
    ``from package import subpackage`` form as what it is, and cannot see prose at all.
    This module already had the pattern twice (``_classify_pandas_imports``,
    and ``_dotenv_use`` in ``test_env_declaration.py``); the import guards simply had
    not caught up.
    """
    parts = module_path.relative_to(_PKG).with_suffix("").as_posix().split("/")
    package = ["views_postprocessing"] + parts[:-1]  # the module's own package

    found: set[str] = set()

    def record(dotted: str) -> None:
        bits = dotted.split(".")
        if len(bits) >= 2 and bits[0] == "views_postprocessing":
            found.add(bits[1])

    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                record(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package[: len(package) - (node.level - 1)]
                resolved = ".".join(base + ([node.module] if node.module else []))
            else:
                resolved = node.module or ""
            record(resolved)
            # `from <pkg> import <subpackage>` — the imported NAME is the subpackage.
            for alias in node.names:
                record(f"{resolved}.{alias.name}")
    return found


def test_the_invariants_do_not_import_the_machinery():
    """The lower leg of ADR-002's chain: ``<partner>/ -> contract/ -> delivery/``.

    ``delivery/`` is the bottom of the stack and must stay usable on its own — that is
    what makes the invariants *representation-free* rather than merely
    representation-light. Its module-level counterpart is
    ``test_clone_readiness.py::test_the_invariants_import_without_the_machinery``, which
    proves the same thing in a fresh interpreter; this one also sees imports hidden
    inside function bodies, which a subprocess never executes.

    **Written 2026-08-03 because the claim existed without it.** ADR-012 said the
    one-way dependency was "enforced by test, not convention"; only the
    partner-to-machinery leg was.
    """
    forbidden = {"contract", *_PARTNER_PACKAGES}
    offenders = [
        f"{f.relative_to(_PKG).as_posix()} -> views_postprocessing.{name}"
        for f in (_PKG / "delivery").rglob("*.py")
        for name in sorted(_imported_subpackages(f.read_text(), f) & forbidden)
    ]
    assert not offenders, (
        f"delivery/ imports upward: {offenders}. The invariants sit below the machinery "
        "and must stay usable without it — that is what makes them representation-free "
        "rather than merely representation-light (ADR-002, ADR-012)."
    )


def test_contract_package_does_not_import_any_partner():
    """The upper leg of ADR-002's chain, and register C-69's fix made permanent.

    Scoped to the declared partner list rather than to ``unfao`` by name: the
    single-name version passed while ``contract/`` was free to import ``crafd``, proven
    by adding that import and watching the suite stay green.

    Uses the same AST walk as its sibling above, for the same reason — the regex here
    was absolute-only, so ``from ..unfao import product`` inside a function body was
    invisible to it *and* to the subprocess check, which never executes a function body.
    """
    offenders = [
        f"{f.relative_to(_PKG).as_posix()} -> views_postprocessing.{name}"
        for f in (_PKG / "contract").rglob("*.py")
        for name in sorted(_imported_subpackages(f.read_text(), f) & set(_PARTNER_PACKAGES))
    ]
    assert not offenders, (
        f"contract/ imports a partner package: {offenders}. The machinery must be "
        "reusable by the next partner without taking this one's product (C-69)."
    )


#: Retired 2026-07-31. The registry itself records the retirement:
#: ``former_contract_name = "PLATFORM-001"   # retired 2026-07-31``.
_RETIRED_CONTRACT_NAME = "PLATFORM-001"


def test_the_retired_contract_name_is_gone_from_code():
    """A citation naming a contract that no longer exists sends the reader nowhere.

    #158 renamed ``PLATFORM-001`` to *the Appwrite Seam Contract* and was closed on
    2026-08-01 — but only the documentation half landed. Four references survived in
    ``.py``, and one of them was **inside the message raised by
    ``appwrite_env.assert_env_declared``**: the text an operator reads when a delivery
    refuses to launch, pointing them at a retired name in a repo they do not own, on
    the day their run failed.

    "Code" means all three roots that hold Python here — the package, the tests, and
    ``scripts/`` (which builds the committed GAUL artifact and the §10 golden fixture).
    Scanning fewer roots than the name claims is register **C-74**'s defect, found the
    same day this test was written: a guard whose declared scope exceeds its actual
    scan passes because the unscanned part happens to be clean.

    ``docs/ADRs/`` and ``reports/`` are deliberately excluded. They legitimately use
    the old name when narrating what was decided under it — an ADR describing a 2026-07
    decision correctly says what the thing was called in 2026-07. Code has no such
    excuse: it speaks in the present tense to whoever is reading it now.
    """
    offenders = []
    roots = (_PKG, _REPO / "tests", _REPO / "scripts")
    for source in sorted(f for root in roots for f in root.rglob("*.py")):
        if source.resolve() == Path(__file__).resolve():
            continue  # this file names it in order to ban it
        for number, line in enumerate(source.read_text().splitlines(), 1):
            if _RETIRED_CONTRACT_NAME in line:
                offenders.append(f"{source.relative_to(_REPO)}:{number}")
    assert not offenders, (
        f"{_RETIRED_CONTRACT_NAME!r} was retired on 2026-07-31 and must not appear in "
        f"code: {offenders}. Use 'the Appwrite Seam Contract' and cite the registry by "
        "pinned URL (views-appwrite/docs/ADRs/platform/coordinate_registry.toml). "
        "Historical narration belongs in docs/ADRs or reports/, not here."
    )


def test_the_ban_covers_the_post_148_deletions_and_spares_the_live_lookalike():
    """A ban list that was not updated when the code changed is why S11 (#197) existed.

    Two failure modes, both real, so both are pinned:

    1. **Entries going missing** — someone trims the list and a document quietly starts
       describing deleted code again. The loop below fails if any known entry stops
       matching. Note what it *cannot* catch: a future deletion whose symbol nobody adds
       is invisible to this test and to the guard alike, which is why the comment above
       ``_BANNED`` says a deletion PR that does not extend it has not finished. No test
       can substitute for that; only the habit can.
    2. **Too broad** — `FAO_PGMDataset` is a *views-faoapi* class, alive and correctly
       cited in `contract/gaul_schema.py` and `contract/enrichment.py`. A careless
       `PGMDataset` pattern would ban a true statement about another repo's code.
    """
    for deleted in (
        "_append_metadata", "_delivery_description", "_clip_observed_history",
        "LEGACY_FORECAST_FILTERS", "tests/test_append_metadata.py",
        "delivery/identity.py", "unfao/extraction.py", "unfao/frames.py",
        "unfao/historical.py", "unfao/gaul_schema.py", "unfao/wire/sink.py",
        "PGMDataset", "PriogridCountryMapper", "geopandas",
    ):
        assert _BANNED.search(deleted), (
            f"{deleted!r} names code this repo deleted, but the ban list does not cover "
            "it — a living doc could describe it as current and nothing would object"
        )

    assert not _BANNED.search("FAO_PGMDataset._METADATA_COLS"), (
        "the ban caught `FAO_PGMDataset`, which is views-faoapi's live class and the "
        "consumer contract our sidecar is written against — banning a true statement "
        "about another repo's code is how a guard earns its own deletion"
    )


def test_the_ban_actually_fires_on_a_living_doc(tmp_path):
    """The scan, not just the regex — a pattern nothing applies is decoration."""
    doc = tmp_path / "README.md"
    doc.write_text("The manager joins metadata in `_append_metadata`.\n")
    assert _deleted_symbol_offenders([doc]), (
        "the scan reported nothing on a doc naming a deleted method"
    )


def test_the_legacy_ok_marker_still_works(tmp_path):
    """The escape hatch the retirement records depend on — line-scoped, deliberately.

    Four documents now name deleted methods in order to say where the work went. That is
    better than a gap, and it only stays possible while this marker keeps working. It is
    line-scoped: a marker on the following line does not excuse the mention above it.
    """
    excused = tmp_path / "ok.md"
    excused.write_text("`_append_metadata` was retired in #149. <!-- legacy-ok: retirement record -->\n")
    assert not _deleted_symbol_offenders([excused])

    wrong_line = tmp_path / "wrong.md"
    wrong_line.write_text("`_append_metadata` was retired.\n<!-- legacy-ok -->\n")
    assert _deleted_symbol_offenders([wrong_line]), (
        "a marker on the NEXT line excused the mention — the opt-out must stay line-scoped, "
        "or a single marker silently covers a whole document"
    )


# --- 4. the post-delivery correction procedure (S8 / #189, register C-22) ---------------

_CORRECTION = _REPO / "docs" / "operations" / "correction_procedure.md"


def test_the_correction_procedure_exists_and_names_how_to_identify_a_delivery():
    """C-22's trigger fired on 2026-07-27 and there was no written procedure.

    Run-0 put 64,742 cells x 36 months into a partner's store, live. The procedure
    that existed (#15, June) described disk caches and shapefiles — both deleted with
    the runtime mapper. This pins the two things a correction cannot start without:
    the fields that say *which* delivery is affected.

    Mirrors ``test_clone_readiness.py::test_the_cloning_guide_exists_and_names_what_
    must_be_supplied`` — the human half of a guarantee, checked mechanically.
    """
    assert _CORRECTION.exists(), f"the correction procedure is missing: {_CORRECTION}"
    text = _CORRECTION.read_text()
    for required in ("run_id", "lookup_version", "manifest"):
        assert required in text, (
            f"the correction procedure does not mention {required!r} — without it a "
            "reader cannot establish which deliveries are affected before acting"
        )


def test_the_correction_procedure_describes_the_delivery_that_exists():
    """It must not describe the pre-#149 pipeline, which is how #15 became useless.

    ``_BANNED`` already covers the deleted symbols; this asserts the *positive* — that
    the document names the ADR-013 mechanisms a correction actually runs through.
    """
    text = _CORRECTION.read_text()
    offenders = [
        line.strip()
        for line in text.splitlines()
        if "legacy-ok" not in line and _BANNED.search(line)
    ]
    assert not offenders, f"the correction procedure describes deleted code: {offenders}"
    for mechanism in ("supersed", "commit marker", "source_selection", "C-73"):
        assert mechanism in text, (
            f"the procedure does not mention {mechanism!r}. A correction that ignores "
            "how the consumer SELECTS a run will publish a fix nobody picks up."
        )


def test_the_procedure_names_who_notifies_and_still_flags_what_fao_has_not_answered():
    """Half of §4 is decided; half is not, and both halves must stay visible.

    **Decided 2026-08-02 (operator):** Simon Polichinel von der Maase makes contact, and
    the intended treatment of a bad delivery is *withdrawal*. **Not decided:** whether
    FAO agrees the recipients and timing (B.1), and whether they have an audit
    requirement arguing against withdrawal (B.2). Both are put to them in Pre-Release
    Note 07, Topic B.

    An earlier version of this test asserted the document said "not decided", and its
    docstring instructed whoever removed that marker to replace it with the decision.
    That is what happened — the guard fired on the operator's answer, which is the
    behaviour it was written for rather than a false positive.

    The failure mode it now guards is subtler: a half-answered question quietly becoming
    a whole answer, so the outstanding half stops being asked.
    """
    text = _CORRECTION.read_text()
    assert "Simon Polichinel von der Maase is responsible" in text, (
        "the procedure no longer names who contacts the partner — an unowned step is "
        "improvised by whoever notices, under time pressure"
    )
    assert "Still awaiting FAO's answer" in text, (
        "the procedure no longer flags what FAO has not answered. If they have "
        "answered, record the answer and the date — do not simply drop the question."
    )
    assert "Pre-Release Note 07" in text, (
        "the procedure must cite where the outstanding questions were put, or they "
        "become questions nobody remembers asking"
    )


def test_the_procedure_distinguishes_intended_policy_from_what_is_implemented():
    """The gap that would otherwise be discovered mid-incident.

    Withdrawal is the decision; supersession is what the wire actually does, and it is
    in force only because nothing else exists. An operator reading this at 22:00 must
    not believe a bad delivery becomes unretrievable when it does not.
    """
    text = _CORRECTION.read_text()
    assert "intended policy is WITHDRAWAL" in text.replace("**", "")
    assert "implemented is SUPERSESSION" in text.replace("**", "")
    assert "ADR-013 amendment" in text, (
        "the procedure must say what withdrawal would COST — otherwise the gap reads "
        "as an oversight rather than as unbuilt work with a known price"
    )


def test_no_partner_contact_details_are_published_in_this_repository():
    """This repo is public. FAO staff email addresses do not belong in it.

    The contacts live in the FAO-02 project materials and the operator's address book.
    Naming a responsible person on our side is fine; publishing an external
    organisation's individual addresses to a public repository is not something to do
    as a side effect of documenting a runbook.
    """
    offenders = []
    for doc in (*sorted(_REPO.rglob("*.md")), *sorted(_PKG.rglob("*.py"))):
        if ".git" in doc.parts:
            continue
        for number, line in enumerate(doc.read_text(errors="ignore").splitlines(), 1):
            if "@fao.org" in line.lower():
                offenders.append(f"{doc.relative_to(_REPO)}:{number}")
    assert not offenders, (
        f"partner contact addresses appear in this public repository: {offenders}. "
        "Keep them in the project materials; reference the decision, not the address."
    )


def test_the_runtime_import_guard_catches_both_ways_of_evading_it():
    """A guard that cannot fail is decoration (ADR-014 §2) — and this one could not.

    Its first draft walked the whole ``if TYPE_CHECKING`` node and substring-matched
    ``ast.dump(test)``. Two evasions passed it, both reproduced before the fix:

    - a real runtime ``import pandas`` in the ``else:`` branch (walked as if guarded);
    - ``if not TYPE_CHECKING:`` (substring match ignores polarity, which is the entire
      point of a guard).

    **And the first draft of THIS test could not have caught either**, because it
    defined its own copy of the classifier and asserted against that. Reintroducing
    the polarity bug into the real guard left all 16 tests green. It now calls
    ``_classify_pandas_imports`` — the same function the guard calls — so a regression
    there fails both.
    """
    def kinds(src: str) -> list[str]:
        return [kind for kind, _ in _classify_pandas_imports(src)]

    assert kinds(
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    pass\nelse:\n    import pandas\n"
    ) == ["runtime"], "an import in the else: branch was classified type-only"

    assert kinds(
        "from typing import TYPE_CHECKING\nif not TYPE_CHECKING:\n    import pandas\n"
    ) == ["runtime"], "`not TYPE_CHECKING` was treated as a type-checking guard"

    assert kinds(
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import pandas\n"
    ) == ["type-only"], "a legitimate type-only import was flagged — the guard cries wolf"
