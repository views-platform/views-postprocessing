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

import ast
import logging
import re
from pathlib import Path

import pytest

from tests.conftest import commit_is_on_main, git_output, require_sibling, sibling_repo
from views_postprocessing.contract import launch_config
from views_postprocessing.unfao import appwrite_env

_PKG = Path(__file__).resolve().parent.parent / "views_postprocessing"


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


# ── drift against the Appwrite Seam Contract's registry (S6 / #187, C-57) ────
#
# The registry is the authority for every name below and lives in views-appwrite. It
# is deliberately **referenced, never copied** — one owner, no duplicated values, no
# drift-by-fork — and that is the right call. What it leaves is C-57's gap: nothing
# mechanical tells you when the two have diverged.
#
# Checked 2026-08-02: there is no live drift. This builds the detector while the
# answer is known-good, which is the cheap moment; the alternative is discovering it
# during a failed delivery.
#
# **Never assert on a coordinate VALUE.** The registry holds non-secret identifiers,
# and copying one into a test is the same violation as copying it into code. These
# compare names, declared classes, and the edition — nothing else.

_REGISTRY_RELPATH = Path("docs") / "ADRs" / "platform" / "coordinate_registry.toml"

#: How this module treats each declared name, vs. the registry's own `class` field.
#:
#: **Written out, not derived.** An earlier draft built this by suffix — anything ending
#: `_API_KEY` is a secret, everything else in CONNECTION_ENV is a connection. That is the
#: precise inference the registry's header forbids ("class is DECLARED here, never
#: inferred from a name's prefix"), reproduced inside the test written to enforce it.
#: It happened to be correct, which is what makes the habit worth breaking rather than
#: excusing. Adding a name without classifying it now fails below.
_EXPECTED_CLASS = {
    "APPWRITE_ENDPOINT": "connection",
    "APPWRITE_DATASTORE_PROJECT_ID": "connection",
    "APPWRITE_DATASTORE_API_KEY": "secret",
    "APPWRITE_PROD_FORECASTS_BUCKET_ID": "target",
    "APPWRITE_PROD_FORECASTS_BUCKET_NAME": "target",
    "APPWRITE_PROD_FORECASTS_COLLECTION_ID": "target",
    "APPWRITE_PROD_FORECASTS_COLLECTION_NAME": "target",
    "APPWRITE_UNFAO_BUCKET_ID": "target",
    "APPWRITE_UNFAO_BUCKET_NAME": "target",
    "APPWRITE_UNFAO_COLLECTION_ID": "target",
    "APPWRITE_UNFAO_COLLECTION_NAME": "target",
    "APPWRITE_METADATA_DATABASE_ID": "target",
    "APPWRITE_METADATA_DATABASE_NAME": "target",
}


def test_every_declared_name_is_classified_here():
    """The map above must cover the module exactly — no silent gaps, no strays.

    Without this, adding a name to one of the ENV tuples would simply not be checked
    against the registry, and the drift test would keep passing while covering less.
    That is register **C-74**'s shape: a guard quietly narrower than it claims.
    """
    declared = set(
        appwrite_env.CONNECTION_ENV + appwrite_env.PROD_FORECASTS_ENV + appwrite_env.UNFAO_ENV
    )
    assert set(_EXPECTED_CLASS) == declared, (
        f"unclassified: {sorted(declared - set(_EXPECTED_CLASS))}; "
        f"stale: {sorted(set(_EXPECTED_CLASS) - declared)}"
    )


def _load_registry(repo: Path) -> dict:
    tomllib = pytest.importorskip(
        "tomllib",
        reason="tomllib is stdlib from Python 3.11; pyproject declares >=3.11, so a "
               "conforming environment has it. CI runs 3.11.",
    )
    return tomllib.loads((repo / _REGISTRY_RELPATH).read_text())


def _declared_classes(registry: dict) -> dict[str, str]:
    """name -> the class the registry DECLARES for it (never inferred from the name)."""
    return {
        name: body.get("class")
        for section in ("connection", "target", "secret")
        for name, body in registry.get(section, {}).items()
    }


def test_every_declared_name_exists_in_the_registry_with_the_class_we_treat_it_as():
    """C-57: a rename or reclassification upstream must not be silent here."""
    repo = require_sibling("views-appwrite")
    declared = _declared_classes(_load_registry(repo))

    missing = sorted(n for n in _EXPECTED_CLASS if n not in declared)
    assert not missing, (
        f"names this package requires are absent from the Appwrite Seam Contract's "
        f"registry: {missing}. Either the registry retired them or this module invented "
        "them; the registry is the authority."
    )
    misclassified = {
        n: (expected, declared[n])
        for n, expected in _EXPECTED_CLASS.items()
        if declared[n] != expected
    }
    assert not misclassified, (
        f"class mismatch (expected, registry) {misclassified}. Class is DECLARED by the "
        "registry, never inferred from a name's prefix — a coordinate treated as a "
        "secret (or the reverse) is a redaction bug waiting to happen."
    )


