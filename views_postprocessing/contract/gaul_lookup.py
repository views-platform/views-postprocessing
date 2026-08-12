"""The ADR-011 GAUL lookup artifact: where it is, what build it is, and one read of it.

One concept — *the precomputed geography asset* — which until #152 was scattered:
its path was a private name in ``enrichment.py`` imported across module boundaries
(register C-68), its version stamp was a ``@staticmethod`` on ``GaulLookupEnricher``
that never touched the instance, and the delivery read the ~880 KiB parquet **three
times per run** (C-66) — once eagerly into a pandas enricher it never used, then
twice more through pyarrow.

The artifact's identity never belonged to that class, which is why splitting them was
the fix: the delivery wants the table and the stamp, not a merge. It reads the file
**once**, in arrow, with no pandas anywhere on the path. The enricher itself was retired
in #90 (register **C-75**) once it was established it had no production caller.

Verified by ``tests/test_gaul_lookup_fidelity.py``: the committed artifact matches
views-datafactory's authoritative GAUL parquets value-for-value, its key is unique,
and the coordinate formula reproduces PRIO-GRID exactly.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)

#: The single declared metadata key carrying the artifact's build stamp.
#: Written by ``scripts/build_gaul_lookup.py``; read verbatim here (C-60).
VERSION_KEY = "lookup_version"


class LookupVersionError(RuntimeError):
    """The lookup artifact does not declare which build produced it."""

#: The committed ADR-011 lookup. Declared public — three modules depend on it, and a
#: leading underscore said the opposite (C-68).
LOOKUP_PATH: Path = Path(__file__).resolve().parent.parent / "data" / "gaul_lookup.parquet"


def version(path: Path | None = None) -> str:
    """The lookup's DECLARED build stamp, for delivery provenance (C-15).

    Reads one flat key — ``lookup_version`` — written by the builder, which is the
    only thing holding both the region and the producer's ledger. Format:
    ``<region>@<short source digest>`` (e.g. ``land_gaul@f74d3b2b``), so a delivery
    can be traced to the exact lookup build that made it.

    Raises:
        LookupVersionError: if the artifact declares no version. It does not
            degrade to a placeholder — see below.

    **Why it raises (register C-60).** This function used to reconstruct the stamp
    by traversing three levels of views-datafactory's ingestion-ledger shape
    (``source_provenance`` → ``land_gaul_region`` → ``content_digest``) inside a
    bare ``except … pass``, returning the string ``"unknown"`` when any level was
    absent or reshaped. A rename upstream would therefore have made every delivery
    untraceable, silently, in the one field C-15 exists to answer *after* a suspect
    delivery — and no gate would have noticed, because a provenance record was
    still written; it just stopped meaning anything.

    The consumer no longer knows the producer's schema. The builder declares; this
    reads. ADR-003.
    """
    raw = pq.read_metadata(path or LOOKUP_PATH).metadata or {}
    declared = raw.get(VERSION_KEY.encode())
    if not declared:
        err_msg = (
            f"the GAUL lookup at {path or LOOKUP_PATH} declares no {VERSION_KEY!r} — "
            "a delivery built from it could not be traced back to the build that "
            "produced it (register C-15). Rebuild the artifact with "
            "scripts/build_gaul_lookup.py, which writes the key (C-60)."
        )
        logger.error(err_msg)  # ADR-008: logged persistently AND raised
        raise LookupVersionError(err_msg)
    return declared.decode()


def load(path: Path | None = None) -> pa.Table:
    """The lookup as an arrow table — read **once** per delivery and passed on.

    Both consumers (``wire.sink.deliver_run`` for the §5 sidecar and
    ``historical.build_historical_table`` for the actuals artifact) take the table as
    a **parameter** (DIP), so the delivery threads one value rather than each reading
    the file for itself.
    """
    return pq.read_table(path or LOOKUP_PATH)
