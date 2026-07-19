"""Hop-B name templates (wire/naming.py) — golden-string tests against the §10
fixture's actual file names (the templates' executable pin)."""

from pathlib import Path

from views_postprocessing.unfao.wire import naming

_FIX = Path(__file__).resolve().parent / "fixtures" / "wire_contract"


def test_shard_name_reproduces_the_fixture():
    name = naming.shard_name("fixture_run_0", "lr_ged_sb", 543)
    assert name == "fixture_run_0__lr_ged_sb__m000543.arrow.parquet"
    assert (_FIX / name).exists()


def test_run_manifest_name_reproduces_the_fixture():
    name = naming.run_manifest_name("fixture_run_0")
    assert name == "fixture_run_0__manifest.json"
    assert (_FIX / name).exists()


def test_sidecar_name_reproduces_the_fixture():
    name = naming.sidecar_name("fixture_run_0")
    assert name == "fixture_run_0__sidecar.parquet"
    assert (_FIX / name).exists()


def test_month_padding_is_six_digits():
    assert naming.shard_name("r", "t", 7).endswith("__m000007.arrow.parquet")
