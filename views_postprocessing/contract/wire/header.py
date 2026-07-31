"""The §2 contract header builder (ADR-013).

One header, both envelopes: the dict built here becomes ``metadata.json`` inside a
Hop-A archive and the ``views_frames`` embedded metadata of a Hop-B arrow shard —
byte-for-byte, which is why **key order is pinned** (§2's key-order rule: writers
emit exactly the order below so independently written headers can byte-match the
§10 fixture; readers must never depend on it).

Closed sub-objects (§2.1 rule-1 clarification, 2026-07-19): ``id_semantics``,
``provenance``, and ``sharding`` accept no extra keys — adding one is a contract
amendment, not a free addition. This builder enforces that on the only sub-object
the caller supplies (``provenance``); the other two are constructed here.

Mirrors the §10 fixture generator's header (``scripts/build_wire_fixture.py``) —
deliberately not imported from it: the fixture's bytes stay canonical and this
module must independently reproduce them (that is the test).
"""

from __future__ import annotations

CONTRACT_VERSION = "1.5"

_PROVENANCE_KEYS = ("ensemble", "pipeline_core_version", "reconciled")

_ID_SEMANTICS = {"time": "views_month_id", "unit": "priogrid_id"}


class HeaderError(ValueError):
    """The declared header inputs violate the §2 schema."""


def build_header(
    *,
    sample_count: int,
    dtype: str,
    target: str,
    time_id: int,
    run_id: str,
    generated_at: str,
    provenance: dict,
    sharding_index: int,
    sharding_count: int,
) -> dict:
    """The §2 header, keys in the pinned contract order.

    ``provenance`` must carry exactly the three §2.2 keys; everything else is
    declared by the caller (typically passed through from the Hop-A header —
    the sink mints nothing, §10.2).
    """
    if set(provenance) != set(_PROVENANCE_KEYS):
        extra = sorted(set(provenance) - set(_PROVENANCE_KEYS))
        missing = sorted(set(_PROVENANCE_KEYS) - set(provenance))
        raise HeaderError(
            f"provenance is a closed sub-object (§2.2): exactly {list(_PROVENANCE_KEYS)}; "
            f"extra={extra}, missing={missing}."
        )
    return {
        "contract_version": CONTRACT_VERSION,
        "frame_type": "prediction",
        "representation": "samples",
        "sample_count": sample_count,
        "dtype": dtype,
        "spatial_level": "pgm",
        "target": target,
        "time_id": time_id,
        "run_id": run_id,
        "generated_at": generated_at,
        "id_semantics": dict(_ID_SEMANTICS),
        "provenance": {key: provenance[key] for key in _PROVENANCE_KEYS},
        "sharding": {
            "scheme": "per_month",
            "index": sharding_index,
            "count": sharding_count,
        },
    }
