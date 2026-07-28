"""Guards for þing-01 P1 (#134): the implicit ensemble-dotenv borrow is dead,
and the manager's entry validation is fail-loud, naming every missing variable.

The borrow (`load_dotenv(ensemble_path_manager.dotenv)` at the old unfao.py:180)
was the runtime edge of the platform's copy-chain (þing-01 sáttmál S6): this
repo's manager reached inside views-models' checkout for its environment. The
verdict retired it — the launcher declares its env sourcing (views-models M3,
merged), and this package only validates (verdict D6).

Imports only `unfao.appwrite_env` (dependency-light by design); the manager
module itself needs views-pipeline-core, absent in test environments, so the
manager-side facts are pinned by source scan — the repo's standing pattern.
"""

import re
from pathlib import Path

import pytest

from views_postprocessing.unfao import appwrite_env


_MANAGER_SOURCE = (
    Path(__file__).resolve().parent.parent
    / "views_postprocessing"
    / "unfao"
    / "managers"
    / "unfao.py"
)


def test_the_dotenv_borrow_is_dead():
    # Prose may mention the dead borrow; importing or calling it may not.
    text = _MANAGER_SOURCE.read_text()
    for token in ("load_dotenv", "from dotenv", "import dotenv", "find_dotenv"):
        assert token not in text, (
            f"{token!r} is back in the manager (þing-01 #134 killed the borrow): "
            "the launcher declares the environment; this package must never load one."
        )


def test_missing_env_raises_naming_every_missing_variable(monkeypatch):
    names = appwrite_env.CONNECTION_ENV + appwrite_env.PROD_FORECASTS_ENV
    for name in names:
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(EnvironmentError) as excinfo:
        appwrite_env.assert_env_declared(names, store="production_forecasts datastore")
    message = str(excinfo.value)
    for name in names:
        assert name in message  # ALL missing names, not just the first


def test_partially_missing_env_names_only_the_missing(monkeypatch):
    names = appwrite_env.CONNECTION_ENV + appwrite_env.UNFAO_ENV
    for name in names:
        monkeypatch.setenv(name, "set")
    monkeypatch.delenv("APPWRITE_UNFAO_BUCKET_ID")
    with pytest.raises(EnvironmentError) as excinfo:
        appwrite_env.assert_env_declared(names, store="unfao_bucket datastore")
    message = str(excinfo.value)
    assert "APPWRITE_UNFAO_BUCKET_ID" in message
    assert "APPWRITE_ENDPOINT" not in message


def test_complete_env_passes(monkeypatch):
    names = appwrite_env.CONNECTION_ENV + appwrite_env.UNFAO_ENV
    for name in names:
        monkeypatch.setenv(name, "set")
    appwrite_env.assert_env_declared(names, store="unfao_bucket datastore")


def test_empty_string_counts_as_missing(monkeypatch):
    # A name exported but empty is not an assembled environment — fail loud,
    # never hand AppwriteConfig an empty coordinate that half-works.
    for name in appwrite_env.CONNECTION_ENV:
        monkeypatch.setenv(name, "set")
    monkeypatch.setenv("APPWRITE_DATASTORE_API_KEY", "")
    with pytest.raises(EnvironmentError, match="APPWRITE_DATASTORE_API_KEY"):
        appwrite_env.assert_env_declared(
            appwrite_env.CONNECTION_ENV, store="production_forecasts datastore"
        )


def test_declared_names_match_the_manager_reads():
    # Declaration and use must not drift: every APPWRITE_* name the manager
    # actually reads is declared, and both store paths validate before building.
    text = _MANAGER_SOURCE.read_text()
    read_names = set(re.findall(r'os\.getenv\("(APPWRITE_[A-Z_]+)"\)', text))
    declared = set(
        appwrite_env.CONNECTION_ENV + appwrite_env.PROD_FORECASTS_ENV + appwrite_env.UNFAO_ENV
    )
    assert read_names == declared
    assert text.count("appwrite_env.assert_env_declared(") == 3  # both stores + legacy save


def test_secret_env_names_follow_the_platform_naming_rule():
    # PLATFORM-001 D3: suffix _API_KEY/_PASSWORD/_TOKEN ⇒ secret. Exactly one
    # declared name is a secret; every other declared name is a coordinate.
    declared = set(
        appwrite_env.CONNECTION_ENV + appwrite_env.PROD_FORECASTS_ENV + appwrite_env.UNFAO_ENV
    )
    secrets = {n for n in declared if n.endswith(("_API_KEY", "_PASSWORD", "_TOKEN"))}
    assert secrets == {"APPWRITE_DATASTORE_API_KEY"}
