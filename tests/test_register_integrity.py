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
    sections = dict(_sections(register))
    blocks = re.split(r"^### ", sections["Open Concerns"], flags=re.M)[1:]
    missing = []
    for block in blocks:
        entry_id = block.split(":", 1)[0].strip()
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


def test_the_register_is_dated_and_governed(register):
    assert re.search(r"\| Last Updated\s+\| \d{4}-\d{2}-\d{2}", register), (
        "the header must carry an ISO Last Updated date"
    )
    assert "ADR-010" in register, "the register must name its governing ADR"
