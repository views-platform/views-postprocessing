"""Hop-A source adapter: verified Track-A archives → interior ``PredictionFrame``s
(ADR-013 §3 consumer side; the delivery *source* adapter required by the #88 review
amendment — the manager calls this, representation logic never lives inline in it).

Pandas-free by construction: a Track-A archive is zip + npy + json; this module turns it
into declared numpy primitives and hands them to ``frames.build_prediction_frame``. The
new wire path never touches pandas.

Declare-don't-guess, per hop: every check here is a **mechanism** guard — the artifact
must match what its own manifest and header *declare* (hashes, counts, shapes, versions).
The §6 *policy* gate (``delivery.draws``, S_min) is separate and runs at the FAO-facing
upload, not here.

What this module verifies (fail loud, naming expected vs found):
- manifest: contract major-version compatible (§2.1 — MINOR additive, MAJOR breaking);
- shard bytes match the manifest's declared sha256 (§3.2: views-postprocessing verifies
  Hop-A hashes on read);
- archive members are exactly the §3.1 triple; header major-version compatible;
- payload matches the header's own declaration: ``(N, sample_count)`` float32, identifier
  arrays of length N (the per-hop ingest assert);
- a run's shards cover exactly the manifest's expected months and cell count (§4.2a
  feeds on this when the manager awaits all targets).
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile

import numpy as np
from views_frames import PredictionFrame

from views_postprocessing.contract.frames import build_prediction_frame

_ARCHIVE_MEMBERS = {"y_pred.npy", "identifiers.npz", "metadata.json"}
_SUPPORTED_CONTRACT_MAJOR = "1"


class TrackASourceError(ValueError):
    """A Track-A artifact does not match what its manifest or header declares."""


def _require_contract_major(version: str, *, where: str) -> None:
    major = str(version).split(".", 1)[0]
    if major != _SUPPORTED_CONTRACT_MAJOR:
        raise TrackASourceError(
            f"{where}: contract_version {version!r} has major {major!r}; this consumer "
            f"speaks major {_SUPPORTED_CONTRACT_MAJOR!r} (§2.1 — MAJOR bumps are breaking)."
        )


def read_manifest(manifest_bytes: bytes) -> dict:
    """Parse and validate a Hop-A (run, target) manifest (§3.2)."""
    manifest = json.loads(manifest_bytes)
    _require_contract_major(manifest.get("contract_version", "?"), where="manifest")
    for key in ("run_id", "target", "shards", "expected_months", "expected_cell_count"):
        if key not in manifest:
            raise TrackASourceError(f"manifest: required field {key!r} is missing.")
    return manifest


def read_shard(shard_bytes: bytes, *, expected_sha256: str) -> tuple[PredictionFrame, dict]:
    """One verified Track-A shard → ``(PredictionFrame, header)``.

    ``expected_sha256`` is the manifest's declaration for these bytes — the §3.2
    hash verification this repo owns on read.
    """
    actual = hashlib.sha256(shard_bytes).hexdigest()
    if actual != expected_sha256:
        raise TrackASourceError(
            f"shard: sha256 mismatch — manifest declares {expected_sha256}, "
            f"bytes hash to {actual}. Refusing a tampered or torn artifact."
        )
    with zipfile.ZipFile(io.BytesIO(shard_bytes)) as zf:
        members = set(zf.namelist())
        if members != _ARCHIVE_MEMBERS:
            raise TrackASourceError(
                f"shard: archive members {sorted(members)} != required {sorted(_ARCHIVE_MEMBERS)} (§3.1)."
            )
        header = json.loads(zf.read("metadata.json"))
        values = np.load(io.BytesIO(zf.read("y_pred.npy")))
        with zipfile.ZipFile(io.BytesIO(zf.read("identifiers.npz"))) as ids:
            time = np.load(io.BytesIO(ids.read("time.npy")))
            unit = np.load(io.BytesIO(ids.read("unit.npy")))

    _require_contract_major(header.get("contract_version", "?"), where="shard header")
    declared_s = header.get("sample_count")
    if values.ndim != 2 or values.shape[1] != declared_s:
        found = values.shape if values.ndim == 2 else f"{values.ndim}-D"
        raise TrackASourceError(
            f"shard: header declares sample_count={declared_s} but y_pred is {found} — "
            f"the artifact lies about its own draws (per-hop ingest assert)."
        )
    if str(values.dtype) != header.get("dtype"):
        raise TrackASourceError(
            f"shard: header declares dtype={header.get('dtype')!r}, y_pred is {values.dtype}."
        )
    n = values.shape[0]
    if time.shape != (n,) or unit.shape != (n,):
        raise TrackASourceError(
            f"shard: identifier lengths (time={time.shape}, unit={unit.shape}) != N={n}."
        )
    return build_prediction_frame(values, time, unit), header


def frames_for_target(
    manifest: dict, fetch_shard_bytes
) -> tuple[PredictionFrame, list[dict]]:
    """A (run, target)'s verified shards → ``(PredictionFrame, headers)``.

    ``fetch_shard_bytes(name) -> bytes`` returns one shard's bytes on demand; the
    manifest is the only source of which shards exist (§3.3: names are locators,
    manifest content is identity). Verifies run completeness against the manifest's own
    declarations — months covered exactly, cell count per month — then stacks months
    into one frame. The returned ``headers`` (manifest shard order) carry the
    producer-minted provenance the sink passes through untouched (§10.2 — nothing is
    minted downstream).

    **A callback rather than a pre-built dict, and the output filled in place rather
    than concatenated — both for memory (register C-101).** Measured on 2026-08-14 at
    36 shards: taking a dict meant every shard's bytes were resident before the first
    was decoded, and stacking with ``np.concatenate`` meant the per-shard frames and
    the finished array were resident together. Peak was **3.06x the delivered frame**,
    in three roughly equal thirds. Fetching per shard and writing into a
    manifest-sized buffer keeps one shard's bytes and one shard's frame alive at a
    time, so peak is the frame plus a shard.

    The buffer is sized from ``expected_cell_count`` x shard count, which is a
    declaration this function already enforces per shard — a shard whose row count
    disagrees is refused *before* anything is written, so the slot arithmetic can
    never straddle two months.
    """
    entries = manifest["shards"]
    if not entries:
        raise TrackASourceError(
            "run: the manifest lists no shards — an empty run must not be assembled."
        )
    expected_cells = manifest["expected_cell_count"]
    # It sizes an array now, where it used to sit on one side of a `!=`. `6.0` compares
    # equal to `6` and passed the old check happily; here it reaches `np.empty` and
    # raises a bare `TypeError: 'float' object cannot be interpreted as an integer`,
    # naming neither the manifest nor the field. `read_manifest` checks that the key is
    # present, never what it holds, and the manifest crosses a repository boundary.
    if type(expected_cells) is not int or expected_cells < 1:
        raise TrackASourceError(
            f"run: manifest declares expected_cell_count={expected_cells!r} "
            f"({type(expected_cells).__name__}) — it must be a positive integer, "
            f"because it sizes the assembled frame."
        )
    values = time = unit = None
    months_seen, headers = [], []

    for position, entry in enumerate(entries):
        name = entry["name"]
        try:
            shard_bytes = fetch_shard_bytes(name)
        except KeyError:
            raise TrackASourceError(
                f"run: manifest lists shard {name!r} but its bytes were not provided — "
                f"an unmanifested or missing shard must not be silently skipped."
            ) from None
        frame, header = read_shard(shard_bytes, expected_sha256=entry["sha256"])
        # The bytes are dead the moment they are decoded. Dropping the reference here
        # is the whole of the first third: without it every shard's bytes outlive the
        # loop.
        del shard_bytes
        if header.get("target") != manifest["target"]:
            raise TrackASourceError(
                f"run: shard header target {header.get('target')!r} != manifest target "
                f"{manifest['target']!r}."
            )
        if frame.n_rows != expected_cells:
            raise TrackASourceError(
                f"run: shard {name!r} carries {frame.n_rows} cells, manifest expects "
                f"{expected_cells}."
            )
        if values is None:
            total = expected_cells * len(entries)
            frame_time, frame_unit = np.asarray(frame.index.time), np.asarray(frame.index.unit)
            values = np.empty((total, frame.values.shape[1]), dtype=frame.values.dtype)
            time = np.empty(total, dtype=frame_time.dtype)
            unit = np.empty(total, dtype=frame_unit.dtype)
        elif frame.values.shape[1] != values.shape[1]:
            # The buffer's width is fixed by the first shard, so a draw-count
            # disagreement is now this function's constraint rather than numpy's.
            # Left to the assignment it reads "could not broadcast input array from
            # shape (a,b) into shape (a,c)" — no shard named, no mention of draws.
            # Stacking said the same in more words; neither is a refusal (C-99).
            raise TrackASourceError(
                f"run: shard {name!r} carries {frame.values.shape[1]} draws per cell, "
                f"the run's first shard carried {values.shape[1]} — a target assembled "
                f"from shards with different sample counts is not one forecast."
            )
        start = position * expected_cells
        stop = start + expected_cells
        values[start:stop] = frame.values
        time[start:stop] = np.asarray(frame.index.time)
        unit[start:stop] = np.asarray(frame.index.unit)
        headers.append(header)
        months_seen.append(int(header.get("time_id")))
        del frame

    if sorted(months_seen) != sorted(int(m) for m in manifest["expected_months"]):
        raise TrackASourceError(
            f"run: months covered {sorted(months_seen)} != manifest expected "
            f"{sorted(manifest['expected_months'])} — a torn run must not be assembled."
        )
    return build_prediction_frame(values, time, unit), headers
