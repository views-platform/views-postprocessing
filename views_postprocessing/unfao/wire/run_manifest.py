"""The §4.2 run manifest builder — the run's single commit marker (ADR-013).

ONE manifest per run, spanning all targets, serialized exactly as the §10 fixture
pins it (key order + ``indent=2``): uploaded LAST, after every shard AND the
sidecar, so a run is either whole or invisible. The fields are the §4.2 table:
shard entries carry ``name``/``target``/``time_id``/``sha256`` (hash of the
complete file bytes); ``expected_cell_count`` is per-shard N (§3.2's scope
ruling); the sidecar object is the Erratum-E1 home of the sidecar hash.

Builders declare, they never inspect: every value here arrives from the caller
(the sink), which in turn passed it through from Hop-A headers or computed it
from bytes it just wrote.
"""

from __future__ import annotations

import json

from views_postprocessing.unfao.wire.header import CONTRACT_VERSION


class RunManifestError(ValueError):
    """The declared manifest inputs violate the §4.2 schema."""


_SHARD_KEYS = ("name", "target", "time_id", "sha256")
_SIDECAR_KEYS = ("name", "sha256")


def build_run_manifest(
    *,
    run_id: str,
    targets: list[str],
    shard_records: list[dict],
    expected_months: list[int],
    expected_cell_count: int,
    sidecar_record: dict,
) -> bytes:
    """§4.2 run-manifest JSON bytes, byte-stable against the §10 fixture."""
    for record in shard_records:
        if set(record) != set(_SHARD_KEYS):
            raise RunManifestError(
                f"shard record keys {sorted(record)} != required {sorted(_SHARD_KEYS)} (§4.2)."
            )
    if set(sidecar_record) != set(_SIDECAR_KEYS):
        raise RunManifestError(
            f"sidecar record keys {sorted(sidecar_record)} != required {sorted(_SIDECAR_KEYS)} (§4.2/E1)."
        )
    manifest = {
        "contract_version": CONTRACT_VERSION,
        "run_id": run_id,
        "targets": list(targets),
        "shards": [{key: record[key] for key in _SHARD_KEYS} for record in shard_records],
        "expected_months": list(expected_months),
        "expected_cell_count": expected_cell_count,
        "sidecar": {key: sidecar_record[key] for key in _SIDECAR_KEYS},
    }
    return json.dumps(manifest, indent=2).encode()
