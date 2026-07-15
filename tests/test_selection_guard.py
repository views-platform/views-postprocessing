"""Golden-string tests for the Hop-A legacy transition guard (ADR-013 §11.4).

The manager cannot be imported in every test environment (it pulls the full
pipeline-core framework), so — like the design-contract tests — these pin the guard
at source level: the legacy selection filters must pin BOTH `category` and the legacy
`type`, so pipeline-core#269's contract uploads (`sampled_forecast_*`) can never be
selected by the deployed legacy reader.
"""

import re
from pathlib import Path

_SRC = (
    Path(__file__).resolve().parent.parent
    / "views_postprocessing" / "unfao" / "managers" / "unfao.py"
).read_text()


def test_legacy_forecast_filters_pin_category_and_type():
    # The golden string (ADR-013 §3.3 spirit): identity of the guard is this exact dict.
    assert 'LEGACY_FORECAST_FILTERS = {"category": "forecast", "type": "ensemble"}' in _SRC


def test_selection_uses_the_guarded_filters():
    # The store selection must go through the guarded constant — no inline
    # category-only filter dict may remain on the selection call.
    assert "get_latest_file_id(filters=LEGACY_FORECAST_FILTERS)" in _SRC
    assert not re.search(
        r"get_latest_file_id\(filters=\{[^}]*\}\)", _SRC
    ), "inline filter dict on the selection call — must use LEGACY_FORECAST_FILTERS"


def test_guard_type_is_disjoint_from_contract_vocabulary():
    # The pinned legacy type must never be one of the contract's types.
    assert '"type": "ensemble"' in _SRC
    for contract_type in (
        "sampled_forecast_shard",
        "sampled_forecast_manifest",
        "sampled_forecast_sidecar",
    ):
        assert f'"type": "{contract_type}"' not in _SRC
