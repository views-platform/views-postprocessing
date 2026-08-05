"""Structural guards for the technical risk register (ADR-010).

Every finding in the review-rr pass of 2026-07-31 was structural and mechanically
detectable: the header counted 25 open concerns while the file held 27, two
entries carried RESOLVED bodies but still sat under ``## Open Concerns``, and
several references pointed at IDs belonging to other repositories' registers with
no namespace to say so. None of that is a judgement call — it is exactly the
class of drift this repo already learned to mechanise, first for ADR-013
(``test_falsify_adr013_*.py``, 40 guards) and then for the þing-01 invariants
(``test_env_declaration.py``, ``test_redaction_guard.py``).

The register is a governance artifact read across four repos, so its **counts
must not lie**: a register that under-reports its own open set is worse than no
register, because it is trusted. These tests do not judge whether a concern is
real, correctly tiered, or well written — only that the document's structure
matches its own declared conventions.

Pure stdlib against the checked-in markdown; no repo imports, so it runs
anywhere the tests do.
"""

import re
from pathlib import Path

import pytest

_REGISTER = Path(__file__).resolve().parent.parent / "reports" / "technical_risk_register.md"

# Section order declared by the Register Conventions and assumed by every reader.
_EXPECTED_SECTIONS = [
    "Tier Definitions",
    "Causal Clusters",
    "Open Concerns",
    "Disagreements",
    "Resolved Concerns",
    "Resolved Disagreements",
    "Register Conventions",
]

# A heading that announces the entry is no longer an open concern.
_CLOSED_MARKERS = ("RESOLVED", "MERGED", "RELOCATED")

# Prefixes that namespace an ID to another repository's register. A reference
# without one of these must resolve to an entry in THIS file.
_FOREIGN_PREFIXES = ("views-", "pipeline-core", "faoapi", "datafactory", "frames", "models", "reporting")


@pytest.fixture(scope="module")
def register() -> str:
    assert _REGISTER.exists(), f"the register is missing: {_REGISTER}"
    return _REGISTER.read_text()


def _sections(text: str) -> list[tuple[str, str]]:
    """[(section title, section body)] in document order."""
    parts = re.split(r"^## (.+)$", text, flags=re.M)[1:]
    return list(zip(parts[::2], parts[1::2]))


def _entry_ids(body: str) -> list[str]:
    return re.findall(r"^### ([CD]-\d+)[:\s]", body, flags=re.M)


def _headings(body: str) -> list[str]:
    return re.findall(r"^### ([CD]-\d+:.*)$", body, flags=re.M)


def _open_blocks(register: str) -> list[tuple[str, str]]:
    """[(entry id, entry body)] for every concern under ``## Open Concerns``."""
    body = dict(_sections(register))["Open Concerns"]
    return [
        (block.split(":", 1)[0].strip(), block)
        for block in re.split(r"^### ", body, flags=re.M)[1:]
    ]


def _header_counts(text: str) -> dict[str, int]:
    return {
        field: int(value)
        for field, value in re.findall(
            r"\| (Total Concerns|Open Concerns|Resolved Concerns)\s+\| (\d+)", text
        )
    }


def test_header_counts_match_the_actual_entries(register):
    # The 2026-07-31 bug: header said 25/30, the file held 27/28.
    sections = dict(_sections(register))
    counts = _header_counts(register)
    assert set(counts) == {"Total Concerns", "Open Concerns", "Resolved Concerns"}, (
        "the register header must declare Total / Open / Resolved concern counts"
    )
    actual_open = len(_entry_ids(sections["Open Concerns"]))
    actual_resolved = len(_entry_ids(sections["Resolved Concerns"]))
    assert counts["Open Concerns"] == actual_open, (
        f"header says {counts['Open Concerns']} open concerns, the file holds {actual_open}"
    )
    assert counts["Resolved Concerns"] == actual_resolved, (
        f"header says {counts['Resolved Concerns']} resolved concerns, "
        f"the file holds {actual_resolved}"
    )
    assert counts["Total Concerns"] == actual_open + actual_resolved, (
        f"Total ({counts['Total Concerns']}) must equal Open + Resolved "
        f"({actual_open} + {actual_resolved})"
    )


def test_no_closed_entry_sits_under_open_concerns(register):
    # C-19 and C-45 both carried RESOLVED bodies while filed under Open for weeks.
    # Moving is physical, not annotational — see the Register Conventions.
    sections = dict(_sections(register))
    stragglers = [
        heading
        for heading in _headings(sections["Open Concerns"])
        if any(marker in heading for marker in _CLOSED_MARKERS)
    ]
    assert not stragglers, (
        "entries announcing themselves closed are still filed under '## Open Concerns' — "
        f"move them to Resolved and correct the header counts: {stragglers}"
    )


