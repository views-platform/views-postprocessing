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


def test_the_procedure_states_the_questions_only_the_operator_can_answer():
    """The two external-party decisions must stay visible, not quietly become defaults.

    Who contacts the UN FAO, and whether they expect retraction or supersession. Per
    CLAUDE.md both are the operator's; the failure mode is that an undecided step gets
    silently improvised the first time it is needed, under time pressure.
    """
    text = _CORRECTION.read_text()
    assert "not decided" in text.lower(), (
        "the procedure no longer flags its undecided step — if it has been decided, "
        "replace the marker with the decision and say who made it"
    )
    assert "UN FAO" in text and "supersede" in text
