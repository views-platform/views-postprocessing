"""The Hop-B sink orchestrator (ADR-013 §4, §5, §6, §11.4 — epic #105; streaming
per-target since the run-0 OOM fix, 2026-07-27).

Composes the wire in the contract's order with the store injected as a port
(DIP) and every value passed through from declarations or Hop-A headers — the
sink mints nothing (§10.2). Memory-bounded by construction: targets are
**leases** (anything with ``.run_id`` and ``.load() -> (frame, headers)``), and
each target's frame lives only for its own gate + shard-writing, then is
released. Peak resident data ≈ one target, never the whole run.

Per target: load (verified, curated by the lease) → **§6 policy gate** → month
shards → release. Run-level facts (run_id, month set, cell set) are checked
incrementally against the first target — a ragged run refuses loud (§4.2).
Then: sidecar built + parity-checked (§5.2) → run manifest **uploaded LAST**
(§4.2, the commit marker; the sidecar is inside the commit) → every document
under the §4.1a fields with the pinned consumer name. Staging goes into a
per-run_id subdirectory; each upload is ledger-logged.

**The §11.4 interlock:** ``upload_enabled`` defaults to
``product.UPLOAD_ENABLED`` (False) — the default configuration stages locally
and makes ZERO store calls; enabling requires an explicit launch declaration,
first live enablement gated on faoapi's C-161 closure.

Note (pipeline-core C-217): manifest bytes are NOT hash-stable through the
store (SDK JSON re-serialization) — never hash-verify manifest bytes; only
shard/sidecar binaries are hash-stable.

Upload store-port surface::

    upload(file_path, *, filename, name, doc_type, category, loa, targets) -> None
"""

from __future__ import annotations

import logging
from pathlib import Path

from views_postprocessing.delivery.draws import assert_draws_uncollapsed
from views_postprocessing.delivery.parity import assert_gid_set_parity
from views_postprocessing.unfao import product
from views_postprocessing.unfao.frame_extraction import cells_of, month_slice
from views_postprocessing.unfao.wire.naming import run_manifest_name
from views_postprocessing.unfao.wire.run_manifest import build_run_manifest
from views_postprocessing.unfao.wire.shard import write_shard
from views_postprocessing.unfao.wire.sidecar import build_sidecar, write_table

logger = logging.getLogger(__name__)

SHARD_DOC_TYPE = "sampled_forecast_shard"
MANIFEST_DOC_TYPE = "sampled_forecast_manifest"
SIDECAR_DOC_TYPE = "sampled_forecast_sidecar"


class SinkError(ValueError):
    """The assembled run cannot be delivered as declared."""


def deliver_run(
    per_target: dict,
    *,
    lookup,
    staging_dir: Path,
    store=None,
    upload_enabled: bool = product.UPLOAD_ENABLED,
    consumer_name: str = product.CONSUMER_DOCUMENT_NAME,
    s_min: int = product.S_MIN,
) -> dict:
    """Deliver one run to `unfao_bucket` (or stage it, when the interlock holds).

    ``per_target`` maps target → lease (``.run_id``, ``.load()``); production
    leases come from ``source_selection.resolve_run``, tests pass trivial ones.
    Returns a summary dict (run_id, records, ``uploaded`` flag, staging path).
    """
    if not per_target:
        raise SinkError("empty run: no targets to deliver.")

    reference: tuple | None = None  # (run_id, months_tuple, gids) from target #1
    staging: Path | None = None
    shard_records: list = []

    for target, lease in per_target.items():
        frame, headers = lease.load()

        # 1. §6 policy gate — before any of this target's bytes are staged.
        assert_draws_uncollapsed(
            frame.values, headers[0]["sample_count"], s_min=s_min, label=f"forecast[{target}]"
        )

        # 2. Run-level facts, checked incrementally (§4.2: ONE run_id, ONE month
        #    set, ONE cell set across the whole run — ragged runs are malformed).
        run_ids = {h["run_id"] for h in headers}
        if len(run_ids) != 1:
            raise SinkError(f"target {target!r} headers disagree on run_id: {sorted(run_ids)}.")
        facts = (
            next(iter(run_ids)),
            tuple(sorted(int(h["time_id"]) for h in headers)),
            frozenset(cells_of(frame)),
        )
        if reference is None:
            reference = facts
            staging = Path(staging_dir) / facts[0]  # per-run_id subdir
            staging.mkdir(parents=True, exist_ok=True)
        else:
            for name, ours, theirs in zip(("run_id", "months", "cell set"), reference, facts):
                if ours != theirs:
                    detail = f"{len(ours)} vs {len(theirs)} cells" if name == "cell set" else f"{ours!r} vs {theirs!r}"
                    raise SinkError(
                        f"targets disagree on {name} ({detail}) — a ragged run is malformed (§4.2)."
                    )

        # 3. This target's shards (§4.1) — producer headers re-embedded untouched.
        for header in headers:
            values, time, unit = month_slice(frame, header["time_id"])
            name, sha = write_shard(values, time, unit, header=header, directory=staging)
            shard_records.append(
                {"name": name, "target": target, "time_id": header["time_id"], "sha256": sha}
            )
        del frame  # release before the next target loads (the OOM fix)

    run_id, months, gids = reference

    # 4. Sidecar (§5) — built, parity-checked, staged.
    table = build_sidecar(lookup, gids)
    assert_gid_set_parity(gids, table.column("priogrid_id").to_pylist())
    sidecar_file, sidecar_sha = write_table(table, run_id=run_id, directory=staging)
    sidecar_record = {"name": sidecar_file, "sha256": sidecar_sha}

    # 5. Run manifest (§4.2) — staged; uploaded LAST below.
    manifest_bytes = build_run_manifest(
        run_id=run_id,
        targets=list(per_target),
        shard_records=shard_records,
        expected_months=list(months),
        expected_cell_count=len(gids),
        sidecar_record=sidecar_record,
    )
    manifest_file = run_manifest_name(run_id)
    (staging / manifest_file).write_bytes(manifest_bytes)

    summary = {
        "run_id": run_id,
        "targets": list(per_target),
        "shards": shard_records,
        "sidecar": sidecar_record,
        "manifest": manifest_file,
        "staging_dir": str(staging),
        "uploaded": False,
    }

    # 6. Upload — behind the §11.4 interlock; shards → sidecar → manifest LAST.
    if not upload_enabled:
        logger.info(
            "ADR-013 upload interlock holding (upload_enabled=False): run %s staged "
            "at %s, ZERO store calls. First live enablement is gated on C-161.",
            run_id,
            staging,
        )
        return summary
    if store is None:
        raise SinkError("upload enabled but no store provided — refusing to guess.")

    common = {"name": consumer_name, "category": "forecast", "loa": "pgm"}

    def _upload(file_name: str, doc_type: str, targets: list) -> None:
        store.upload(staging / file_name, filename=file_name, doc_type=doc_type, targets=targets, **common)
        logger.info("uploaded %s (type=%s, run=%s)", file_name, doc_type, run_id)  # the ledger

    for record in shard_records:
        _upload(record["name"], SHARD_DOC_TYPE, [record["target"]])
    _upload(sidecar_file, SIDECAR_DOC_TYPE, list(per_target))
    _upload(manifest_file, MANIFEST_DOC_TYPE, list(per_target))  # the commit marker
    summary["uploaded"] = True
    return summary
