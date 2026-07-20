"""The Hop-B sink orchestrator (ADR-013 §4, §5, §6, §11.4 — epic #105).

Composes the wire pieces in the contract's order, with the store injected as a
port (DIP) and every value passed through from declarations or Hop-A headers —
the sink mints nothing (§10.2):

1. **§6 policy gate first** — ``delivery.draws.assert_draws_uncollapsed`` per
   target, before a single byte is staged.
2. Per-(target, month) arrow shards (§4.1), re-embedding the producer's own
   headers (one header, both envelopes).
3. Sidecar built, **parity-checked** (§5.2), then staged.
4. The run manifest staged LAST-in-spirit and uploaded LAST-in-fact (§4.2 —
   after every shard AND the sidecar: the commit marker).
5. Every store document carries the §4.1a fields with the pinned consumer
   ``name`` — the fix for the F1 invisibility.
6. **The §11.4 interlock**: ``upload_enabled`` defaults to
   ``product.UPLOAD_ENABLED`` (False). Disabled means artifacts are staged
   locally and logged — ZERO store calls; enabling requires an explicit
   declaration at launch, and the first live enablement is gated on faoapi's
   C-161 closure (outside this epic).

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

    ``per_target`` is ``source_selection.fetch_run``'s output:
    ``{target: (frame, headers)}``. Returns a summary dict (run_id, records,
    ``uploaded`` flag, staging paths).
    """
    if not per_target:
        raise SinkError("empty run: no targets to deliver.")
    staging = Path(staging_dir)
    staging.mkdir(parents=True, exist_ok=True)

    # 1. §6 policy gate — before any write.
    for target, (frame, headers) in per_target.items():
        assert_draws_uncollapsed(
            frame.values,
            headers[0]["sample_count"],
            s_min=s_min,
            label=f"forecast[{target}]",
        )

    # Run-level facts, cross-checked across targets (§4.2: ONE months set, ONE
    # per-shard cell count, ONE run id for the whole run).
    run_id = _single_value(per_target, lambda h: h["run_id"], "run_id")
    expected_months = sorted(
        _single_value(per_target, lambda h: h["time_id"], "months", collect=True)
    )
    gids = _single_gid_set(per_target)
    expected_cell_count = len(gids)

    # 2. Shards (§4.1) — the producer's headers re-embedded untouched.
    shard_records = []
    for target, (frame, headers) in per_target.items():
        for header in headers:
            values, time, unit = month_slice(frame, header["time_id"])
            name, sha = write_shard(values, time, unit, header=header, directory=staging)
            shard_records.append(
                {"name": name, "target": target, "time_id": header["time_id"], "sha256": sha}
            )

    # 3. Sidecar (§5) — built, parity-checked, staged.
    table = build_sidecar(lookup, gids)
    assert_gid_set_parity(gids, table.column("priogrid_id").to_pylist())
    sidecar_file, sidecar_sha = write_table(table, run_id=run_id, directory=staging)
    sidecar_record = {"name": sidecar_file, "sha256": sidecar_sha}

    # 4. Run manifest (§4.2) — staged; uploaded LAST below.
    manifest_bytes = build_run_manifest(
        run_id=run_id,
        targets=list(per_target),
        shard_records=shard_records,
        expected_months=expected_months,
        expected_cell_count=expected_cell_count,
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

    # 5+6. Upload — behind the §11.4 interlock.
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
    for record in shard_records:  # shards first …
        store.upload(
            staging / record["name"],
            filename=record["name"],
            doc_type=SHARD_DOC_TYPE,
            targets=[record["target"]],
            **common,
        )
    store.upload(  # … sidecar next …
        staging / sidecar_file,
        filename=sidecar_file,
        doc_type=SIDECAR_DOC_TYPE,
        targets=list(per_target),
        **common,
    )
    store.upload(  # … manifest LAST: the commit marker (§4.2).
        staging / manifest_file,
        filename=manifest_file,
        doc_type=MANIFEST_DOC_TYPE,
        targets=list(per_target),
        **common,
    )
    summary["uploaded"] = True
    return summary


def _single_value(per_target: dict, pick, what: str, *, collect: bool = False):
    """One agreed value across every header of every target — or fail loud."""
    per_target_values = {
        target: sorted({pick(h) for h in headers}) if collect else {pick(h) for h in headers}
        for target, (_, headers) in per_target.items()
    }
    distinct = {tuple(v) if isinstance(v, list) else tuple(sorted(v)) for v in per_target_values.values()}
    if len(distinct) != 1:
        raise SinkError(f"targets disagree on {what}: {per_target_values} — a ragged run is malformed (§4.2).")
    value = next(iter(per_target_values.values()))
    if collect:
        return value
    if len(value) != 1:
        raise SinkError(f"multiple {what} values within one target: {value}.")
    return next(iter(value))


def _single_gid_set(per_target: dict) -> set[int]:
    """One agreed cell set across targets (§4.2/§5.2) — or fail loud."""
    sets = {target: frozenset(cells_of(frame)) for target, (frame, _) in per_target.items()}
    if len(set(sets.values())) != 1:
        sizes = {t: len(s) for t, s in sets.items()}
        raise SinkError(f"targets disagree on the cell set (sizes: {sizes}) — ragged run (§4.2).")
    return set(next(iter(sets.values())))
