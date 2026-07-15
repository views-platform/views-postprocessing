"""Build the ADR-013 §10 golden fixture — the wire contract's executable spec.

Generates the canonical small-S artifact set into ``tests/fixtures/wire_contract/``:

    fixture_run_0__lr_ged_sb__m000543.tap.zip        Hop-A Track-A shard (zip)
    fixture_run_0__lr_ged_sb__manifest.json          Hop-A (run, target) manifest
    fixture_run_0__lr_ged_sb__m000543.arrow.parquet  Hop-B arrow shard (views_frames.io.arrow)
    fixture_run_0__sidecar.parquet                   §5 GAUL sidecar (9 columns, NaN row preserved)
    fixture_run_0__manifest.json                     Hop-B run manifest (commit marker)
    SHA256SUMS                                       the pinned hashes (§10.1 — THE cross-repo contract)

Deterministic by construction (§10.2): provenance (`run_id`, `generated_at`) is injected
as fixed literals, values come from a fixed seed, and every zip member carries a pinned
1980-01-01 timestamp — regenerating with the same tool versions reproduces the bytes.
The *committed bytes + SHA256SUMS are canonical*; regeneration requires the pinned tool
versions recorded in the fixture README (parquet bytes vary across pyarrow versions).

Data shape (canonical-minimal): 1 target × 1 month × 6 cells × S=4. Row 0 is
draw-degenerate on purpose (pins §6's per-row-zero-variance-is-legal rule); the sidecar's
last gid carries NaN GAUL codes (pins §5.1's NaN-preserved rule). Hop-A manifest carries
``sidecar_sha256: null`` (Erratum E1).

A change to this fixture is a change to the contract (§10).
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from views_frames.io import arrow as vf_arrow

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "wire_contract"

# ---- declared fixture identity (§10.2 injected provenance — fixed literals) -----------
RUN_ID = "fixture_run_0"
GENERATED_AT = "2026-07-15T00:00:00Z"
TARGET = "lr_ged_sb"  # canonical wire vocabulary (§7a)
TIME_ID = 543
S = 4
GIDS = np.array([100001, 100002, 100003, 100004, 100005, 100006], dtype=np.int64)
N = len(GIDS)
_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)  # pinned member timestamp → reproducible zips


def _header(sharding_index: int = 0, sharding_count: int = 1) -> dict:
    """The §2 contract header, in contract field order."""
    return {
        "contract_version": "1.5",
        "frame_type": "prediction",
        "representation": "samples",
        "sample_count": S,
        "dtype": "float32",
        "spatial_level": "pgm",
        "target": TARGET,
        "time_id": TIME_ID,
        "run_id": RUN_ID,
        "generated_at": GENERATED_AT,
        "id_semantics": {"time": "views_month_id", "unit": "priogrid_id"},
        "provenance": {
            "ensemble": "fixture_ensemble",
            "pipeline_core_version": "0.0.0-fixture",
            "reconciled": False,
        },
        "sharding": {"scheme": "per_month", "index": sharding_index, "count": sharding_count},
    }


def _values() -> np.ndarray:
    """(N, S) float32 draws; row 0 deliberately draw-degenerate (per-row zeros are legal)."""
    rng = np.random.default_rng(1305)
    values = rng.gamma(2.0, size=(N, S)).astype(np.float32)
    values[0] = 0.0
    return values


def _npy_bytes(arr: np.ndarray) -> bytes:
    buf = io.BytesIO()
    np.save(buf, arr)
    return buf.getvalue()


def _pinned_zip(members: dict[str, bytes]) -> bytes:
    """A byte-reproducible zip: pinned member timestamps, stored (no compression)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:
        for name, data in members.items():
            zf.writestr(zipfile.ZipInfo(name, date_time=_ZIP_EPOCH), data)
    return buf.getvalue()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    values = _values()
    time = np.full(N, TIME_ID, dtype=np.int64)
    written: dict[str, bytes] = {}

    # --- Hop-A Track-A shard (§3.1): zip of y_pred.npy + identifiers.npz + metadata.json
    identifiers_npz = _pinned_zip({"time.npy": _npy_bytes(time), "unit.npy": _npy_bytes(GIDS)})
    shard_a_name = f"{RUN_ID}__{TARGET}__m{TIME_ID:06d}.tap.zip"
    shard_a = _pinned_zip(
        {
            "y_pred.npy": _npy_bytes(values),
            "identifiers.npz": identifiers_npz,
            "metadata.json": json.dumps(_header(), indent=2).encode(),
        }
    )
    written[shard_a_name] = shard_a

    # --- Hop-A (run, target) manifest (§3.2; Erratum E1: sidecar_sha256 null at Hop A)
    manifest_a_name = f"{RUN_ID}__{TARGET}__manifest.json"
    manifest_a = json.dumps(
        {
            "contract_version": "1.5",
            "run_id": RUN_ID,
            "target": TARGET,
            "shards": [{"name": shard_a_name, "sha256": _sha256(shard_a)}],
            "expected_months": [TIME_ID],
            "expected_cell_count": N,
            "sidecar_sha256": None,
        },
        indent=2,
    ).encode()
    written[manifest_a_name] = manifest_a

    # --- Hop-B arrow shard (§4.1): views_frames.io.arrow with the §2 header as metadata
    shard_b_name = f"{RUN_ID}__{TARGET}__m{TIME_ID:06d}.arrow.parquet"
    shard_b_path = OUT / shard_b_name
    vf_arrow.save(
        shard_b_path, values=values, time=time, unit=GIDS, level="pgm", metadata=_header()
    )
    shard_b = shard_b_path.read_bytes()
    written[shard_b_name] = shard_b

    # --- §5 sidecar: 9 pinned columns, gid-keyed; last gid carries NaN GAUL codes
    sidecar_name = f"{RUN_ID}__sidecar.parquet"
    nan = float("nan")
    sidecar_table = pa.table(
        {
            "priogrid_id": pa.array(GIDS, pa.int64()),
            "pg_xcoord": pa.array([10.25, 10.75, 11.25, 11.75, 12.25, 12.75], pa.float64()),
            "pg_ycoord": pa.array([5.25, 5.25, 5.25, 5.75, 5.75, 5.75], pa.float64()),
            "country_iso_a3": pa.array(["AAA", "AAA", "AAA", "BBB", "BBB", None], pa.string()),
            "admin1_gaul1_code": pa.array([11.0, 11.0, 12.0, 21.0, 21.0, nan], pa.float64()),
            "admin1_gaul1_name": pa.array(["A-one", "A-one", "A-two", "B-one", "B-one", None], pa.string()),
            "admin1_gaul0_code": pa.array([1.0, 1.0, 1.0, 2.0, 2.0, nan], pa.float64()),
            "admin1_gaul0_name": pa.array(["Aland", "Aland", "Aland", "Bland", "Bland", None], pa.string()),
            "admin2_gaul2_code": pa.array([111.0, 112.0, 121.0, 211.0, 212.0, nan], pa.float64()),
            "admin2_gaul2_name": pa.array(["A-1-1", "A-1-2", "A-2-1", "B-1-1", "B-1-2", None], pa.string()),
        }
    )
    pq.write_table(sidecar_table, OUT / sidecar_name)
    sidecar = (OUT / sidecar_name).read_bytes()
    written[sidecar_name] = sidecar

    # --- Hop-B run manifest (§4.2): ONE per run, spanning targets; sidecar hash pinned here
    manifest_b_name = f"{RUN_ID}__manifest.json"
    manifest_b = json.dumps(
        {
            "contract_version": "1.5",
            "run_id": RUN_ID,
            "targets": [TARGET],
            "shards": [{"name": shard_b_name, "target": TARGET, "time_id": TIME_ID, "sha256": _sha256(shard_b)}],
            "expected_months": [TIME_ID],
            "expected_cell_count": N,
            "sidecar": {"name": sidecar_name, "sha256": _sha256(sidecar)},
        },
        indent=2,
    ).encode()
    written[manifest_b_name] = manifest_b

    # --- write byte artifacts + SHA256SUMS (§10.1: the hash is the cross-repo contract)
    for name, data in written.items():
        (OUT / name).write_bytes(data)
    sums = "".join(f"{_sha256((OUT / n).read_bytes())}  {n}\n" for n in sorted(written))
    (OUT / "SHA256SUMS").write_text(sums)
    print(sums)
    print(f"fixture written to {OUT}")


if __name__ == "__main__":
    build()
