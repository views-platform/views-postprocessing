"""Contract-mode Hop-A inbound: resolve the newest manifested run cheaply, then
lease each target for lazy, memory-bounded loading (ADR-013 §3.2/§4.2a; the
run-0 OOM fix, 2026-07-27 expert review amendments).

Two phases, deliberately split:

- ``resolve_run`` — CHEAP. Downloads only manifests: newest manifest names the
  run; every declared target must have a content-verified (run, target) manifest
  (§4.2a await-all-targets); every listed shard's store **file_id is pinned here**
  so later fetches are race-free — a newer run published mid-delivery cannot be
  mixed in (fetch-by-id, never re-filtered).
- ``TargetLease.load()`` — HEAVY, one target at a time. Downloads the pinned
  shards, delegates byte/manifest verification to ``track_a_source``, verifies
  the **declared identity** (every header's ``provenance.ensemble`` equals the
  launch declaration — fails loud, never falls back), then returns the *product*
  frame: declared-region curation applied (``drop_units``) and the coverage
  invariants asserted. Callers downstream never see raw producer frames.

The store is a **port** (DIP): any object with ``latest_file_id(filters)`` /
``download(file_id)``; production adapts ``DatastoreModule``, tests use a dict.
Selection filters are pinned to pipeline-core's shipped publisher constants
(re-verified 2026-07-20) and golden-string tested.

Note (pipeline-core C-217): manifest bytes are NOT hash-stable through the store
— the Appwrite SDK auto-parses JSON payloads and they are re-serialized in
compact form on download. Only shard/sidecar (binary) bytes are hash-stable.
**Never hash-verify manifest bytes.**
"""

from __future__ import annotations

from dataclasses import dataclass, field

from views_postprocessing.delivery import coverage
from views_postprocessing.contract import track_a_source
from views_postprocessing.contract.frame_extraction import cells_of, drop_units

# pipeline-core's shipped vocabulary (§3.1/§3.2/§3.3) — golden-string tested.
HOP_A_SHARD_FILTERS = {"category": "forecast", "type": "sampled_forecast_shard"}
HOP_A_MANIFEST_FILTERS = {"category": "forecast", "type": "sampled_forecast_manifest"}
HOP_A_MANIFEST_NAME_TEMPLATE = "{run_id}__{target}__manifest.json"


class SourceSelectionError(ValueError):
    """The store's contents do not satisfy the declared selection."""


@dataclass
class TargetLease:
    """One target's claim on a resolved run: manifest + pinned shard file_ids +
    everything needed to load, verify, and curate it later — without re-querying
    the store's 'latest' state."""

    target: str
    manifest: dict
    shard_file_ids: dict  # shard name -> pinned store file_id
    store: object
    expected_ensemble: str
    excluded_gids: frozenset = field(default_factory=frozenset)
    expected_cells: int | None = None

    @property
    def run_id(self) -> str:
        return self.manifest["run_id"]

    def load(self):
        """Fetch (by pinned id), verify, curate — return the PRODUCT ``(frame, headers)``.

        Shards are fetched **one at a time**, by handing ``frames_for_target`` a lookup
        rather than a filled dict. The dict comprehension that stood here downloaded
        every shard of the target before the first was decoded; with the stacking fix
        beside it that made peak 3.06x the delivered frame (register C-101, measured).
        Fetch-by-pinned-id is unchanged — the ids were pinned by ``resolve_run`` and a
        newer run still cannot be mixed in.
        """
        def fetch(name):
            # `frames_for_target` reads a KeyError as "this shard was never pinned".
            # Only the lookup is allowed to say that: a KeyError thrown from inside the
            # store — a response shape indexed with [] somewhere in the client — would
            # otherwise be relabelled "bytes were not provided", blaming the manifest
            # for a store failure and discarding the traceback that says otherwise.
            # C-99 was that exact substitution one layer down.
            file_id = self.shard_file_ids[name]
            try:
                return self.store.download(file_id)
            except KeyError as exc:
                raise SourceSelectionError(
                    f"run {self.run_id!r}, target {self.target!r}: the store raised "
                    f"KeyError({exc}) downloading shard {name!r} (file_id {file_id!r}). "
                    f"The shard was pinned and requested — this is a store fault, not a "
                    f"missing manifest entry."
                ) from exc

        frame, headers = track_a_source.frames_for_target(self.manifest, fetch)
        for header in headers:
            found = header.get("provenance", {}).get("ensemble")
            if found != self.expected_ensemble:
                raise SourceSelectionError(
                    f"run {self.run_id!r}, target {self.target!r}: header declares "
                    f"ensemble {found!r}, the delivery was launched for "
                    f"{self.expected_ensemble!r} — identity mismatch fails loud, "
                    f"never falls back (§4.2a)."
                )
        # Declared-region curation (C-30): the producer publishes its full model
        # grid; the product excludes the declared GAUL-uncovered cells.
        frame = drop_units(frame, self.excluded_gids)
        cells = cells_of(frame)
        if self.excluded_gids:
            coverage.assert_no_excluded_cells(cells, self.excluded_gids, label=f"forecast[{self.target}]")
        if self.expected_cells is not None:
            coverage.assert_complete_coverage(cells, self.expected_cells, label=f"forecast[{self.target}]")
        return frame, headers


def resolve_run(
    store,
    *,
    expected_targets,
    expected_ensemble: str,
    excluded_gids=frozenset(),
    expected_cells: int | None = None,
) -> dict:
    """Resolve the newest fully-manifested run — manifests and file_ids only.

    Returns ``{target: TargetLease}`` covering exactly ``expected_targets``.
    Heavy bytes move only when a lease's ``load()`` is called.
    """
    newest_id = store.latest_file_id(dict(HOP_A_MANIFEST_FILTERS))
    if newest_id is None:
        raise SourceSelectionError(
            f"no Hop-A manifest in the store (filters={HOP_A_MANIFEST_FILTERS}) — "
            f"nothing has been published under the contract."
        )
    newest = track_a_source.read_manifest(store.download(newest_id))
    run_id = newest["run_id"]

    leases: dict = {}
    for target in expected_targets:
        manifest = _manifest_for(store, run_id=run_id, target=target, newest=newest)
        shard_file_ids = {}
        for entry in manifest["shards"]:
            shard_id = store.latest_file_id({**HOP_A_SHARD_FILTERS, "name": entry["name"]})
            if shard_id is None:
                raise SourceSelectionError(
                    f"run {run_id!r}: manifested shard {entry['name']!r} not found in "
                    f"the store — a torn run must not be assembled."
                )
            shard_file_ids[entry["name"]] = shard_id
        leases[target] = TargetLease(
            target=target,
            manifest=manifest,
            shard_file_ids=shard_file_ids,
            store=store,
            expected_ensemble=expected_ensemble,
            excluded_gids=frozenset(excluded_gids),
            expected_cells=expected_cells,
        )
    return leases


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