def test_section_order_is_the_declared_order(register):
    assert [title for title, _ in _sections(register)] == _EXPECTED_SECTIONS


def test_entry_ids_are_unique_across_the_register(register):
    ids = _entry_ids(register)
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    assert not duplicates, (
        "IDs are permanent and must appear exactly once — an entry listed in two "
        f"sections is the drift that breaks the counts: {duplicates}"
    )


def test_concerns_and_disagreements_are_not_filed_under_each_other(register):
    for title, body in _sections(register):
        if "Concerns" in title:
            strays = [i for i in _entry_ids(body) if i.startswith("D-")]
            assert not strays, f"disagreement(s) filed under '{title}': {strays}"
        elif "Disagreements" in title:
            strays = [i for i in _entry_ids(body) if i.startswith("C-")]
            assert not strays, f"concern(s) filed under '{title}': {strays}"


def test_every_concern_entry_declares_the_required_fields(register):
    # Open concerns carry Tier/Source/Trigger/Location; resolved ones may instead
    # carry Resolved/Resolution. Either shape is fine — silence is not.
    missing = []
    for entry_id, block in _open_blocks(register):
        for field in ("ID", "Tier", "Source", "Trigger", "Location"):
            if not re.search(rf"^\| {field} \|", block, flags=re.M):
                missing.append(f"{entry_id}: {field}")
    assert not missing, f"open concerns missing required field rows: {missing}"


def test_internal_references_resolve_and_foreign_ones_are_namespaced(register):
    """A bare `C-161` sends the reader hunting in this file for another repo's entry.

    Every ``C-nn``/``D-nn`` mention must either name an entry that exists here or
    be prefixed with the owning repository (``views-faoapi C-161``).
    """
    # The conventions section documents the rule using deliberately bare examples.
    body = register.split("## Register Conventions")[0]
    known = set(_entry_ids(register))

    # The owning repo is named *near* the reference, not necessarily as the word
    # immediately before it ("views-pipeline-core register entries C-59/C-60",
    # "faoapi's C-71"), so scan a short preceding window rather than one token.
    window = 48

    unresolved = []
    for match in re.finditer(r"\b([CD]-\d+)\b", body):
        ref = match.group(1)
        if ref in known:
            continue
        preceding = body[max(0, match.start() - window) : match.start()]
        if any(token in preceding for token in _FOREIGN_PREFIXES):
            continue
        line = body.count("\n", 0, match.start()) + 1
        unresolved.append(f"line {line}: {ref}")

    assert not unresolved, (
        "references that neither resolve to an entry in this register nor name the "
        f"repository that owns them: {unresolved}"
    )


def test_test_files_named_by_live_entries_exist_or_name_their_repo(register):
    """A live entry pointing at a test nobody can find describes work against nothing.

    Scoped to **Open Concerns and Disagreements** deliberately. A resolved entry citing
    `test_mapping.py` or `test_reconciliation_parity.py` is recording what discharged it,
    and those files are correctly gone — a blanket existence check would fire on eleven
    such mentions and be deleted within a day (ADR-014 §3). Measured before scoping:
    eleven missing across the whole register, **two** in live entries.

    The two it found on 2026-08-05 were both real, and one of them is a shape this
    register already polices for identifiers but not for paths:
    ``tests/forecast/test_wire_golden_fixture.py`` is **views-faoapi's** file. A bare
    foreign path sends the reader hunting in this repo's tree, which is exactly the
    argument `test_internal_references_resolve_and_foreign_ones_are_namespaced` makes
    about a bare ``C-161``.

    **The exemption is a declaration, not a proximity heuristic, and the first draft got
    that wrong.** It reused `_FOREIGN_PREFIXES` — the identifier-namespacing list — over a
    60-character window. That list holds ordinary English: ``models``, ``frames``,
    ``pipeline-core``. Mutation M1 planted a vanished file in a live entry and the guard
    stayed green, because the sentence three words earlier happened to say *"pinned
    pipeline-core-free"*. It had caught its two real findings by luck of their neighbours
    and would have missed most others. So the owning repo must now be named **immediately
    before the path**, in the possessive form a reader would write anyway.
    """
    body = register.split("## Register Conventions")[0]
    live = body[body.index("## Open Concerns"):body.index("## Resolved Concerns")]

    repo = Path(__file__).resolve().parent.parent
    #: `views-faoapi's `tests/...`` — the repo abutting the path, not merely nearby.
    owned_elsewhere = re.compile(r"views-[\w-]+(?:'s)?[\s:]*$")

    unresolved = []
    for match in re.finditer(r"`(?:(tests/[\w/]+\.py)|(test_\w+\.py))`", live):
        rel = match.group(1) or f"tests/{match.group(2)}"
        if (repo / rel).exists():
            continue
        if owned_elsewhere.search(live[max(0, match.start() - 40) : match.start()]):
            continue
        line = live.count("\n", 0, match.start()) + 1
        unresolved.append(f"line ~{line} of the live sections: {rel}")

    assert not unresolved, (
        "live register entries name test files that do not exist here and do not name "
        f"the repository that owns them: {unresolved}. If the file is another repo's, "
        "say so beside it. If it is ours, it was deleted and the entry is describing "
        "work against a file nobody can open."
    )


