"""The ADR-011 GAUL lookup artifact: where it is, what build it is, and one read of it.

One concept — *the precomputed geography asset* — which until #152 was scattered:
its path was a private name in ``enrichment.py`` imported across module boundaries
(register C-68), its version stamp was a ``@staticmethod`` on ``GaulLookupEnricher``
that never touched the instance, and the delivery read the 888 KB parquet **three
times per run** (C-66) — once eagerly into a pandas enricher it never used, then
twice more through pyarrow.

The artifact's identity does not belong to the enricher. ``GaulLookupEnricher`` is
one *consumer* of this asset (the pandas merge used by the build/verification path);
the contract delivery is another, and it wants the table and the stamp, not the
merge. Splitting them lets the delivery read the file once, in arrow, with no pandas
anywhere on the path.

Verified by ``tests/test_gaul_lookup_fidelity.py``: the committed artifact matches
views-datafactory's authoritative GAUL parquets value-for-value, its key is unique,
and the coordinate formula reproduces PRIO-GRID exactly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

#: The committed ADR-011 lookup. Declared public — three modules depend on it, and a
#: leading underscore said the opposite (C-68).
LOOKUP_PATH: Path = Path(__file__).resolve().parent.parent / "data" / "gaul_lookup.parquet"


def version(path: Path | None = None) -> str:
    """A short, stampable build id for the lookup, for delivery provenance (C-15).

    Format: ``<region>@<short source digest>`` (e.g. ``land_gaul@f74d3b2b``) so a
    delivery can be traced to the exact lookup build.

    **Known limitation, tracked as register C-60:** this reaches three levels into
    views-datafactory's ingestion-ledger shape (``source_provenance`` →
    ``land_gaul_region`` → ``content_digest``) and returns ``"unknown"`` if any level
    is absent or reshaped — so the traceability stamp can silently degrade. Moved
    verbatim from ``GaulLookupEnricher._read_version`` in #152 **without behaviour
    change**; fixing it means having the builder write a flat declared key and
    raising here when it is missing, which is C-60's own scope.
    """
    meta = pq.read_metadata(path or LOOKUP_PATH).metadata or {}
    meta = {k.decode(): v.decode() for k, v in meta.items()}
    region = meta.get("region", "?")
    digest = "?"
    try:
        prov = json.loads(meta.get("source_provenance", "{}"))
        digest = (prov.get("land_gaul_region", {}).get("content_digest", "?"))[:8]
    except (ValueError, AttributeError):
        pass
    return "unknown" if region == "?" and digest == "?" else f"{region}@{digest}"


def load(path: Path | None = None) -> pa.Table:
    """The lookup as an arrow table — read **once** per delivery and passed on.

    Both consumers (``wire.sink.deliver_run`` for the §5 sidecar and
    ``historical.build_historical_table`` for the actuals artifact) take the table as
    a **parameter** (DIP), so the delivery threads one value rather than each reading
    the file for itself.
    """
    return pq.read_table(path or LOOKUP_PATH)