def test_the_pinned_contract_edition_still_matches_the_registry():
    """The check that catches everything the other one cannot — including additions.

    Names and classes catch a rename. The edition catches **any** other change: a new
    target this repo ought to adopt, a retired secret slot, a reworded rule. It fails
    loudly and tells you what to do rather than what broke.
    """
    repo = require_sibling("views-appwrite")
    actual = _load_registry(repo)["meta"]["version"]
    assert actual == appwrite_env.SEAM_CONTRACT_VERSION, (
        f"the Appwrite Seam Contract's registry moved to v{actual}; this repo declares "
        f"v{appwrite_env.SEAM_CONTRACT_VERSION}. Re-verify appwrite_env's declaration "
        f"against v{actual}, then bump SEAM_CONTRACT_VERSION and SEAM_CONTRACT_COMMIT "
        "together. Do not bump one alone — the pair is the claim."
    )


def test_the_pinned_commit_is_reachable_from_the_contract_repos_main():
    """Existence is not reachability, and that distinction cost a merged PR (#196).

    S3 pinned a commit resolved with ``rev-parse HEAD`` on a views-appwrite checkout
    that happened to be sitting on an unmerged branch. The commit existed. Both cited
    files existed at it. Every check anyone had written passed. It had never reached
    ``main``, declared a version that was never ratified, and was withdrawn.
    """
    repo = require_sibling("views-appwrite")
    commit = appwrite_env.SEAM_CONTRACT_COMMIT
    if not git_output(repo, "cat-file", "-t", commit):
        pytest.skip(
            f"{commit} is not in the local views-appwrite checkout — run `git fetch` "
            "there; a stale clone cannot answer whether the pin reached main"
        )
    assert commit_is_on_main(repo, commit), (
        f"the pinned commit {commit!r} is not an ancestor of views-appwrite's main. A "
        "pin taken from a working copy's HEAD can land on an unmerged branch — that is "
        "#196, verbatim. Re-pin from `git rev-parse --short origin/main`."
    )


def test_the_drift_check_would_catch_a_rename(tmp_path):
    """A gated test that cannot fail is decoration — so prove this one bites in CI.

    Runs with **no** views-appwrite checkout: a synthetic registry with one name
    renamed and one reclassified, fed to the same comparison the gated tests use.
    """
    registry = {
        "meta": {"version": appwrite_env.SEAM_CONTRACT_VERSION},
        "connection": {"APPWRITE_ENDPOINT": {"class": "connection"}},
        "target": {"APPWRITE_UNFAO_BUCKET_ID": {"class": "secret"}},  # reclassified
        "secret": {"APPWRITE_DATASTORE_API_KEY": {"class": "secret"}},
    }
    declared = _declared_classes(registry)

    assert "APPWRITE_DATASTORE_PROJECT_ID" not in declared, "fixture should omit it"
    missing = sorted(n for n in _EXPECTED_CLASS if n not in declared)
    assert missing, "the detector reported no missing names against a registry that omits most"

    mismatched = [
        n for n, expected in _EXPECTED_CLASS.items()
        if n in declared and declared[n] != expected
    ]
    assert "APPWRITE_UNFAO_BUCKET_ID" in mismatched, (
        "a target reclassified as a secret went unnoticed — that is the case where "
        "getting it wrong leaks or hides a value"
    )


def _docstring_nodes(tree: ast.AST) -> set[int]:
    """ids of the string Constants that are docstrings — prose, not values."""
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            first = node.body[0] if node.body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                out.add(id(first.value))
    return out


def test_no_coordinate_value_is_copied_into_this_repo():
    """The registry's own rule: *"never bake a value into code, an example, or a
    dataclass default."* Consumers READ and VALIDATE; the launcher supplies values.

    **Two wrong narrowings before this one, both instructive.**

    A substring text scan over every ``.py`` flagged three "leaks": ``file_metadata``
    (a **function name** in ``contract/store_metadata.py``), ``production_forecasts``
    and ``unfao_bucket`` (only in refusal labels and docstrings naming which store a
    function serves). None was a copy, and a guard that fails on
    ``def file_metadata(record)`` gets deleted — after which the real rule is unguarded.

    Narrowing to *assignments and default arguments* then went too far in the other
    direction: it caught neither a dict value nor a keyword argument, and the keyword
    argument is the shape this repo would actually produce —
    ``AppwriteConfig(bucket_id=...)`` is how every store is configured, and swapping one
    ``os.getenv`` for a literal there is the violation.

    The right axis was **exact equality on string constants**, not statement shape. It
    catches dict values and kwargs, while all three original false positives fall out on
    their own: a function name is not a ``Constant``; ``"unfao_bucket datastore"`` is not
    equal to ``"unfao_bucket"``; docstrings are excluded outright.
    """
    repo = sibling_repo("views-appwrite")
    if repo is None:
        pytest.skip("views-appwrite checkout not found — set VIEWS_APPWRITE")
    registry = _load_registry(repo)
    values = {
        body["value"]
        for section in ("connection", "target")
        for body in registry.get(section, {}).values()
        if isinstance(body.get("value"), str) and len(body["value"]) > 6
    }

    copied = []
    for source in sorted(_PKG.rglob("*.py")):
        tree = ast.parse(source.read_text())
        docstrings = _docstring_nodes(tree)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and node.value in values
                and id(node) not in docstrings
            ):
                copied.append(f"{source.relative_to(_PKG)}:{node.lineno} = {node.value!r}")
    assert not copied, (
        f"coordinate value(s) from the registry are copied into code: {copied}. The "
        "registry is referenced, never copied — values reach this package through the "
        "environment the launcher assembles, validated by assert_env_declared."
    )
