"""Delivery provenance invariant: stamp each upload with structured, auditable
provenance so the partner can verify what produced their data (register C-15, S5).

Representation-free — primitives in, a plain JSON-serializable dict out. No pandas, no
datastore types. The manager sources the primitives (the enricher's lookup version, the
configured region, the S1 coverage counts, the unmapped-cell count) and attaches the
returned dict to the upload; the *shape* of provenance lives here.

Carrier note: pipeline-core's ``upload_data`` exposes no structured-metadata field — only
a free-text ``description`` — so the manager serializes this dict into ``description`` as
JSON for now. A dedicated field is requested upstream (see C-15); when it lands, only the
manager's attach step changes, not this shape.
"""

from __future__ import annotations


def build_provenance(
    *,
    lookup_version: str,
    region: str | None,
    expected_cell_count: int | None,
    actual_cell_count: int,
    unmapped_count: int,
    fill_count: int | None = None,
) -> dict:
    """Assemble the structured provenance for one delivered file.

    Every value is sourced by the caller from the actual delivery — the enricher's
    lookup version, the configured region, the coverage counts (S1), the post-enrich
    unmapped-cell count — nothing is hardcoded. ``fill_count`` is included only when the
    caller can supply it (it is omitted rather than reported as a misleading zero).

    Args:
        lookup_version: the GAUL lookup table version that produced the metadata.
        region: the configured delivery region (e.g. ``"land_gaul"``), or None.
        expected_cell_count: the region's pinned cell count, or None if unpinned.
        actual_cell_count: distinct cells actually delivered in this file.
        unmapped_count: delivered cells with missing metadata (0 once validation passes).
        fill_count: optional count of fabricated/filled values, if known.

    Returns:
        A JSON-serializable dict of the provenance fields.
    """
    provenance: dict = {
        "lookup_version": lookup_version,
        "region": region,
        "expected_cell_count": expected_cell_count,
        "actual_cell_count": actual_cell_count,
        "unmapped_count": unmapped_count,
    }
    if fill_count is not None:
        provenance["fill_count"] = fill_count
    return provenance


DESCRIPTION_MAX = 255  # Appwrite metadata attribute limit (run-0 lesson, 2026-07-27)


def compact_description(prov: dict) -> str:
    """The provenance dict as compact JSON, guaranteed to fit the store's
    255-char description attribute — the only structured carrier the upload
    exposes (C-15). The decorative prose prefix died here: it cost the run-0
    historical document (metadata rejected; file stranded as an invisible
    orphan). Fails loud if even compact JSON cannot fit — never truncates
    silently."""
    import json

    text = json.dumps(prov, separators=(",", ":"))
    if len(text) > DESCRIPTION_MAX:
        essential = {
            k: prov[k]
            for k in ("lookup_version", "region", "expected_cell_count", "actual_cell_count", "unmapped_count")
            if k in prov
        }
        text = json.dumps(essential, separators=(",", ":"))
    if len(text) > DESCRIPTION_MAX:
        raise ValueError(
            f"provenance description cannot fit the store's {DESCRIPTION_MAX}-char "
            f"limit even compacted ({len(text)} chars) — refusing to truncate silently."
        )
    return text
