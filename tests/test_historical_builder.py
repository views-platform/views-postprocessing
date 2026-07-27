"""The frame-native historical artifact builder (unfao/historical.py, #126) —
reader-level parity with the legacy characterization golden, plus its own
fail-loud properties."""

from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from views_frames import FeatureFrame, SpatialLevel, SpatioTemporalIndex

from views_postprocessing.unfao import historical
from views_postprocessing.unfao.frame_extraction import drop_months_above
from views_postprocessing.unfao.gaul_schema import METADATA_COLS

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_historical_parity import GOLDEN, REAL_TARGETS, reader_view  # noqa: E402

_FIXDIR = Path(__file__).resolve().parent / "fixtures" / "historical_golden"
_LOOKUP = Path(__file__).resolve().parents[1] / "views_postprocessing" / "data" / "gaul_lookup.parquet"


def _slice_frame() -> FeatureFrame:
    """The committed raw input slice as the FeatureFrame the loader would return."""
    table = pq.read_table(_FIXDIR / "raw_slice_input.parquet")
    time = np.asarray(table.column("month_id"), dtype=np.int64)
    unit = np.asarray(table.column("priogrid_id"), dtype=np.int64)
    values_2d = np.column_stack(
        [np.asarray(table.column(t), dtype=np.float32) for t in REAL_TARGETS]
    )
    index = SpatioTemporalIndex(time=time, unit=unit, level=SpatialLevel.PGM)
    return FeatureFrame.from_2d(values_2d, index, feature_names=list(REAL_TARGETS))


def test_reader_level_parity_with_the_legacy_golden(tmp_path):
    # The #126 acceptance oracle: same slice, frame-native chain, and faoapi's
    # reader must see the same frame the legacy chain produced (minus junk).
    table = historical.build_historical_table(_slice_frame(), pq.read_table(_LOOKUP))
    historical.assert_metadata_complete(table)
    name, _ = historical.write_historical_artifact(table, tmp_path / "new.parquet")
    new = reader_view(tmp_path / "new.parquet")
    old = reader_view(GOLDEN)
    assert set(new["targets"]) == set(REAL_TARGETS)  # junk row/col GONE by design
    assert new["rows"].keys() == old["rows"].keys()  # identical (month, cell) set
    def norm(v):
        # faoapi's reader semantics: pandas collapses parquet null/NaN to NaN,
        # and _validate_feature_samples (handlers.py:374-376) normalizes scalar
        # and single-element-list values to the same 1-array — the legacy chain
        # shipped [v] (the C-40 list-in-cell disease), the frame builder ships v;
        # both reach faoapi identical. The oracle compares post-normalization.
        if isinstance(v, list) and len(v) == 1:
            v = v[0]
        return float("nan") if v is None else v

    for key, new_cols in new["rows"].items():
        old_cols = old["rows"][key]
        for col in (*REAL_TARGETS, *METADATA_COLS):
            a, b = norm(new_cols[col]), norm(old_cols[col])
            if isinstance(a, float) and isinstance(b, float):
                if a != a and b != b:  # both NaN — equal through the reader
                    continue
                assert a == pytest.approx(b, rel=1e-6), (key, col)
            else:
                assert a == b, (key, col)


def test_junk_columns_are_dropped():
    table = historical.build_historical_table(_slice_frame(), pq.read_table(_LOOKUP))
    assert "row" not in table.column_names and "col" not in table.column_names
    assert table.column_names == ["month_id", "priogrid_id", *REAL_TARGETS, *METADATA_COLS]


def test_strings_are_plain_and_codes_float64():
    table = historical.build_historical_table(_slice_frame(), pq.read_table(_LOOKUP))
    assert table.schema.field("country_iso_a3").type == pa.string()
    assert table.schema.field("admin1_gaul0_code").type == pa.float64()


def test_cell_absent_from_lookup_fails_loud():
    frame = _slice_frame()
    bad_index = SpatioTemporalIndex(
        time=np.asarray(frame.index.time),
        unit=np.where(np.arange(frame.n_rows) == 0, 999_999, np.asarray(frame.index.unit)),
        level=SpatialLevel.PGM,
    )
    bad = FeatureFrame(frame.values, bad_index, feature_names=list(frame.feature_names))
    with pytest.raises(historical.HistoricalArtifactError, match="999999"):
        historical.build_historical_table(bad, pq.read_table(_LOOKUP))


def test_multi_sample_historical_refused():
    frame = _slice_frame()
    fat = FeatureFrame(
        np.repeat(frame.values, 2, axis=2), frame.index, feature_names=list(frame.feature_names)
    )
    with pytest.raises(historical.HistoricalArtifactError, match="single-valued"):
        historical.build_historical_table(fat, pq.read_table(_LOOKUP))


def test_unmapped_cell_count_counts_distinct_gids():
    table = historical.build_historical_table(_slice_frame(), pq.read_table(_LOOKUP))
    assert historical.unmapped_cell_count(table) == 0
    # poke one null into a metadata column across both months of one cell
    poked = table.set_column(
        table.column_names.index("country_iso_a3"),
        "country_iso_a3",
        pa.array(
            [None if i < 2 else v for i, v in enumerate(table.column("country_iso_a3").to_pylist())],
            pa.string(),
        ),
    )
    assert historical.unmapped_cell_count(poked) >= 1


def test_frame_native_month_clip():
    frame = _slice_frame()  # months 121, 122
    clipped = drop_months_above(frame, 121)
    months = sorted(set(np.asarray(clipped.index.time).tolist()))
    assert months == [121]
    assert drop_months_above(frame, 122) is frame  # nothing to clip → identity
