"""Unit tests for the representation-free delivery-provenance invariant (S5 / C-15).

Pure primitives in, a JSON-serializable dict out — no framework, no pandas.
"""

import json

from views_postprocessing.delivery.provenance import build_provenance


def test_carries_all_core_fields_from_primitives():
    prov = build_provenance(
        lookup_version="v1.4.0",
        region="land_gaul",
        expected_cell_count=64_742,
        actual_cell_count=64_742,
        unmapped_count=0,
    )
    assert prov == {
        "lookup_version": "v1.4.0",
        "region": "land_gaul",
        "expected_cell_count": 64_742,
        "actual_cell_count": 64_742,
        "unmapped_count": 0,
    }


def test_fill_count_omitted_when_not_supplied():
    prov = build_provenance(
        lookup_version="v1",
        region="land_gaul",
        expected_cell_count=1,
        actual_cell_count=1,
        unmapped_count=0,
    )
    assert "fill_count" not in prov


def test_fill_count_included_when_supplied():
    prov = build_provenance(
        lookup_version="v1",
        region="land_gaul",
        expected_cell_count=1,
        actual_cell_count=1,
        unmapped_count=0,
        fill_count=7,
    )
    assert prov["fill_count"] == 7


def test_unpinned_region_keeps_none_expected_count():
    prov = build_provenance(
        lookup_version="v1",
        region="africa_me_legacy",
        expected_cell_count=None,
        actual_cell_count=13_110,
        unmapped_count=0,
    )
    assert prov["expected_cell_count"] is None
    assert prov["region"] == "africa_me_legacy"


def test_result_is_json_serializable():
    prov = build_provenance(
        lookup_version="v1.4.0",
        region="land_gaul",
        expected_cell_count=64_742,
        actual_cell_count=64_700,
        unmapped_count=0,
        fill_count=3,
    )
    # round-trips cleanly — it must survive serialization into the upload description.
    assert json.loads(json.dumps(prov)) == prov
