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

import re
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_PKG = _REPO / "views_postprocessing"

# --- 1. deleted-symbol scan -------------------------------------------------------------

# Symbols that name code removed in ADR-011 / C-39. None should appear as *current* in a
# living onboarding doc.
_BANNED = re.compile(
    r"PriogridCountryMapper|mapping/README|use_disk_cache|cachetools|geopandas",
    re.IGNORECASE,
)


def _living_docs() -> list[Path]:
    """The onboarding surface that must stay current."""
    docs = [_REPO / "README.md"]
    docs += sorted((_REPO / "docs" / "architecture").glob("*.md"))
    docs += sorted((_REPO / "views_postprocessing").rglob("README.md"))
    return [d for d in docs if d.exists()]


def test_living_docs_have_no_deleted_symbol_references():
    offenders = []
    for doc in _living_docs():
        for i, line in enumerate(doc.read_text().splitlines(), start=1):
            if "legacy-ok" in line:  # explicit opt-out for an intentional historical mention
                continue
            if _BANNED.search(line):
                offenders.append(f"{doc.relative_to(_REPO)}:{i}: {line.strip()}")
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

_MANAGER = _PKG / "unfao" / "managers" / "unfao.py"
_MANAGER_LINE_BUDGET = 450  # epic #148's bound; 406 at close, 636 before #149


def test_pandas_has_exactly_one_importer():
    """ADR-012's 'Representation Seam' row says pandas is isolated to one module."""
    importers = sorted(
        f.relative_to(_PKG).as_posix()
        for f in _PKG.rglob("*.py")
        if re.search(r"^\s*(?:import pandas|from pandas\b)", f.read_text(), re.M)
    )
    assert importers == ["contract/enrichment.py"], (
        f"ADR-012 claims one pandas-aware module; found {importers}. Either the claim "
        "or the code moved — fix whichever is wrong, do not leave the ADR lying."
    )


def test_views_pipeline_core_has_exactly_one_importer():
    """ADR-012's 'Pipeline Manager' row, and C-40's blast-radius claim.

    This property is what makes the C-40 de-inheritance a bounded job rather than an
    open-ended one. If it spreads, that entry's scope changes and its narrative is wrong.
    """
    importers = sorted(
        f.relative_to(_PKG).as_posix()
        for f in _PKG.rglob("*.py")
        if "views_pipeline_core" in f.read_text()
    )
    assert importers == ["unfao/managers/unfao.py"], (
        f"views_pipeline_core is imported by {importers}. ADR-012 and register C-40 both "
        "state it is one file wide; a second importer widens C-40's blast radius."
    )


def test_the_manager_stays_within_its_line_budget():
    """ADR-012 no longer calls the manager 'thin' — it states a number. Hold it."""
    lines = len(_MANAGER.read_text().splitlines())
    assert lines <= _MANAGER_LINE_BUDGET, (
        f"the manager is {lines} lines, over epic #148's {_MANAGER_LINE_BUDGET} bound. "
        "It was 636 before #149 and is the repo's one known dumping ground — growth "
        "here is the regression that epic existed to reverse."
    )


def test_contract_package_does_not_import_the_partner():
    """The dependency direction ADR-002 declares: unfao/ -> contract/ -> delivery/."""
    offenders = [
        f.relative_to(_PKG).as_posix()
        for f in (_PKG / "contract").rglob("*.py")
        if re.search(r"^\s*(?:from|import)\s+views_postprocessing\.unfao", f.read_text(), re.M)
    ]
    assert not offenders, (
        f"contract/ imports the partner package: {offenders}. The machinery must be "
        "reusable by views-crafdapi / views-productionapi without taking FAO (C-69)."
    )


# --- 3. retired cross-repo contract name (S3 / #184, finishing #158) --------------------

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
