"""Hop-B file-name templates (ADR-013 §4.1b).

A file name is a **locator only, never identity** (§3.3's lesson): consumers select
by store-document metadata and verify by manifest content hashes; these names exist
so humans and buckets can address the artifacts. Do not parse meaning back out of
them.

Not to be confused with the store-document ``name`` *field* (§4.1a,
``product.CONSUMER_DOCUMENT_NAME``): that routes faoapi's queries; these name files.
The two never interchange.

Templates are pinned by the §10 golden fixture and golden-string tested — a drift
here is a contract change, not a refactor.
"""

from __future__ import annotations


def shard_name(run_id: str, target: str, time_id: int) -> str:
    """`{run_id}__{target}__m{time_id:06d}.arrow.parquet` — one per (target, month)."""
    return f"{run_id}__{target}__m{time_id:06d}.arrow.parquet"


def run_manifest_name(run_id: str) -> str:
    """`{run_id}__manifest.json` — ONE per run (§4.2, the commit marker)."""
    return f"{run_id}__manifest.json"


def sidecar_name(run_id: str) -> str:
    """`{run_id}__sidecar.parquet` — one per run (§5)."""
    return f"{run_id}__sidecar.parquet"
