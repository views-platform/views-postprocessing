"""Fidelity guards for the committed ADR-011 GAUL lookup (register C-43 / C-59 / C-61).

``views_postprocessing/data/gaul_lookup.parquet`` is a 64,742-row binary that the
enricher, the historical builder and the wire sidecar all treat as ground truth.
Until 2026-07-31 nothing verified it: every downstream gate checks **presence**
(nulls, cell counts, gid-set equality) and none checked **values**. The migration
plan's own old-vs-new diff (#20 Stage 2 / #23) was signed off without being
produced, and the comparator was deleted in PR #42 — so the backward check is
unrecoverable and C-43 stood open with global data already delivered to FAO.

The check that *is* available runs **forwards**: the lookup is a transcription of
views-datafactory's area-majority GAUL parquets plus a closed-form gid->lat/lon
formula, so both halves can be re-derived from the producer. That was run by hand
on 2026-07-31 (zero mismatches on all four links, including the delivered run-0
sidecar bytes); this module makes it a standing guarantee instead of a session
result. C-43 closes on these tests being green, not on that transcript.

**Scope, deliberately.** These tests prove the lookup faithfully *transcribes* the
producer's assignment. They cannot prove the assignment is *correct* — if
views-datafactory puts a cell in the wrong country, every test here still passes.
That is views-datafactory#387 (square-degree area math at high latitudes), and it
must not be conflated with what this file guarantees.

Split by dependency, on purpose:
  * **always-on** — self-consistency of the committed artifact, plus the coordinate
    formula against a committed PRIO-GRID sample. Runs anywhere, including CI.
  * **skipif** — full value comparison against the views-datafactory sibling
    checkout. Stronger, but absent on most machines (cf. C-46, where a hardcoded
    path made a cross-repo gate invisible; here the skip is explicit and the
    always-on half still guards regressions).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import pytest

from views_postprocessing.delivery import coverage
from views_postprocessing.contract.gaul_schema import (
    CODE_COLS,
    COORD_COLS,
    METADATA_COLS,
    NAME_COLS,
    SOURCE_RENAME,
    xcoord,
    ycoord,
)

_REPO = Path(__file__).resolve().parent.parent
_LOOKUP = _REPO / "views_postprocessing" / "data" / "gaul_lookup.parquet"
_GROUND_TRUTH = _REPO / "tests" / "fixtures" / "priogrid_geometry" / "priogrid_centres_sample.json"

# The lookup is built for this region; its count is pinned in delivery/coverage.py.
_REGION = "land_gaul"

_DATAFACTORY = _REPO.parent / "views-datafactory"
_HAS_DATAFACTORY = (_DATAFACTORY / "data" / "raw" / "gaul_admin").is_dir()
_needs_datafactory = pytest.mark.skipif(
    not _HAS_DATAFACTORY,
    reason=(
        "views-datafactory sibling checkout not present — the producer-comparison half "
        "cannot run here. The always-on tests in this module still guard the artifact."
    ),
)


@pytest.fixture(scope="module")
def lookup():
    assert _LOOKUP.exists(), f"the ADR-011 lookup is missing: {_LOOKUP}"
    return pq.read_table(_LOOKUP)


@pytest.fixture(scope="module")
def lookup_meta():
    raw = pq.read_metadata(_LOOKUP).metadata or {}
    return {k.decode(): v.decode() for k, v in raw.items() if k != b"pandas"}


@pytest.fixture(scope="module")
def gids(lookup):
    return lookup.column("priogrid_gid").to_numpy()


# ── always-on: the committed artifact must be self-consistent ────────────────


def test_lookup_key_is_unique(gids):
    """C-59: a duplicated gid silently inflates the legacy pandas delivery.

    ``enrichment.py`` left-merges on this key, so a duplicate multiplies rows for
    the affected cell — with every metadata value present and non-null, so the
    null gate passes, and with the distinct-cell count unchanged, so the coverage
    gate passes too. Nothing downstream can see it; it has to be caught here.
    """
    unique = np.unique(gids)
    assert unique.size == gids.size, (
        f"the GAUL lookup has {gids.size - unique.size} duplicate gid(s) — the legacy "
        "merge would inflate rows invisibly to every downstream gate (C-59)."
    )


def test_lookup_has_no_nulls(lookup):
    for col in METADATA_COLS:
        assert lookup.column(col).null_count == 0, (
            f"lookup column {col!r} has nulls; the lookup must contain only complete "
            "cells so that an absent cell (not a partial one) is what fails downstream."
        )


def test_lookup_carries_no_sentinel_codes(lookup):
    """C-61: ``-1`` is non-null, so no downstream gate would ever catch it.

    Shipping ``-1`` as a country/admin code is the resolved C-35 defect returning
    through a different door. The builder guards this with a bare ``assert``,
    which ``python -O`` strips — so the artifact is re-checked here.
    """
    for col in CODE_COLS:
        values = lookup.column(col).to_numpy(zero_copy_only=False).astype("float64")
        assert not np.any(values == -1), (
            f"lookup column {col!r} contains the -1 sentinel — this is C-35 (invalid "
            "codes delivered to FAO) recurring, and it is non-null so nothing downstream "
            "would reject it (C-61)."
        )


def test_lookup_names_are_non_empty(lookup):
    for col in NAME_COLS:
        values = lookup.column(col).to_pylist()
        empty = sum(1 for v in values if v is None or str(v).strip() == "")
        assert empty == 0, f"lookup column {col!r} has {empty} empty name(s)."


def test_lookup_columns_are_exactly_the_contract(lookup):
    present = [c for c in lookup.column_names if not c.startswith("__")]
    assert set(present) == {"priogrid_gid", *METADATA_COLS}, (
        f"lookup schema drifted from the 9-column contract: {sorted(present)}"
    )


def test_lookup_cell_count_matches_the_pinned_region_count(gids):
    """The artifact and the delivery's coverage contract must agree.

    If these diverge, either the lookup was rebuilt for a different region or the
    pin in ``delivery/coverage.py`` is stale — both ship wrong coverage.
    """
    expected = coverage.expected_for(_REGION)
    assert expected is not None, f"{_REGION} is unpinned in delivery/coverage.py"
    assert gids.size == expected, (
        f"lookup has {gids.size} cells but delivery/coverage.py pins {expected} for "
        f"{_REGION!r}. One of the two is stale."
    )


def test_lookup_excludes_the_gaul_uncovered_cells(gids):
    """The excluded cells have no GAUL assignment; they must not be in the lookup."""
    leaked = set(gids.tolist()) & set(coverage.excluded_for(_REGION))
    assert not leaked, (
        f"{len(leaked)} GAUL-uncovered cell(s) are present in the lookup: "
        f"{sorted(leaked)[:10]}. These would attribute partner rows to a non-country."
    )


def test_coordinate_formula_matches_priogrid_ground_truth():
    """The gid->lat/lon formula against authoritative PRIO-GRID cell centres.

    This is the highest-leverage check in the module. ``gaul_schema.xcoord/ycoord``
    derive coordinates arithmetically rather than reading them from the producer,
    so a transposed row/col, an off-by-one, or a hemisphere flip would put a plausible
    wrong coordinate on **every** cell — non-null, correctly typed, and invisible to
    every gate in the delivery chain.

    The fixture samples grid corners, row boundaries, the equator crossing and an
    even spread, so the failure modes above cannot all pass by coincidence.
    """
    truth = json.loads(_GROUND_TRUTH.read_text())["cells"]
    bad = []
    for gid_s, want in truth.items():
        gid = int(gid_s)
        if abs(xcoord(gid) - want["xcoord"]) > 1e-9:
            bad.append((gid, "xcoord", want["xcoord"], xcoord(gid)))
        if abs(ycoord(gid) - want["ycoord"]) > 1e-9:
            bad.append((gid, "ycoord", want["ycoord"], ycoord(gid)))
    assert not bad, f"coordinate formula diverged from PRIO-GRID ground truth: {bad[:5]}"


def test_lookup_coordinates_were_built_with_that_formula(lookup, gids):
    """Every stored coordinate must equal the formula applied to its own gid."""
    want_x = np.array([xcoord(int(g)) for g in gids])
    want_y = np.array([ycoord(int(g)) for g in gids])
    got_x = lookup.column("pg_xcoord").to_numpy(zero_copy_only=False)
    got_y = lookup.column("pg_ycoord").to_numpy(zero_copy_only=False)
    assert np.abs(got_x - want_x).max() == 0.0, "stored pg_xcoord disagrees with the formula"
    assert np.abs(got_y - want_y).max() == 0.0, "stored pg_ycoord disagrees with the formula"


def test_lookup_declares_its_provenance(lookup_meta):
    """C-60: the traceability stamp must be present rather than degrading silently.

    ``enrichment._read_version`` falls back to ``"unknown"`` when this metadata is
    absent or reshaped, so the field that ties a delivery to its lookup build can
    vanish without any gate noticing. At minimum the build must declare itself.
    """
    for key in ("adr", "region", "n_cells"):
        assert key in lookup_meta, f"lookup parquet metadata is missing {key!r}"
    assert lookup_meta["region"] == _REGION
    assert int(lookup_meta["n_cells"]) == coverage.expected_for(_REGION)


def test_lookup_version_stamp_resolves(lookup):
    """The stamp the delivery provenance carries (C-15) must not be 'unknown'."""
    from views_postprocessing.contract.enrichment import GaulLookupEnricher

    version = GaulLookupEnricher(_LOOKUP).lookup_version
    assert version != "unknown", (
        "lookup_version resolved to 'unknown' — the delivery would ship untraceable "
        "provenance (C-60). The lookup's embedded source_provenance is absent or reshaped."
    )
    assert version.startswith(f"{_REGION}@"), f"unexpected lookup_version: {version!r}"


# ── skipif: the full comparison against the producer ─────────────────────────


@_needs_datafactory
def test_lookup_values_match_the_producer_parquets(lookup, gids):
    """C-43, the core forward-check: every value against views-datafactory.

    This is what the deleted #23 diff was for, run forwards against the producer
    instead of backwards against the retired mapper. All 7 GAUL columns, all cells.
    """
    mismatches = {}
    for src, dst in SOURCE_RENAME.items():
        table = pq.read_table(_DATAFACTORY / "data" / "raw" / "gaul_admin" / f"{src}.parquet")
        source = dict(
            zip(
                (int(g) for g in table.column("gid").to_pylist()),
                table.column("value").to_pylist(),
            )
        )
        got = lookup.column(dst).to_pylist()
        bad = [
            (int(g), source.get(int(g)), v)
            for g, v in zip(gids, got)
            if source.get(int(g)) != v
        ]
        if bad:
            mismatches[dst] = bad[:5]
    assert not mismatches, (
        f"the committed lookup diverges from the producer's GAUL parquets: {mismatches}. "
        "Rebuild it with scripts/build_gaul_lookup.py against the current datafactory."
    )


@_needs_datafactory
def test_lookup_gid_set_equals_the_declared_region(gids):
    region_file = _DATAFACTORY / "src" / "datafactory_query" / f"{_REGION}_pgids.json"
    region = set(json.loads(region_file.read_text()))
    got = set(int(g) for g in gids)
    assert got == region, (
        f"lookup gid set != {_REGION} region: {len(region - got)} missing, "
        f"{len(got - region)} extra."
    )


@_needs_datafactory
def test_coordinate_formula_matches_every_priogrid_cell():
    """The committed fixture samples 219 cells; the sibling lets us check all 259,200."""
    import struct

    dbf = _DATAFACTORY / "data" / "raw" / "priogrid" / "shapefile" / "priogrid_cell.dbf"
    if not dbf.exists():
        pytest.skip("PRIO-GRID shapefile not present in the datafactory checkout")
    with dbf.open("rb") as fh:
        header = fh.read(32)
        n_records = struct.unpack("<I", header[4:8])[0]
        header_len = struct.unpack("<H", header[8:10])[0]
        record_len = struct.unpack("<H", header[10:12])[0]
        fh.seek(header_len)
        raw = fh.read(n_records * record_len)

    rows = np.char.decode(np.frombuffer(raw, dtype=f"S{record_len}"))
    gid = np.array([int(r[1:11]) for r in rows], dtype=np.int64)
    truth_x = np.array([float(r[11:35]) for r in rows])
    truth_y = np.array([float(r[35:59]) for r in rows])

    want_x = np.array([xcoord(int(g)) for g in gid])
    want_y = np.array([ycoord(int(g)) for g in gid])
    assert np.abs(want_x - truth_x).max() == 0.0, "xcoord formula diverges across the full grid"
    assert np.abs(want_y - truth_y).max() == 0.0, "ycoord formula diverges across the full grid"


# ── the builder's own invariants must not be vacuous ────────────────────────


def _synthetic_source(n: int = 6):
    """A minimal well-formed source frame in the producer's column vocabulary."""
    import pandas as pd

    gids = list(range(1, n + 1))
    return pd.DataFrame(
        {
            "gaul0_code": [10] * n,
            "gaul0_name": ["Country"] * n,
            "gaul1_code": [20] * n,
            "gaul1_name": ["Admin1"] * n,
            "gaul2_code": [30] * n,
            "gaul2_name": ["Admin2"] * n,
            "iso3_code": ["ABC"] * n,
        },
        index=pd.Index(gids, name="gid"),
    )


