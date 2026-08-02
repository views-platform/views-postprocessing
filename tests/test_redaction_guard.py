"""Guards born from the þing-01 delivery-log/provenance redaction audit (#135,
orð_09 §3 commitment; the Appwrite Seam Contract's multi-carrier redaction clause).

The audit (2026-07-28) found the delivery clean: no credential in any carrier —
log lines carry filenames/run_ids/counts/regions, and the provenance description
(the one carrier that leaves the machine, into the store's metadata) is a closed
set of delivery primitives. Each test pins one of those audited facts permanently
so drift fails loud instead of leaking quietly.
"""

import json
from pathlib import Path

from views_postprocessing.delivery import provenance


_PKG = Path(__file__).resolve().parent.parent / "views_postprocessing"

# The delivery-path modules the audit certified credential-blind: they never read
# the environment and never see a key (the manager's DIP port hands them data
# only). A hit here means a credential VALUE could newly reach a delivery log
# line or artifact — re-run the #135 audit before allowing it.
#
# **These paths moved and this list did not** (register C-74, S10 / #192). Epic
# #148's #153 relocated the machinery from ``unfao/`` to ``contract/``; four of the
# five roots below kept pointing at ``unfao/`` and the guard went on passing while
# scanning **6 files instead of 16**. It was not wrong; it was not updated.
#
# Written out as an explicit list rather than derived from the package tree —
# deliberately. ``tests/test_clone_readiness.py`` enumerates an overlapping set for
# a *different* question ("does the machinery import without the partner?"), and
# folding them together would couple two guards whose sets are free to diverge:
# a new module can be partner-neutral without being credential-blind. Two lists
# that each say what they mean beat one that means neither.
#
# What makes the explicit list safe is the root-existence assertion below. That is
# the half that fixes the *class* rather than today's instance.
_CREDENTIAL_BLIND = [
    _PKG / "contract" / "wire",
    _PKG / "delivery",
    _PKG / "contract" / "historical.py",
    _PKG / "contract" / "track_a_source.py",
    _PKG / "contract" / "frame_extraction.py",
]

_FORBIDDEN_TOKENS = ("os.environ", "getenv", "load_dotenv", "API_KEY", "credentials")


def _python_sources(path: Path):
    if path.is_file():
        yield path
    else:
        yield from sorted(path.rglob("*.py"))


def _scan(roots: list[Path], base: Path = _PKG) -> list[str]:
    """Every forbidden-token hit under ``roots``, reported relative to ``base``.

    ``base`` is a parameter only so the guard can be pointed at a synthetic tree and
    proven to bite — see ``test_the_guard_would_catch_a_credential_reference``.
    """
    hits = []
    for root in roots:
        for source in _python_sources(root):
            text = source.read_text()
            for token in _FORBIDDEN_TOKENS:
                if token in text:
                    hits.append(f"{source.relative_to(base)}: {token!r}")
    return hits


def test_every_declared_credential_blind_root_exists():
    """The half that fixes the class, not the instance (register C-74).

    ``_python_sources`` calls ``rglob`` on a directory that is not a file — and
    ``rglob`` on a **nonexistent** directory yields an empty iterator rather than
    raising. So a missing root and a clean root are indistinguishable to the scan,
    and a package move silently narrows it to nothing while the suite stays green.

    That is precisely what happened between #153 and this test: four of five roots
    resolved to nothing for two days, and the þing-01 #135 audit was pinned over
    roughly a third of what it certified.
    """
    missing = [str(r.relative_to(_PKG)) for r in _CREDENTIAL_BLIND if not r.exists()]
    assert not missing, (
        f"declared credential-blind root(s) no longer exist: {missing}. A move that "
        "leaves this list behind does not fail the scan — it empties it. Re-point the "
        "list at where the modules live now (þing-01 #135, register C-74)."
    )


def test_wire_and_delivery_modules_stay_credential_blind():
    hits = _scan(_CREDENTIAL_BLIND)
    assert not hits, (
        "credential-blind delivery modules now reference the environment or a "
        f"credential (þing-01 #135 audit invalidated): {hits}"
    )


def test_the_scan_covers_the_whole_audited_surface():
    """A count, so silent narrowing shows up as a number rather than as silence.

    The #135 audit certified the delivery path — the wire, the invariants, and the
    three seam modules. It is ~16 files; it was 6 while the roots were stale. The
    bound is deliberately loose (a lower bound, not an equality) so adding a module
    does not fail the suite, while *losing* most of them does.
    """
    scanned = sum(1 for root in _CREDENTIAL_BLIND for _ in _python_sources(root))
    assert scanned >= 15, (
        f"the credential-blind scan covers only {scanned} files. The audited surface "
        "is the wire (8), delivery (6) and three seam modules. A number well below "
        "that means roots are resolving to nothing again — see C-74."
    )


def test_the_guard_would_catch_a_credential_reference(tmp_path):
    """The defect it was written for: a delivery module reading the environment.

    A guard nobody has watched fail is a guard nobody knows the shape of. This one
    was passing for two days over four roots that resolved to nothing (C-74), which
    is exactly what an unproven guard buys you.
    """
    (tmp_path / "clean.py").write_text("def build(table):\n    return table\n")
    assert _scan([tmp_path], base=tmp_path) == [], "a clean module was flagged"

    (tmp_path / "leaky.py").write_text(
        "import os\nkey = os.environ['APPWRITE_DATASTORE_API_KEY']\n"
    )
    hits = _scan([tmp_path], base=tmp_path)
    assert any("leaky.py" in h for h in hits), (
        f"a module reading a credential from the environment was not flagged: {hits}"
    )


def test_provenance_carries_only_the_declared_closed_keyset():
    # The description is uploaded into the store's metadata — it leaves the
    # machine. Its content must stay exactly the declared delivery primitives.
    prov = provenance.build_provenance(
        lookup_version="gaul-2024a",
        region="land_gaul",
        expected_cell_count=64742,
        actual_cell_count=64742,
        unmapped_count=0,
        fill_count=3,
    )
    assert set(prov) == {
        "lookup_version",
        "region",
        "expected_cell_count",
        "actual_cell_count",
        "unmapped_count",
        "fill_count",
    }
    round_trip = json.loads(provenance.compact_description(prov))
    assert round_trip == prov
