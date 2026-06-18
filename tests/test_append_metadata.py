"""Tests for the manager's _append_metadata sequence after the ADR-011 swap.

UNFAOPostProcessorManager cannot be instantiated in this environment (it needs
views-pipeline-core), so — like test_validation.py replicates _validate() — this
replicates the exact _append_metadata sequence with GaulLookupEnricher:

    raw = enricher.enrich_dataframe_with_pg_info(df.reset_index(), ...)
    raw = raw[filter_cols].set_index([time_id, entity_id])
    result = predictions.join(raw)

and verifies the joined result carries the 9 metadata columns aligned to the
predictions, with the fail-loud path intact. Keep in lockstep with
views_postprocessing/unfao/managers/unfao.py:_append_metadata.
"""

import pandas as pd
import pytest

from views_postprocessing.unfao.enrichment import GaulLookupEnricher
from views_postprocessing.unfao.gaul_schema import METADATA_COLS

_TIME_ID = "month_id"
_ENTITY_ID = "priogrid_gid"
# filter_cols as built in _append_metadata: time, entity, then the 9 columns.
_FILTER_COLS = [_TIME_ID, _ENTITY_ID, *METADATA_COLS]


@pytest.fixture(scope="module")
def enricher():
    return GaulLookupEnricher()


def _predictions(gids, months=(100, 101)):
    """A minimal prediction frame indexed like a PGMDataset.dataframe."""
    rows = [(m, g) for m in months for g in gids]
    idx = pd.MultiIndex.from_tuples(rows, names=[_TIME_ID, _ENTITY_ID])
    return pd.DataFrame({"pred_ln_sb_best": 0.0}, index=idx)


def _append_metadata(enricher, predictions):
    """Replica of UNFAOPostProcessorManager._append_metadata."""
    raw = enricher.enrich_dataframe_with_pg_info(
        predictions.reset_index(),
        pg_id_col=_ENTITY_ID, time_id_col=_TIME_ID, only_metadata=True,
    )
    raw = raw[_FILTER_COLS].set_index([_TIME_ID, _ENTITY_ID])
    return predictions.join(raw)


class TestAppendMetadata:
    def test_nine_columns_added_and_aligned(self, enricher):
        gids = enricher._lookup.index[:5].tolist()
        out = _append_metadata(enricher, _predictions(gids))
        for c in METADATA_COLS:
            assert c in out.columns
        # The prediction column survives the join.
        assert "pred_ln_sb_best" in out.columns

    def test_row_count_preserved(self, enricher):
        gids = enricher._lookup.index[:4].tolist()
        preds = _predictions(gids, months=(100, 101, 102))
        out = _append_metadata(enricher, preds)
        assert len(out) == len(preds)  # 4 gids x 3 months

    def test_metadata_matches_lookup_per_cell(self, enricher):
        gids = enricher._lookup.index[:6].tolist()
        out = _append_metadata(enricher, _predictions(gids, months=(100,)))
        for g in gids:
            assert out.loc[(100, g), "country_iso_a3"] == \
                enricher._lookup.loc[g, "country_iso_a3"]
            assert out.loc[(100, g), "admin2_gaul2_code"] == \
                enricher._lookup.loc[g, "admin2_gaul2_code"]

    def test_no_nulls_for_known_cells(self, enricher):
        gids = enricher._lookup.index[:20].tolist()
        out = _append_metadata(enricher, _predictions(gids, months=(100,)))
        for c in METADATA_COLS:
            assert out[c].isna().sum() == 0, c

    def test_unknown_cell_yields_null_metadata(self, enricher):
        # Fail-loud: an out-of-lookup cell flows through as NaN so _validate()
        # (not the enricher) is the single place the delivery crashes.
        good = int(enricher._lookup.index[0])
        preds = _predictions([good, 999_999], months=(100,))
        out = _append_metadata(enricher, preds)
        assert out.loc[(100, good), "country_iso_a3"] is not None
        assert pd.isna(out.loc[(100, 999_999), "country_iso_a3"])