def _build_with(monkeypatch, source, tmp_path):
    """Run the builder against ``source``, bypassing the datafactory entirely.

    ``region="all"`` short-circuits ``_region_gids`` (returns None), and
    ``_provenance`` is best-effort, so no checkout is required.
    """
    import scripts.build_gaul_lookup as builder

    monkeypatch.setattr(builder, "_load_source", lambda _df: source)
    return builder.build(Path("/nonexistent"), "all", tmp_path / "lookup.parquet")


def test_builder_rejects_a_duplicate_gid(monkeypatch, tmp_path):
    """C-59: prove the uniqueness guard is not vacuous.

    Note the guard is only *reachable* with ``region="all"``. Under a region filter
    pandas' ``Index.intersection`` silently de-duplicates first — an accidental
    protection, not a declared one, which is why the explicit raise still earns its
    place. See the C-59 narrative for the corrected exposure analysis.
    """
    import pandas as pd
    import scripts.build_gaul_lookup as builder

    source = _synthetic_source()
    duplicated = pd.concat([source, source.iloc[[2]]])
    with pytest.raises(builder.LookupBuildError, match="duplicate gid"):
        _build_with(monkeypatch, duplicated, tmp_path)


def test_a_sentinel_code_is_dropped_rather_than_shipped(monkeypatch, tmp_path):
    """C-61, tested honestly: the *completeness filter* is what stops ``-1``.

    The raise at the end of ``build()`` is a backstop that ordinary data can never
    reach — the filter at ``build_gaul_lookup.py:125-131`` removes every ``-1`` row
    first. That filter is plain code, so ``python -O`` does not touch it; the C-61
    exposure is therefore narrower than first registered (see the corrected entry).

    What this pins is the behaviour that actually protects FAO: a cell with a
    sentinel code is **excluded from the lookup**, so it later fails loud as an
    *absent* cell rather than shipping as a wrong-but-non-null code.

    The backstop raise is deliberately left untested — reaching it requires stubbing
    pandas internals, and a test that fragile is worse than the invariant it guards.
    """
    source = _synthetic_source()
    source.loc[3, "gaul1_code"] = -1
    result = _build_with(monkeypatch, source, tmp_path)
    assert 3 not in result.index, "the -1 cell must be dropped from the lookup"
    assert len(result) == 5


def test_builder_accepts_a_clean_source(monkeypatch, tmp_path):
    """The guards must not reject well-formed input."""
    result = _build_with(monkeypatch, _synthetic_source(), tmp_path)
    assert len(result) == 6
    assert list(result.columns) == METADATA_COLS


@_needs_datafactory
def test_coord_dtypes_are_wire_stable(lookup):
    """Codes survive the int64->float64 wire cast losslessly (sidecar/historical §5.1)."""
    for col in CODE_COLS:
        values = lookup.column(col).to_numpy(zero_copy_only=False)
        assert np.all(np.abs(values) < 2**53), (
            f"{col} exceeds exact float64 integer range; the §5.1 float64 wire cast "
            "would silently lose precision."
        )
    for col in COORD_COLS:
        assert lookup.schema.field(col).type == "double", f"{col} must be float64"
