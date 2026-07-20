"""Contract-mode Hop-A inbound: select and assemble the newest manifested run
(ADR-013 §3.2/§4.2a).

The store is a **port** (DIP): any object with the three-method surface below —
production passes the manager's ``DatastoreModule``-backed wrapper, tests pass a
dict-backed fake. This module owns the *selection policy*; byte verification and
assembly stay in ``track_a_source`` (mechanism), the §6 policy gate stays at the
sink.

Selection filters are pinned to pipeline-core's shipped publisher constants
(``sampled_forecast_publisher.py``: ``SHARD_TYPE``/``MANIFEST_TYPE``/
``FORECAST_CATEGORY``/``MANIFEST_NAME_TEMPLATE`` — re-verified 2026-07-20) and
golden-string tested here; a drift on either side fails loud in tests, not in
production.

Await-all-targets (§4.2a): the newest manifest names the run; the run is usable
only when EVERY declared target has a manifested leg. A missing target refuses
loud — a partial run is never assembled. Declared identity (§4.2a): each shard
header's ``provenance.ensemble`` must equal the launch declaration; mismatches
fail loud, never fall back.

Store port surface::

    latest_file_id(filters: dict) -> str | None
    file_metadata(file_id: str) -> dict     # carries at least "name"
    download(file_id: str) -> bytes
"""

from __future__ import annotations

from views_postprocessing.unfao import track_a_source

# pipeline-core's shipped vocabulary (§3.1/§3.2/§3.3) — golden-string tested.
HOP_A_SHARD_FILTERS = {"category": "forecast", "type": "sampled_forecast_shard"}
HOP_A_MANIFEST_FILTERS = {"category": "forecast", "type": "sampled_forecast_manifest"}
HOP_A_MANIFEST_NAME_TEMPLATE = "{run_id}__{target}__manifest.json"


class SourceSelectionError(ValueError):
    """The store's contents do not satisfy the declared selection."""


def fetch_run(store, *, expected_targets, expected_ensemble: str) -> dict:
    """Assemble the newest fully-manifested run matching the declaration.

    Returns ``{target: (frame, headers)}`` for exactly ``expected_targets``.
    """
    newest_id = store.latest_file_id(dict(HOP_A_MANIFEST_FILTERS))
    if newest_id is None:
        raise SourceSelectionError(
            f"no Hop-A manifest in the store (filters={HOP_A_MANIFEST_FILTERS}) — "
            f"nothing has been published under the contract."
        )
    newest = track_a_source.read_manifest(store.download(newest_id))
    run_id = newest["run_id"]

    per_target: dict = {}
    for target in expected_targets:
        manifest = _manifest_for(store, run_id=run_id, target=target, newest=newest)
        shard_bytes = {}
        for entry in manifest["shards"]:
            shard_id = store.latest_file_id(
                {**HOP_A_SHARD_FILTERS, "name": entry["name"]}
            )
            if shard_id is None:
                raise SourceSelectionError(
                    f"run {run_id!r}: manifested shard {entry['name']!r} not found in "
                    f"the store — a torn run must not be assembled."
                )
            shard_bytes[entry["name"]] = store.download(shard_id)
        frame, headers = track_a_source.frames_for_target(manifest, shard_bytes)
        for header in headers:
            found = header.get("provenance", {}).get("ensemble")
            if found != expected_ensemble:
                raise SourceSelectionError(
                    f"run {run_id!r}, target {target!r}: header declares ensemble "
                    f"{found!r}, the delivery was launched for {expected_ensemble!r} — "
                    f"identity mismatch fails loud, never falls back (§4.2a)."
                )
        per_target[target] = (frame, headers)
    return per_target


def _manifest_for(store, *, run_id: str, target: str, newest: dict) -> dict:
    """The (run, target) manifest — the newest one if it already is that pair."""
    if newest["target"] == target:
        return newest
    name = HOP_A_MANIFEST_NAME_TEMPLATE.format(run_id=run_id, target=target)
    file_id = store.latest_file_id({**HOP_A_MANIFEST_FILTERS, "name": name})
    if file_id is None:
        raise SourceSelectionError(
            f"run {run_id!r}: no manifest for declared target {target!r} — the run is "
            f"incomplete for this delivery; awaiting all of its targets (§4.2a)."
        )
    manifest = track_a_source.read_manifest(store.download(file_id))
    if manifest["run_id"] != run_id or manifest["target"] != target:
        raise SourceSelectionError(
            f"manifest named {name!r} declares (run={manifest['run_id']!r}, "
            f"target={manifest['target']!r}) — names are locators, content is identity "
            f"(§3.3); refusing the mismatch."
        )
    return manifest
