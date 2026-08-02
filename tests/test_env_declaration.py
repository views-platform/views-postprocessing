"""Guards for þing-01 P1 (#134): the implicit ensemble-dotenv borrow is dead,
and the manager's entry validation is fail-loud, naming every missing variable.

The borrow (`load_dotenv(ensemble_path_manager.dotenv)` at the old unfao.py:180)
was the runtime edge of the platform's copy-chain (þing-01 sáttmál S6): this
repo's manager reached inside views-models' checkout for its environment. The
verdict retired it — the launcher declares its env sourcing (views-models M3,
merged), and this package only validates (verdict D6).

Imports `unfao.appwrite_env` and its sibling `contract.launch_config` — both are
dependency-light by design (no views-pipeline-core, no pandas), which is what
lets them be exercised directly here. The manager module is not: it needs
views-pipeline-core, absent in test environments, so the manager-side facts are
pinned by source scan instead — the repo's standing pattern.
"""

import logging
import re
from pathlib import Path

import pytest

from views_postprocessing.contract import launch_config
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
    # One validation per store construction. Was 3 until #149 retired the legacy
    # `_save`, whose Appwrite config duplicated `_unfao_appwrite_config` verbatim;
    # the two survivors are the production_forecasts read and the unfao_bucket write.
    assert text.count("appwrite_env.assert_env_declared(") == 2


# ── ADR-008 across BOTH entry validators (S1 / #182, register C-71) ──────────
#
# `appwrite_env` asserts the launcher assembled the *environment*; `launch_config`
# asserts it declared the *delivery mode*. They are deliberate siblings, NOT a
# shared abstraction (WET before DRY — the trigger to extract is a THIRD such
# module, #181). Siblings drift: `launch_config` was written in #149 by mirroring
# `appwrite_env`, inherited its missing log call, was fixed in review, and left
# the module it copied as the odd one out for two weeks.
#
# Parametrising the ADR-008 obligation over both is what stops that recurring —
# and adding a third validator is one line here, not a new test.
_REFUSALS = (
    pytest.param(
        lambda: appwrite_env.assert_env_declared(("VPP_S1_ABSENT_VAR",), store="test_store"),
        EnvironmentError,
        "VPP_S1_ABSENT_VAR",
        id="appwrite_env.assert_env_declared",
    ),
    pytest.param(
        lambda: launch_config.assert_contract_mode({}),
        launch_config.LaunchConfigError,
        launch_config.WIRE_CONTRACT_KEY,
        id="launch_config.assert_contract_mode",
    ),
    pytest.param(
        lambda: launch_config.assert_frame_native_historical("pandas_dataframe"),
        launch_config.LaunchConfigError,
        launch_config.FEATURE_FRAME_FORMAT,
        id="launch_config.assert_frame_native_historical",
    ),
)


@pytest.mark.parametrize("refuse,exc,expected_token", _REFUSALS)
def test_every_entry_validator_logs_before_it_raises(refuse, exc, expected_token, caplog):
    """ADR-008:48/51 — a structural refusal must leave a persistent record.

    :48 requires raised structural failures to be logged at ERROR or higher; :51
    that *"raising is not a substitute for logging."* A launcher misconfiguration
    is a structural failure by any reading, and these are the two seams whose
    whole job is to make one visible. An operator reading logs after a refused
    run must find the reason there, not only in a traceback they no longer have.
    """
    with caplog.at_level(logging.ERROR):
        with pytest.raises(exc):
            refuse()

    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert len(errors) == 1, (
        f"expected exactly one ERROR record from the refusal, got {len(errors)}: "
        f"{[r.getMessage() for r in errors]}"
    )
    assert expected_token in errors[0].getMessage(), (
        "the log record must name what was missing — a record that says only "
        "'refused' sends the operator back to the traceback it was meant to replace"
    )


def test_the_environment_refusal_logs_names_and_never_values(monkeypatch, caplog):
    """The one place ADR-008 and the redaction discipline could collide.

    `CONNECTION_ENV` carries `APPWRITE_DATASTORE_API_KEY` — a secret slot. Logging
    a refusal is only safe because `missing` holds NAMES: membership is decided by
    `os.getenv(name)` being falsy and the resolved value is never read. This test
    pins that, so a future "let's log the current environment for debuggability"
    cannot land quietly. See tests/test_redaction_guard.py for the wider rule.
    """
    sentinel = "s1-sentinel-secret-value-must-never-be-logged"
    monkeypatch.setenv("APPWRITE_DATASTORE_API_KEY", sentinel)
    monkeypatch.delenv("APPWRITE_ENDPOINT", raising=False)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(EnvironmentError):
            appwrite_env.assert_env_declared(appwrite_env.CONNECTION_ENV, store="unfao_bucket")

    logged = "\n".join(r.getMessage() for r in caplog.records)
    assert "APPWRITE_ENDPOINT" in logged, "the missing NAME must be reported"
    assert sentinel not in logged, "a secret VALUE reached a log record"
    assert "APPWRITE_DATASTORE_API_KEY" not in logged, (
        "the key was set, so it is not missing — it must not appear at all"
    )


def test_secret_env_names_follow_the_seam_contract_naming_rule():
    # þing-01 D3, the Appwrite Seam Contract §3 ("Classification — declared, never
    # inferred"): suffix _API_KEY/_PASSWORD/_TOKEN marks a secret. Exactly one
    # declared name is a secret; every other declared name is a coordinate.
    declared = set(
        appwrite_env.CONNECTION_ENV + appwrite_env.PROD_FORECASTS_ENV + appwrite_env.UNFAO_ENV
    )
    secrets = {n for n in declared if n.endswith(("_API_KEY", "_PASSWORD", "_TOKEN"))}
    assert secrets == {"APPWRITE_DATASTORE_API_KEY"}
