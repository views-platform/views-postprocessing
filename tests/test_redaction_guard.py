"""Guards born from the þing-01 delivery-log/provenance redaction audit (#135,
orð_09 §3 commitment; PLATFORM-001 multi-carrier redaction clause).

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
_CREDENTIAL_BLIND = [
    _PKG / "unfao" / "wire",
    _PKG / "delivery",
    _PKG / "unfao" / "historical.py",
    _PKG / "unfao" / "track_a_source.py",
    _PKG / "unfao" / "frame_extraction.py",
]

_FORBIDDEN_TOKENS = ("os.environ", "getenv", "load_dotenv", "API_KEY", "credentials")


def _python_sources(path: Path):
    if path.is_file():
        yield path
    else:
        yield from sorted(path.rglob("*.py"))


def test_wire_and_delivery_modules_stay_credential_blind():
    hits = []
    for root in _CREDENTIAL_BLIND:
        for source in _python_sources(root):
            text = source.read_text()
            for token in _FORBIDDEN_TOKENS:
                if token in text:
                    hits.append(f"{source.relative_to(_PKG)}: {token!r}")
    assert not hits, (
        "credential-blind delivery modules now reference the environment or a "
        f"credential (þing-01 #135 audit invalidated): {hits}"
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
