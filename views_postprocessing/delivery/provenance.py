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

Deferred deliberately (#297): the producer also publishes a **per-source** boundary map,
``last_valid_month_ids``, in the store attrs and consumer manifest. It is not stamped here
because ``datafactory_query.defaults`` exposes only the scalar ``get_last_valid_month_id``,
and a multi-source map would not fit the 255-char carrier below in any case.
**Trigger:** when C-15's structured metadata field lands upstream and the 255-char ceiling
goes with it, stamp the per-source map alongside the scalar.
"""

from __future__ import annotations


class _Unread:
    """Sentinel for "the observed-range boundary has not been read yet".

    Distinct from ``None``, which means "read attempted and unavailable, so this
    delivery was NOT clipped". Conflating the two is the C-103 mistake — a broken
    read reported as a producer that publishes no boundary — and #297 is what it
    costs: an artifact that cannot say what it clipped against, and a day of
    forensics to recover a number the delivery already had.
    """

    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover - diagnostic only
        return "<boundary-unread>"


#: Managers initialise their boundary attribute to this; ``build_provenance``
#: refuses it. Reaching provenance without having read the boundary is a bug in
#: the call order, not a delivery condition.
UNREAD = _Unread()


def build_provenance(
    *,
    lookup_version: str,
    region: str | None,
    expected_cell_count: int | None,
    actual_cell_count: int,
    unmapped_count: int,
    observed_through: int | None | _Unread,
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
        observed_through: the producer's ``last_valid_month_id`` this delivery clipped
            against, or ``None`` if the boundary could not be read and the clip was
            therefore **skipped** (degrade-open, C-26). Always emitted, never omitted:
            an absent field is indistinguishable from an older artifact that never
            stamped one, and that ambiguity is the whole of #297. Passing
            :data:`UNREAD` raises.
        fill_count: optional count of fabricated/filled values, if known.

    Returns:
        A JSON-serializable dict of the provenance fields.
    """
    if isinstance(observed_through, _Unread):
        raise ValueError(
            "observed_through was never read — provenance is being built before the "
            "observed-range boundary was fetched. This is a call-order bug, not a "
            "delivery condition: pass the boundary the clip used, or None if the read "
            "failed and the clip was skipped (C-26)."
        )
    provenance: dict = {
        "lookup_version": lookup_version,
        "observed_through": observed_through,
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
            for k in (
                "lookup_version",
                "observed_through",
                "region",
                "expected_cell_count",
                "actual_cell_count",
                "unmapped_count",
            )
            if k in prov
        }
        text = json.dumps(essential, separators=(",", ":"))
    if len(text) > DESCRIPTION_MAX:
        raise ValueError(
            f"provenance description cannot fit the store's {DESCRIPTION_MAX}-char "
            f"limit even compacted ({len(text)} chars) — refusing to truncate silently."
        )
    return text