# ── Closing conditions must not already be met (S2 / #183) ───────────────────
#
# The guards above catch a heading that SAYS it is resolved. They cannot catch an
# entry that says it is open while the thing it is waiting for has arrived — and
# that turned out to be this register's actual failure mode. Six instances in two
# days: C-63 and C-47 (open, defect fixed), C-43, C-59 and C-61 (open, each
# naming a test that existed and passed), and C-74's cousin in `test_validation.py`.
#
# The stale-OPEN direction is the safe one — nothing is claimed fixed that is not —
# but it inflates the open set with finished work, so prioritisation lies. C-43 in
# particular carried its own closing condition in its body and sat under Open with
# it met, which is what makes this mechanisable at all: the entry told us what to
# check, in writing.
#
# Deliberately narrow. Two phrasings, both unambiguous past-tense claims, and the
# path-gated one only fires when the named file actually EXISTS. A guard that
# cries wolf gets deleted — this repo already deleted one over-fragile test this
# week for exactly that reason (C-61's `-1` monkeypatch). False negatives are the
# accepted cost.
_CLOSING_CONDITION = re.compile(r"closes when\b", re.I)

#: Exact strings, and that is the point: these are CONVENTIONS the register writes
#: and this guard enforces by matching them. "Mitigation - landed" (hyphen) slips
#: through, deliberately — see the false-negatives note above.
_LANDED = "Mitigation — landed"
_PARTIAL = "Partial mitigation"

#: A backticked token is treated as a closing artifact when it looks repo-relative.
#:
#: **Executable roots only.** For a test or a script, "the file exists" is close to
#: what a closing condition means, because the suite then RUNS it — C-43's condition
#: was "committed and green", and the 18 tests are what make the second half true.
#: For `docs/` the two come apart completely: an ADR file has existed since July,
#: while the section an entry is waiting on may never have been written. Including
#: doc paths here would fire on correctly-open entries and the guard would be
#: deleted rather than fixed, which is the failure this whole check exists to avoid.
_ARTIFACT_ROOTS = ("tests/", "scripts/")


def test_no_open_entry_names_a_closing_artifact_that_already_exists(register):
    """An entry that says "closes when `tests/x.py` is committed" and finds it there.

    C-43's own words: *"C-43 closes when tests/test_gaul_lookup_fidelity.py is
    committed and green."* The file was committed, the 18 tests passed, and the
    entry stayed under Open for two days. Nothing objected, because nothing was
    asked to.
    """
    repo = _REGISTER.parent.parent
    satisfied = []
    for entry_id, block in _open_blocks(register):
        for match in _CLOSING_CONDITION.finditer(block):
            window = block[match.end() : match.end() + 300]
            for token in re.findall(r"`([^`]+)`", window):
                path = token.split("::", 1)[0].strip()
                if path.startswith(_ARTIFACT_ROOTS) and (repo / path).exists():
                    satisfied.append(f"{entry_id} -> {path}")
    assert not satisfied, (
        "open concern(s) whose own stated closing condition is already met — the "
        "named artifact exists. Move the entry to Resolved citing it, or reword "
        f"the condition to say what is actually outstanding: {sorted(set(satisfied))}"
    )


def test_no_open_entry_claims_its_mitigation_has_landed(register):
    """A recorded landed mitigation is a past-tense claim that the fix shipped.

    C-59 and C-61 both carried it, both naming tests that existed and passed, and
    both sat under Open. If a fix genuinely landed only in part, say so — the
    escape hatch is the phrase "Partial mitigation", which is itself a declaration
    rather than an ambiguity.
    """
    claimed = [
        entry_id
        for entry_id, block in _open_blocks(register)
        if _LANDED in block and _PARTIAL not in block
    ]
    assert not claimed, (
        f"open concern(s) recording a landed mitigation: {claimed}. Either move the "
        f"entry to Resolved, or write {_PARTIAL!r} and state what remains."
    )


def test_the_register_is_dated_and_governed(register):
    assert re.search(r"\| Last Updated\s+\| \d{4}-\d{2}-\d{2}", register), (
        "the header must carry an ISO Last Updated date"
    )
    assert "ADR-010" in register, "the register must name its governing ADR"
