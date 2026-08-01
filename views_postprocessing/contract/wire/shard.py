"""The Hop-B arrow shard writer (ADR-013 §4.1).

One ``views_frames.io.arrow`` file per (target, month), the §2 header embedded —
written from declared primitives (one month's ``values/time/unit`` slice, cut by
``frame_extraction.month_slice``) so this module never touches the frame API.
The shard's file name derives from the header's own declarations (never invented
here), and the returned SHA-256 of the complete file bytes is what the §4.2 run
manifest will pin.

Byte determinism: given identical inputs and the pinned toolchain (pyarrow per the
fixture README), the emitted bytes equal the §10 fixture's — the test is byte
parity, not schema similarity.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from views_frames.io import arrow as vf_arrow

from views_postprocessing.contract.wire.naming import shard_name


def write_shard(values, time, unit, *, header: dict, directory: Path) -> tuple[str, str]:
    """Write one (target, month) shard; return ``(file_name, sha256_of_bytes)``.

    ``header`` is the §2 dict from ``wire.header.build_header`` — its ``run_id``,
    ``target`` and ``time_id`` name the file (§4.1b); the whole dict is embedded
    as the arrow metadata (one header, both envelopes).
    """
    name = shard_name(header["run_id"], header["target"], header["time_id"])
    path = Path(directory) / name
    vf_arrow.save(path, values=values, time=time, unit=unit, level="pgm", metadata=header)
    return name, hashlib.sha256(path.read_bytes()).hexdigest()
