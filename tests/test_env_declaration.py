"""Guards for þing-01 P1 (#134): the implicit ensemble-dotenv borrow is dead,
and the manager's entry validation is fail-loud, naming every missing variable.

The borrow (`load_dotenv(ensemble_path_manager.dotenv)` at the old unfao.py:180)
was the runtime edge of the platform's copy-chain (þing-01 sáttmál S6): this
repo's manager reached inside views-models' checkout for its environment. The
verdict retired it — the launcher declares its env sourcing (views-models M3,
merged), and this package only validates (verdict D6).

Imports **every partner's** `appwrite_env` and their shared sibling
`contract.launch_config` — all dependency-light by design (no views-pipeline-core, no
pandas), which is what lets them be exercised directly here. The manager modules are
not exercised directly: instantiating one needs a full Appwrite environment and a
views-models path manager, so the manager-side facts are pinned by source scan instead —
the repo's standing pattern. (The older reason given here, that views-pipeline-core is
"absent in test environments", stopped being true: it is a declared dependency,
CI installs it, and the manager module imports fine.)

**Scoped to `unfao` by name until #211**, at which point `crafd/appwrite_env.py`
landed pinned to a registry edition at which its own coordinates had no values, and
every check here went on passing over a module it was not looking at. The partner list
now comes from `tests/conftest.PARTNER_PACKAGES` and is asserted against the
filesystem, so the next partner cannot be silently exempt (register C-57).
"""

import ast
import hashlib
import logging
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tests.seam_registry import (
    ABSENT as _ABSENT,
    REGISTRY_RELPATH as _REGISTRY_RELPATH,
    RegistryReadError as _RegistryReadError,
    registry_at as _registry_at,
    registry_current as _registry_current,
    rows as _rows,
)
from tests.conftest import (
    PARTNER_PACKAGES,
    broken_sibling_overrides,
    commit_is_on_main,
    git_output,
    require_sibling,
)
from views_postprocessing.contract import launch_config
from views_postprocessing.crafd import appwrite_env as crafd_env
from views_postprocessing.unfao import appwrite_env

_REPO = Path(__file__).resolve().parent.parent
_PKG = _REPO / "views_postprocessing"


def _manager_source(partner: str) -> Path:
    """``<partner>/managers/<partner>.py``, asserted to exist.

    The layout is **declared** — ``docs/CLONING.md`` §3 states it as the shape a new
    partner supplies — but a declaration this function merely assumes is one it cannot
    notice going stale. Without the check below a renamed manager gives a bare
    ``FileNotFoundError`` from ``read_text``, which is loud but says nothing about
    which rule was broken (ADR-014 §2: assert that a guard's inputs are real).
    """
    path = _PKG / partner / "managers" / f"{partner}.py"
    assert path.exists(), (
        f"no manager at {path.relative_to(_PKG.parent)}. Every check in this file that "
        f"scans {partner}'s manager silently covers nothing without it. The layout is "
        "declared in docs/CLONING.md §3 — either follow it or teach this function the "
        "new one; do not leave the scan pointing at a path that stopped existing."
    )
    return path


_SHARED_CLASS = {
    "APPWRITE_ENDPOINT": "connection",
    "APPWRITE_DATASTORE_PROJECT_ID": "connection",
    "APPWRITE_DATASTORE_API_KEY": "secret",
    "APPWRITE_PROD_FORECASTS_BUCKET_ID": "target",
    "APPWRITE_PROD_FORECASTS_BUCKET_NAME": "target",
    "APPWRITE_PROD_FORECASTS_COLLECTION_ID": "target",
    "APPWRITE_PROD_FORECASTS_COLLECTION_NAME": "target",
    "APPWRITE_METADATA_DATABASE_ID": "target",
    "APPWRITE_METADATA_DATABASE_NAME": "target",
}

#: Per partner: the module, the tuple naming its own outbound store, and how this test
#: treats every name that partner declares.
#:
#: **Parametrised since #211, and that is the point.** Every check below imported
#: ``unfao.appwrite_env`` by name. When ``crafd/appwrite_env.py`` landed pinned two
#: registry editions stale — at a commit where its own four ``APPWRITE_CRAFD_*``
#: coordinates still carried no values — not one of them fired, because none of them
#: was looking. A drift detector that names its subject cannot detect drift in the
#: subject it does not name (register C-57, amended 2026-08-03).
_PARTNER_ENV = {
    "unfao": (
        appwrite_env,
        appwrite_env.UNFAO_ENV,
        _SHARED_CLASS | {
            "APPWRITE_UNFAO_BUCKET_ID": "target",
            "APPWRITE_UNFAO_BUCKET_NAME": "target",
            "APPWRITE_UNFAO_COLLECTION_ID": "target",
            "APPWRITE_UNFAO_COLLECTION_NAME": "target",
        },
    ),
    "crafd": (
        crafd_env,
        crafd_env.CRAFD_ENV,
        _SHARED_CLASS | {
            "APPWRITE_CRAFD_BUCKET_ID": "target",
            "APPWRITE_CRAFD_BUCKET_NAME": "target",
            "APPWRITE_CRAFD_COLLECTION_ID": "target",
            "APPWRITE_CRAFD_COLLECTION_NAME": "target",
        },
    ),
}

_PARTNERS = tuple(_PARTNER_ENV)

#: Every coordinate name any partner declares — the left-hand sides a document could
#: assign a registry value to.
_EXPECTED_NAMES = {name for _, _, expected in _PARTNER_ENV.values() for name in expected}


#: Function names that belong to python-dotenv and to essentially nothing else.
#:
#: ``set_key``/``get_key``/``unset_key`` are deliberately **absent**. They are dotenv
#: members, but they are also ordinary method names — a first draft included ``set_key``
#: and flagged ``draft.set_key("run_id", run_id)`` in ``contract/store_metadata.py`` as
#: *"python-dotenv is back in this package"*. That is ADR-014 §3: a guard that cries
#: wolf gets deleted, and then the rule it carried is unguarded. Reaching them requires
#: importing ``dotenv``, which the import half below catches outright.
_DOTENV_CALLS = {"load_dotenv", "find_dotenv", "dotenv_values"}


def _parsed(path: Path) -> ast.Module:
    """Parse ``path``, refusing a malformed module by path and line — never by content."""
    try:
        return ast.parse(path.read_text())
    except SyntaxError as exc:
        raise AssertionError(f"{path.name} does not parse (line {exc.lineno})") from None


def _dotenv_use(path: Path) -> list[str]:
    """Real imports of, and calls into, python-dotenv — parsed, not grepped.

    A malformed module is refused by path and line, never by content. ``ast.parse``
    raises with the source as its own frame's argument, which pytest renders in full — so
    a package file that both fails to parse and carries a coordinate value would publish
    itself. ``from None`` drops the chained ``SyntaxError``, which carries the same text.
    (An earlier version credited the ``Path`` parameter for this. Measured: it changes
    nothing, because the text still reaches ``ast.parse``.)

    **Prose is not a violation and must not be treated as one.** ``appwrite_env.py``'s
    own docstring explains what the retired borrow was, spelling it exactly; a token
    scan over the package flags that sentence and gets deleted, after which the rule it
    carried is unguarded (ADR-014 §3 — when a guard cries wolf, the matching is wrong
    before the scope is). An AST walk sees imports and calls and never sees a docstring
    or a comment, so the guard can cover the whole package without lying about prose.
    """
    found = []
    for node in ast.walk(_parsed(path)):
        if isinstance(node, ast.Import):
            found += [a.name for a in node.names if a.name.split(".")[0] == "dotenv"]
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] == "dotenv":
                found.append(f"from {node.module}")
        elif isinstance(node, ast.Call):
            fn = node.func
            name = fn.id if isinstance(fn, ast.Name) else getattr(fn, "attr", None)
            if name in _DOTENV_CALLS:
                found.append(f"{name}()")
    return sorted(set(found))


def test_no_sibling_override_points_at_a_missing_path():
    """Assert the cross-repo checks' inputs are real (ADR-014 §2), once for all of them.

    Every gated check in this repository resolves a sibling checkout and skips when it
    is absent. Absent is normal — CI checks out only this repo. A variable that is
    *set* and wrong is not normal, and skipping on it means an operator who asked for
    the cross-repo assertions silently got none of them, for as long as the typo lives.
    """
    broken = broken_sibling_overrides()
    assert not broken, (
        f"sibling override(s) set but pointing at nothing: {broken}. Every check gated "
        "on those repositories is skipping — you asked for them and are getting none. "
        "Fix the path or unset the variable."
    )


def test_the_dotenv_borrow_is_dead():
    """þing-01 #134's verdict, held over the whole package rather than two files.

    **This guard has been too narrow twice.** It was scoped to ``unfao``'s manager, and
    a live ``load_dotenv`` in ``crafd/managers/crafd.py`` left the suite green. Widened
    to both managers, it still covered 2 files of 30: verified 2026-08-03 that
    ``load_dotenv(find_dotenv())`` at module scope in ``unfao/appwrite_env.py`` — *the
    entry validator whose own docstring says the borrow is dead* — ran on import with
    the suite green, as did the same line in ``product.py`` and ``launch_config.py``.

    The rule was never about managers. þing-01 D6 says **this package** validates the
    environment and never loads one, so the scan is the package. Register **C-74**'s
    shape twice over: a guard narrower than the sentence describing it.
    """
    offenders = {
        source.relative_to(_PKG).as_posix(): used
        for source in sorted(_PKG.rglob("*.py"))
        for used in [_dotenv_use(source)]
        if used
    }
    assert not offenders, (
        f"python-dotenv is back in this package: {offenders}. þing-01 #134 killed the "
        "borrow — the launcher declares the environment (verdict D6) and this package "
        "validates it fail-loud. A module that loads a .env reintroduces the copy-chain "
        "the assembly retired, and does it at import time, before any validation runs."
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


@pytest.mark.parametrize("partner", _PARTNERS)
def test_declared_names_match_the_manager_reads(partner):
    # Declaration and use must not drift: every APPWRITE_* name the manager
    # actually reads is declared, and both store paths validate before building.
    #
    # Parametrised since #211. The crafd manager reads its own four coordinates by
    # hardcoded literal (`crafd.py:363-366`) exactly as the FAO one does, so it can
    # drift from its own declaration in exactly the same way — and did not have a
    # check saying otherwise.
    module, own_store, _ = _PARTNER_ENV[partner]
    text = _manager_source(partner).read_text()
    read_names = set(re.findall(r'os\.getenv\("(APPWRITE_[A-Z_]+)"\)', text))
    declared = set(module.CONNECTION_ENV + module.PROD_FORECASTS_ENV + own_store)
    assert read_names == declared, (
        f"[{partner}] the manager reads {sorted(read_names - declared)} without "
        f"declaring them, and declares {sorted(declared - read_names)} without "
        "reading them"
    )
    # One validation per store construction. Was 3 until #149 retired the legacy
    # `_save`, whose Appwrite config duplicated `_unfao_appwrite_config` verbatim;
    # the two survivors are the production_forecasts read and the partner-bucket write.
    assert text.count("appwrite_env.assert_env_declared(") == 2


def test_a_queryset_that_failed_to_import_is_refused_as_that(caplog):
    """Register C-83 — the refusal must name the real fault, not a plausible one.

    `get_queryset()` returns ``None`` for **any** exception while importing
    ``config_queryset.py``. Feeding that to ``declared_data_format`` yields
    ``'dataframe'`` (its documented default for a non-dict), and the format guard then
    tells the operator to set ``data_format: 'feature_frame'`` — in a file that already
    says exactly that.

    Reproduced both ways on 2026-08-03: in an environment without views-datafactory the
    real ``un_fao`` queryset reported ``dataframe`` while declaring ``feature_frame``;
    in a complete environment the same file reported ``feature_frame``.
    """
    import logging

    with caplog.at_level(logging.ERROR):
        with pytest.raises(launch_config.LaunchConfigError) as excinfo:
            launch_config.assert_queryset_was_importable(None)

    message = str(excinfo.value)
    assert "could not be imported" in message
    assert "data_format" in message and "do not edit" in message.lower(), (
        "the refusal must actively steer the operator AWAY from the config file — "
        "that is the whole point, since the old message steered them into it"
    )
    assert any(r.levelno >= logging.ERROR for r in caplog.records), (
        "ADR-008: a structural refusal leaves a persistent record, not just a traceback"
    )


def test_an_importable_queryset_passes_the_readability_check():
    """The guard must not stand in front of a queryset that imported fine.

    Anything not-None passes here; whether it declares the right format is the *next*
    check's question, and keeping them separate is the entire fix.
    """
    launch_config.assert_queryset_was_importable({"data_format": "feature_frame"})
    launch_config.assert_queryset_was_importable({})  # wrong, but importable


def test_both_managers_check_importability_before_asking_what_was_declared():
    """Order matters: reversed, the confusing message wins again.

    Source-scan because the managers need Appwrite env and a views-models path manager
    to instantiate — the standing pattern for manager-side facts.
    """
    for partner in _PARTNERS:
        source = _manager_source(partner).read_text()
        assert source.count("get_queryset()") == 1, (
            f"[{partner}] the queryset must be read ONCE and the value reused; reading "
            "it twice invites the two checks to disagree about what they saw"
        )
        importable = source.index("assert_queryset_was_importable")
        declared = source.index("assert_frame_native_historical")
        assert importable < declared, (
            f"[{partner}] the importability check must come FIRST. Reversed, a queryset "
            "that failed to import is still reported as one declaring 'dataframe'."
        )


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


#: How this module treats each declared name, vs. the registry's own `class` field.
#:
#: **Written out, not derived.** An earlier draft built this by suffix — anything ending
#: `_API_KEY` is a secret, everything else in CONNECTION_ENV is a connection. That is the
#: precise inference the registry's header forbids ("class is DECLARED here, never
#: inferred from a name's prefix"), reproduced inside the test written to enforce it.
#: It happened to be correct, which is what makes the habit worth breaking rather than
#: excusing. Adding a name without classifying it now fails below.
def test_every_partner_package_has_its_environment_checked_here():
    """Assert this module's declared scope is the real one (ADR-014 §2).

    ``_PARTNER_ENV`` is what every parametrised check below iterates. A partner
    package missing from it is a partner whose coordinates nobody compares against the
    registry — and the suite stays green, which is exactly how ``crafd`` arrived. So
    the keys are checked against the repository's single declared partner list rather
    than maintained by hand and hoped over.
    """
    assert set(_PARTNERS) == set(PARTNER_PACKAGES), (
        f"partner packages without an environment check: "
        f"{sorted(set(PARTNER_PACKAGES) - set(_PARTNERS))}; "
        f"checked but no longer a partner: {sorted(set(_PARTNERS) - set(PARTNER_PACKAGES))}. "
        "Add the partner to _PARTNER_ENV — an unlisted one is silently exempt from "
        "every registry comparison in this file."
    )


@pytest.mark.parametrize("partner", _PARTNERS)
def test_every_declared_name_is_classified_here(partner):
    """The map above must cover each module exactly — no silent gaps, no strays.

    Without this, adding a name to one of the ENV tuples would simply not be checked
    against the registry, and the drift test would keep passing while covering less.
    That is register **C-74**'s shape: a guard quietly narrower than it claims.
    """
    module, own_store, expected = _PARTNER_ENV[partner]
    declared = set(module.CONNECTION_ENV + module.PROD_FORECASTS_ENV + own_store)
    assert set(expected) == declared, (
        f"[{partner}] unclassified: {sorted(declared - set(expected))}; "
        f"stale: {sorted(set(expected) - declared)}"
    )


#: Every top-level table the registry may carry, and what this repository does with it.
#:
#: **Declared, and asserted against the live registry** — a table appearing upstream that
#: nobody here has classified is a change this repository has not looked at. That is not
#: hypothetical: `[contract.*]` arrived in v1.5.0 carrying a live obligation (the
#: ADR-017 delivery-label mirror), and the ONLY mechanism here that noticed was a
#: version-string comparison that fired for the wrong reason and was deleted with this
#: change. Four tables were being ignored silently at the time.
_TABLE_ROLE = {
    "connection": "CONSUMED",   # parsed by _declared_classes; coordinates we read
    "target": "CONSUMED",       # parsed by _declared_classes; coordinates we read
    "secret": "CONSUMED",       # parsed by _declared_classes; the operator's slots
    "contract": "MIRRORED",     # values live in our source by design (ADR-017 §5);
    #                             checked by tests/test_product.py, not by _declared_classes
    "excluded": "IGNORED",      # names the registry records as deliberately NOT coordinates
    # IGNORED because nothing here READS it, not because it is none of our business —
    # it is the clause that says which live checks this package may build, and a reader
    # who believed the older comment spent weeks thinking a permission was a prohibition
    # (register C-95, C-96). Its rows are bare strings, not tables, so it must stay out of
    # `rows()` until that is handled (C-91).
    "test_environment": "IGNORED",
    #: Arrived at registry v1.6.0, and it is views-appwrite#76 delivered — each edition
    #: marked ``obliges_consumers = true|false``, so a consumer can tell a console
    #: observation from a change it must act on. IGNORED only because nothing here reads
    #: it YET: adopting it is the follow-up that lets the drift check below stop caring
    #: about editions that oblige nobody. Caught by this very partition on its first
    #: encounter, which is what the partition is for.
    "edition": "IGNORED",
    "meta": "METADATA",         # the edition and its amendment log
}

#: An IGNORED table vanishing upstream is deliberately unchecked; a new, unclassified one
#: is a red build with something to do. (An earlier version of this comment illustrated
#: the silent case with v1.5.1's removal of `[unmodelled]`, which was wrong — `unmodelled`
#: was never in this partition, so it would have been a red build demanding
#: classification. The rule was right; the illustration was not, in three places.)
#: The only roles that mean anything. A typo in `_TABLE_ROLE` used to be silent, and it
#: silently narrowed a security scan: mistyping "CONSUMED" dropped `target` from the
#: no-copy check's sections, taking it from twelve values to two, with no test objecting.
_ROLES = ("CONSUMED", "MIRRORED", "IGNORED", "METADATA")

#: Tables this package reads rows out of. **One source, three consumers** — the class
#: check, the drift projection and the no-copy scan all derive from here rather than each
#: keeping a copy of the tuple. They did keep copies, which made classifying a table as
#: CONSUMED add exactly zero coverage while satisfying the guard that demanded it — the
#: guard's own remediation advice producing register C-74's shape.
_CONSUMED_TABLES = tuple(n for n, role in _TABLE_ROLE.items() if role == "CONSUMED")

_TABLES_WE_DEPEND_ON = tuple(
    name for name, role in _TABLE_ROLE.items() if role in ("CONSUMED", "MIRRORED")
)


def _unclassified_tables(registry: dict) -> list[str]:
    """Tables upstream that nobody here has classified. THE production predicate.

    Extracted so the proof can call it instead of re-typing it. The previous proof
    re-typed the set arithmetic, so neutering this to ``return []`` left it green — a
    detector for the detector that detected nothing.
    """
    return sorted(set(registry) - set(_TABLE_ROLE))


def _missing_dependencies(registry: dict) -> list[str]:
    """Tables we depend on that are absent upstream. THE production predicate."""
    return sorted(n for n in _TABLES_WE_DEPEND_ON if n not in registry)


def _projection(registry: dict, names: set[str]) -> dict[str, tuple]:
    """``name -> (section, class, value-or-absent)`` for the names we declare.

    The unit of comparison between two editions. Restricted to our own surface, so an
    unrelated row moving is invisible here — that is the whole point, and it is what
    stops an observation-only bump from reddening this repository (register C-86).

    ``value`` is included because **rotation is the change no other check can see**: a
    bucket id whose value changes keeps its name and its class, so the names-and-classes
    check passes while every delivery goes to the wrong place. The no-copy rule forbids
    writing the expected values into this repository, so the pinned edition is the only
    lawful place a baseline for that comparison can live.
    """
    return {n: row for n, row in _rows(registry, _CONSUMED_TABLES).items() if n in names}


def _describe_changes(then: dict, now: dict, names: set[str]) -> dict[str, str]:
    """What differs, said WITHOUT printing a coordinate value.

    This repository is public and its CI logs are world-readable. The first version of
    this comparison interpolated the projection tuples straight into the assertion
    message — so the single event this check exists to fire on, a rotated coordinate,
    would have printed the old and new values into a public log. Longer than the
    six-character threshold the no-copy check itself uses to define a leak, and the
    outcome ``tests/test_redaction_guard.py`` exists to prevent.

    So: name the field that moved, and for a value give a short digest — enough to see
    that two editions disagree and to match against a rotation you performed, never
    enough to be the value.
    """
    def digest(value) -> str:
        if value is _ABSENT:
            return "<absent>"
        return f"<sha256:{hashlib.sha256(str(value).encode()).hexdigest()[:8]}>"

    out = {}
    for name in sorted(names):
        was, is_ = then.get(name), now.get(name)
        if was == is_:
            continue
        if was is None or is_ is None:
            out[name] = "absent at the pin" if was is None else "removed upstream"
            continue
        fields = [
            f"{label}: {a!r} -> {b!r}" if label != "value" else f"value: {digest(a)} -> {digest(b)}"
            for label, a, b in zip(("section", "class", "value"), was, is_)
            if a != b
        ]
        out[name] = "; ".join(fields)
    return out


def _declared_classes(registry: dict) -> dict[str, str]:
    """name -> the class the registry DECLARES for it (never inferred from the name)."""
    return {n: row[1] for n, row in _rows(registry, _CONSUMED_TABLES).items()}


@pytest.mark.parametrize("partner", _PARTNERS)
def test_every_declared_name_exists_in_the_registry_with_the_class_we_treat_it_as(partner):
    """C-57: a rename or reclassification upstream must not be silent here."""
    repo = require_sibling("views-appwrite")
    declared = _declared_classes(_registry_current(repo))
    _, _, expected_class = _PARTNER_ENV[partner]

    missing = sorted(n for n in expected_class if n not in declared)
    assert not missing, (
        f"[{partner}] names this package requires are absent from the Appwrite Seam "
        f"Contract's registry: {missing}. Either the registry retired them or this "
        "module invented them; the registry is the authority."
    )
    misclassified = {
        n: (expected, declared[n])
        for n, expected in expected_class.items()
        if declared[n] != expected
    }
    assert not misclassified, (
        f"[{partner}] class mismatch (expected, registry) {misclassified}. Class is "
        "DECLARED by the registry, never inferred from a name's prefix — a coordinate "
        "treated as a secret (or the reverse) is a redaction bug waiting to happen."
    )


@pytest.mark.parametrize("partner", _PARTNERS)
def test_the_pinned_commit_declares_the_pinned_version(partner):
    """The pair is a claim, and until now nothing checked it.

    ``appwrite_env.py`` declares a version AND a commit, and the old drift check's own
    message said *"Do not bump one alone — the pair is the claim."* That sentence lived
    only inside an error string: no test compared the two. Someone could bump either
    alone and the whole suite stayed green, leaving a pin that names an edition nobody
    published.

    Verified 2026-08-11: ``fcf32c9`` does declare ``1.4.4`` — true by luck, not by check.

    Both sides of the *comparison* are frozen, so upstream editing the registry cannot
    change its verdict. It still needs the sibling checkout to read the pinned blob, so a
    missing or degraded clone reddens it — the check that runs with no sibling at all is
    ``test_the_docstring_states_the_same_edition_the_constants_declare``.
    """
    repo = require_sibling("views-appwrite")
    module = _PARTNER_ENV[partner][0]
    pinned = _registry_at(repo, module.SEAM_CONTRACT_COMMIT)
    assert pinned["meta"]["version"] == module.SEAM_CONTRACT_VERSION, (
        f"[{partner}] the pin is internally inconsistent: commit "
        f"{module.SEAM_CONTRACT_COMMIT} declares registry v{pinned['meta']['version']}, "
        f"but SEAM_CONTRACT_VERSION says v{module.SEAM_CONTRACT_VERSION}. One of the two "
        "was bumped alone. The pair is the claim — fix whichever is wrong."
    )


def test_every_table_in_the_registry_is_classified_here():
    """A table nobody classified is an upstream change nobody looked at.

    This replaces the old edition-equality check, and it is worth being precise about
    what that check was really doing. It compared version *strings*, so it fired on every
    edition — five in four days, four of them recording console observations that carried
    no obligation for anyone here (register C-86). A guard that cries wolf gets bumped
    reflexively, which is how its one real firing goes unread.

    But it did have a real job underneath the noise, and this is that job. On 2026-08-10
    the registry grew a ``[contract.*]`` table carrying a live obligation for this
    repository — the ADR-017 delivery-label mirror — and the edition check was the *only*
    mechanism here that noticed, because ``_declared_classes`` parses three tables and
    was silently ignoring four.

    **Directional on purpose.** Every table upstream must be classified; only the tables
    we depend on must exist. An IGNORED table disappearing is not our business, so it is
    silent, while a new, unclassified one is a red build with something to do. Two such events in the registry's life so far, and this
    repository needed to see both.

    *(An earlier draft illustrated the silent case with v1.5.1's removal of
    ``[unmodelled]``. That was wrong — ``unmodelled`` was never in the partition, so it
    would have been a red build demanding classification, not a silent pass.)*
    """
    repo = require_sibling("views-appwrite")
    registry = _registry_current(repo)

    unclassified = _unclassified_tables(registry)
    assert not unclassified, (
        f"the registry has table(s) this repository has never classified: "
        f"{unclassified}. Decide what each one is — CONSUMED (we read it), MIRRORED (its "
        "values live in our source), or IGNORED (with a reason) — and add it to "
        "_TABLE_ROLE. A new table is how an obligation arrives; `[contract.*]` arrived "
        "exactly this way and only a noisy version check happened to catch it."
    )
    vanished = _missing_dependencies(registry)
    assert not vanished, (
        f"table(s) this repository depends on are gone from the registry: {vanished}. "
        "Either they were retired upstream and this package must stop reading them, or "
        "the file being read is not the registry."
    )


@pytest.mark.parametrize("partner", _PARTNERS)
def test_nothing_this_repo_reads_has_changed_since_the_pin(partner):
    """The drift check, matching on the facts rather than on the edition label.

    ADR-014 §3: when a guard fires on something legitimate, ask whether the *matching* is
    wrong before you narrow the scope. The old check matched on ``meta.version``, which
    is a label for "anything at all changed". This matches on the rows this package
    actually declares, compared between the edition we pinned and the edition upstream
    has now.

    **Fires on:** a rename, a reclassification, a removal, a valueless row gaining a
    value — and on **rotation**, which is the one no other check in this file can see. A
    rotated bucket id keeps its name and its class, so names-and-classes passes while
    every delivery goes somewhere else. The no-copy rule forbids writing the expected
    values into this repository, so the pinned edition is the only lawful baseline for
    that comparison.

    **Silent through:** prose edits, ``[meta]`` bumps, and rows belonging to anyone else.
    Measured across the real v1.4.4 -> v1.5.2 window (three editions, one week): green.

    **The stopping rule, because this check has been widened once already.** It fires on
    exactly one condition: *a row named in this partner's* ``expected_class`` *differs
    between the pinned edition and the sibling's* ``main``.

    Any proposal to widen it must state two things: which delivery failure it prevents,
    **and its false-alarm surface measured against the live registry**. If that surface
    includes rows this package does not read, it is refused. (An earlier version of this
    rule asked instead whether ``assert_env_declared`` already prevented the failure at
    run time. That rule is wrong in both directions: an unadopted upstream coordinate is
    not prevented by it, so arrival detection would pass — and a removed coordinate *is*
    caught by it, so the removal detection this check does perform would fail.)

    An arrival half failed the surface test and was deleted (#245): it compared every row
    of every depended-on table, and measured, each partner reads 13 of 25 while 6 belong
    to no repository here. It defended itself by claiming ``[contract.*]``
    "arrived exactly this way and nothing else here would have seen it" — false at table
    granularity, where ``test_every_table_in_the_registry_is_classified_here`` catches it.

    **What that deletion costs, stated rather than implied.** A coordinate views-appwrite
    issues *for this package* is now silent until a human reads the registry — no test, no
    run-time assert, nothing. So is a second ``[contract.*]`` row for a future partner.
    That is the accepted price of not being reddened by every unrelated row, and it is
    carried in register C-90 rather than here.
    """
    repo = require_sibling("views-appwrite")
    module, _, expected_class = _PARTNER_ENV[partner]
    pinned = _registry_at(repo, module.SEAM_CONTRACT_COMMIT)
    current = _registry_current(repo)

    names = set(expected_class)
    then, now = _projection(pinned, names), _projection(current, names)

    changed = _describe_changes(then, now, names)
    assert not changed, (
        f"[{partner}] the registry changed something this package reads, since the "
        f"edition it was verified against (v{module.SEAM_CONTRACT_VERSION}, commit "
        f"{module.SEAM_CONTRACT_COMMIT}): {changed}. Re-verify this module's declaration "
        "against the current edition, then move SEAM_CONTRACT_VERSION and "
        "SEAM_CONTRACT_COMMIT together. If a value rotated, the delivery is pointing "
        "somewhere else until the launcher's environment is updated too."
    )


@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_the_docstring_states_the_same_edition_the_constants_declare(partner):
    """The module says the edition twice — in prose and in a constant. Only one is checked.

    Both `appwrite_env.py` docstrings name the registry edition in a sentence
    (*"That pin is registry v1.4.1"*) beside the constant that declares it. The drift
    detector reads the constant, so on 2026-08-05 the pins moved to v1.4.4 with both
    guards green and both docstrings still saying v1.4.1 — a reader following the prose
    would have checked their coordinates against a superseded edition.

    This is the same defect the register carries as C-80 and C-82: a claim in prose next
    to a fact in code, with a guard on the fact only. Cheap to close here because the
    prose states the value in a fixed form, so the two can simply be compared.
    """
    module = _PARTNER_ENV[partner][0]
    stated = re.findall(r"registry \*\*v([\d.]+)\*\*", module.__doc__ or "")
    assert stated, (
        f"{partner}/appwrite_env.py's docstring no longer states the registry edition in "
        "the form this guard reads. If the sentence was reworded, reword the pattern too "
        "— do not delete the check, or the prose goes unguarded again."
    )
    assert set(stated) == {module.SEAM_CONTRACT_VERSION}, (
        f"[{partner}] the docstring says registry v{'/v'.join(sorted(set(stated)))} but "
        f"SEAM_CONTRACT_VERSION declares v{module.SEAM_CONTRACT_VERSION}. The constant is "
        "what the drift detector checks, so the prose is the half that rots silently."
    )


@pytest.mark.parametrize("partner", _PARTNERS)
def test_the_docstring_url_points_at_the_commit_the_constant_declares(partner):
    """The docstring publishes a blob URL. Its sha is a third copy of the pin, unguarded.

    The neighbouring test compares the docstring's *version*; nothing compared its *sha*.
    That is how an annotated tag reached the pin: git peeled it, every check passed, and
    two public modules published a URL returning 404 three lines above the sentence "a
    pinned URL does not rot". Third time this class has bitten — register C-57.
    """
    module = _PARTNER_ENV[partner][0]
    urls = re.findall(
        r"views-appwrite/blob/([0-9a-f]{7,40})/docs/ADRs/platform/coordinate_registry\.toml",
        module.__doc__ or "",
    )
    assert urls, (
        f"{partner}/appwrite_env.py's docstring no longer publishes a registry blob URL in "
        "the expected form. If the URL moved, teach this test its new shape — do not delete "
        "the check, or the sha goes unguarded again."
    )
    wrong = sorted({u for u in urls if not module.SEAM_CONTRACT_COMMIT.startswith(u[:7])})
    assert not wrong, (
        f"[{partner}] the docstring's blob URL names commit(s) {wrong} while "
        f"SEAM_CONTRACT_COMMIT declares {module.SEAM_CONTRACT_COMMIT}. A reader following "
        "that link reads a different edition from the one this module was verified against, "
        "and if the sha is not a commit at all the link 404s."
    )


@pytest.mark.parametrize("partner", _PARTNERS)
def test_the_pinned_commit_is_reachable_from_the_contract_repos_main(partner):
    """Existence is not reachability, and that distinction cost a merged PR (#196).

    S3 pinned a commit resolved with ``rev-parse HEAD`` on a views-appwrite checkout
    that happened to be sitting on an unmerged branch. The commit existed. Both cited
    files existed at it. Every check anyone had written passed. It had never reached
    ``main``, declared a version that was never ratified, and was withdrawn.
    """
    repo = require_sibling("views-appwrite")
    commit = _PARTNER_ENV[partner][0].SEAM_CONTRACT_COMMIT
    if not git_output(repo, "cat-file", "-t", commit):
        pytest.skip(
            f"{commit} is not in the local views-appwrite checkout — run `git fetch` "
            "there; a stale clone cannot answer whether the pin reached main"
        )
    assert commit_is_on_main(repo, commit), (
        f"[{partner}] the pinned commit {commit!r} is not an ancestor of "
        "views-appwrite's main. A "
        "pin taken from a working copy's HEAD can land on an unmerged branch — that is "
        "#196, verbatim. Re-pin from `git rev-parse --short origin/main`."
    )


def test_the_pinned_reader_refuses_every_way_a_baseline_can_be_wrong(tmp_path):
    """Each refusal branch, against a scratch repository built to trigger it.

    The first version of this test used a bogus sha against *this* repository — where the
    registry path does not exist at any ref, so a nonsense sha and ``HEAD`` failed
    identically. It proved the helper rejects *something*, not that it rejects an
    unreadable **pin**, and deleting the empty-file and anchor branches left it green.

    Every branch here is genuinely reachable, and each is the shape of a real accident:
    a pin blanked by a bad edit, a pin pointing at a branch, a pin naming an annotated
    tag, a file emptied upstream, a file that parses but is not the registry.
    """
    import subprocess as sp

    def git(*args):
        return sp.run(["git", "-C", str(tmp_path), *args], capture_output=True, text=True, check=True)

    git("init", "-q")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    target = tmp_path / _REGISTRY_RELPATH
    target.parent.mkdir(parents=True)

    def commit(text: str, message: str) -> str:
        target.write_text(text)
        git("add", "-A")
        git("commit", "-q", "-m", message)
        return git("rev-parse", "--short", "HEAD").stdout.strip()

    good = commit('[meta]\nversion = "9.9.9"\n\n[connection.X]\nclass = "connection"\n', "good")
    empty = commit("", "empty")
    anchorless = commit('[target.X]\nclass = "target"\n', "no meta, no connection")
    git("tag", "-a", "v1", "-m", "annotated")

    assert _registry_at(tmp_path, good)["meta"]["version"] == "9.9.9", (
        "the reader must accept a well-formed registry, or the refusals below prove nothing"
    )

    with pytest.raises(_RegistryReadError, match="does not resolve to a commit"):
        _registry_at(tmp_path, "")          # a blanked pin reads the INDEX
    with pytest.raises(_RegistryReadError, match="annotated TAG|does not start with it"):
        _registry_at(tmp_path, "v1")        # a tag object: git peels it, the URL 404s
    with pytest.raises(_RegistryReadError, match="is EMPTY"):
        _registry_at(tmp_path, empty)       # exits 0, stdout empty
    with pytest.raises(_RegistryReadError, match="no meta.version or no"):
        _registry_at(tmp_path, anchorless)  # parses, but is not the registry
    with pytest.raises(_RegistryReadError, match="does not resolve to a commit"):
        _registry_at(tmp_path, "0" * 40)    # a pin that names nothing


def test_the_role_vocabulary_is_closed():
    """A typo in a role string used to silently narrow a security scan.

    ``_TABLE_ROLE``'s values drive which sections the no-copy check reads. Mistyping
    ``"CONSUMED"`` dropped `target` from that scan — twelve coordinate values to two —
    with nothing objecting, while also narrowing what counts as a dependency. Roles are
    now a closed set, asserted.
    """
    unknown = sorted({r for r in _TABLE_ROLE.values() if r not in _ROLES})
    assert not unknown, (
        f"unknown role(s) in _TABLE_ROLE: {unknown}. Roles drive which sections the "
        f"no-copy scan reads; a typo here silently narrows it. Use one of {_ROLES}."
    )
    assert _CONSUMED_TABLES, "no table is classified CONSUMED — every row check reads nothing"


def test_the_table_partition_would_catch_a_new_table_and_a_vanished_one():
    """Calls the production predicates, so neutering them fails here.

    The first version of this test re-typed the set arithmetic inline. Mutation-proven
    afterwards: replacing the real computations with ``[]`` left the guard accepting any
    upstream registry forever, and this proof still passed. It detected nothing, which is
    ADR-014 §2 exactly — and it was the ONLY thing claiming the table check bites.

    The asymmetry is the design and is asserted in both directions: an unclassified table
    fires, a vanished IGNORED table does not.
    """
    base = {name: {} for name in _TABLE_ROLE}

    assert _unclassified_tables(base | {"brand_new_table": {}}) == ["brand_new_table"], (
        "a table nobody classified went unnoticed — that is how `[contract.*]` arrived"
    )
    assert not _unclassified_tables(base), "the real registry's tables must all classify"

    assert _missing_dependencies({k: v for k, v in base.items() if k != "target"}) == ["target"], (
        "a table this package reads rows out of vanished and the check did not object"
    )
    assert not _missing_dependencies({k: v for k, v in base.items() if k != "excluded"}), (
        "an IGNORED table disappearing must NOT fire (ADR-014 §3: prefer the false "
        "negative to the false alarm)"
    )


@pytest.mark.parametrize("partner", _PARTNERS)
def test_the_drift_check_would_catch_a_rotation_that_names_and_classes_cannot(partner):
    """Rotation is why the projection carries ``value`` — proven through the real code.

    The first version of this test asserted ``then != now`` on dicts it built itself.
    Mutation-proven afterwards: making the production comparison ignore ``value`` — which
    is *literally* "names and classes cannot see a rotation", the thing this test exists
    to disprove — left both the proof and the check green, while a rotated bucket id
    shipped every delivery to the wrong place. So it now calls ``_describe_changes``, the
    same function the check calls.

    Runs without a sibling, so it holds on every machine rather than only where
    views-appwrite happens to be checked out.
    """
    _, own_store, expected_class = _PARTNER_ENV[partner]
    canary = own_store[0]
    names = set(expected_class)

    def edition(value: str) -> dict:
        return {
            "meta": {"version": "0.0.0-fixture"},
            "connection": {"APPWRITE_ENDPOINT": {"class": "connection", "value": "e"}},
            "target": {canary: {"class": "target", "value": value}},
        }

    was, rotated = "at-the-pin", "after-rotation"
    then = _projection(edition(was), names)
    now = _projection(edition(rotated), names)

    assert then[canary][:2] == now[canary][:2], (
        "this fixture must differ ONLY in the value, or it is not proving what it claims"
    )
    changed = _describe_changes(then, now, names)
    assert canary in changed, (
        f"[{partner}] a rotated value went unnoticed. Name and class are identical on "
        "both sides, so nothing else in this file can see it."
    )
    assert "value:" in changed[canary], (
        f"[{partner}] the report must name the FIELD that moved, or a maintainer reading "
        "the failure cannot tell a rotation from a reclassification."
    )
    # Both sides, from the fixture's own variables — the rotated one was never checked.
    for side in (was, rotated):
        assert side not in changed[canary], (
            f"[{partner}] the report printed the {side!r} value. It must name the field "
            "and never the value: this repository is public, its CI logs are "
            "world-readable, and they cannot be redacted afterwards."
        )


@pytest.mark.parametrize("partner", _PARTNERS)
def test_the_drift_check_is_silent_on_a_row_this_partner_does_not_read(partner, monkeypatch):
    """The stopping rule above, as a check rather than a paragraph.

    Paired with ``test_the_drift_check_fires_when_a_row_this_partner_reads_rotates``,
    which is the positive direction through the same harness. Neither is optional: alone,
    this one is a check that can only pass, and alone the twin says nothing about what the
    check ignores.

    An earlier version of this docstring vouched for the two proofs either side — "rotation
    fires, a rename fires" — and neither is about this check. One calls the helper
    underneath it; the other belongs to the class check. That is this file's own recurring
    defect (C-80, C-82), so the vouching is gone and the twin is real.

    **It drives the real check**, through the real registry readers, rather than calling
    the projection helpers underneath it. A first version called ``_describe_changes``
    directly and was worthless: re-adding the deleted arrival half to the check left the
    whole suite green, because that half never lived in the helper this was asking. A
    guard has to be pointed at the thing it claims to guard.
    """
    expected_class = _PARTNER_ENV[partner][2]
    targets = sorted(n for n, cls in expected_class.items() if cls == "target")
    assert targets, (
        f"[{partner}] declares no coordinate of class 'target', so this fixture has "
        "nothing to file under [target] and would prove nothing. (An earlier version "
        "asserted that the chosen name's class was 'target' — true by construction, "
        "since the name was selected by that condition. A proof that cannot fail is the "
        "defect this entry's own C-90 records.)"
    )
    mine = targets[0]

    pinned = {
        "meta": {"version": "0.0.0-fixture"},
        "connection": {"APPWRITE_ENDPOINT": {"class": "connection", "value": "e"}},
        "target": {mine: {"class": "target", "value": "unchanged"}},
    }
    # The same registry, plus one coordinate belonging to another repository.
    current = {**pinned, "secret": {"SOMEBODY_ELSES_API_KEY": {"class": "secret"}}}

    here = sys.modules[__name__]
    monkeypatch.setattr(here, "require_sibling", lambda name: Path("/nonexistent"))
    monkeypatch.setattr(here, "_registry_at", lambda repo, ref: pinned)
    monkeypatch.setattr(here, "_registry_current", lambda repo: current)

    test_nothing_this_repo_reads_has_changed_since_the_pin(partner)


@pytest.mark.parametrize("partner", _PARTNERS)
def test_the_drift_check_fires_when_a_row_this_partner_reads_rotates(partner, monkeypatch):
    """The positive twin of the silence guard, through the same real check.

    Without this, the check's entire ``assert not changed`` could be deleted and the suite
    would stay green — measured. Its two apparent proofs are not about it: the rotation
    proof above calls ``_describe_changes``, the helper underneath, and the rename proof
    calls ``_declared_classes``, which belongs to a different check altogether. So the
    silence guard was the only test driving this one, and a guard that can only pass is
    the same defect as a guard pointed at the wrong subject.
    """
    targets = sorted(n for n, cls in _PARTNER_ENV[partner][2].items() if cls == "target")
    assert targets, f"[{partner}] declares no 'target' coordinate to rotate"
    mine = targets[0]

    pinned = {
        "meta": {"version": "0.0.0-fixture"},
        "connection": {"APPWRITE_ENDPOINT": {"class": "connection", "value": "e"}},
        "target": {mine: {"class": "target", "value": "at-the-pin"}},
    }
    rotated = {**pinned, "target": {mine: {"class": "target", "value": "after-rotation"}}}

    here = sys.modules[__name__]
    monkeypatch.setattr(here, "require_sibling", lambda name: Path("/nonexistent"))
    monkeypatch.setattr(here, "_registry_at", lambda repo, ref: pinned)
    monkeypatch.setattr(here, "_registry_current", lambda repo: rotated)

    with pytest.raises(AssertionError, match=mine):
        test_nothing_this_repo_reads_has_changed_since_the_pin(partner)


@pytest.mark.parametrize("partner", _PARTNERS)
def test_the_drift_check_would_catch_a_rename(partner):
    """A gated test that cannot fail is decoration — so prove this one bites in CI.

    Runs with **no** views-appwrite checkout: a synthetic registry with one name
    renamed and one reclassified, fed to the same comparison the gated tests use.

    Parametrised over partners for the reason the whole file now is: a detector proven
    against one partner's coordinates is not proven against another's, and the gated
    checks skip on any machine without a views-appwrite checkout — so this is the only
    proof that runs everywhere.
    """
    module, own_store, expected_class = _PARTNER_ENV[partner]
    # The partner's own outbound bucket id — a `target` in the real registry, which is
    # what makes reclassifying it to `secret` the meaningful mutation.
    canary = own_store[0]

    registry = {
        "meta": {"version": module.SEAM_CONTRACT_VERSION},
        "connection": {"APPWRITE_ENDPOINT": {"class": "connection"}},
        "target": {canary: {"class": "secret"}},  # reclassified
        "secret": {"APPWRITE_DATASTORE_API_KEY": {"class": "secret"}},
    }
    declared = _declared_classes(registry)

    assert expected_class[canary] == "target", (
        f"{canary} is not classified as a target here, so reclassifying it below is "
        "not the mutation this test believes it is"
    )
    assert "APPWRITE_DATASTORE_PROJECT_ID" not in declared, "fixture should omit it"
    missing = sorted(n for n in expected_class if n not in declared)
    assert missing, "the detector reported no missing names against a registry that omits most"

    mismatched = [
        n for n, expected in expected_class.items()
        if n in declared and declared[n] != expected
    ]
    assert canary in mismatched, (
        f"[{partner}] a target reclassified as a secret went unnoticed — that is the "
        "case where getting it wrong leaks or hides a value"
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

    **Names coordinates, never values** — including in this docstring. pytest prints the
    failing function's source, so a value written here publishes on exactly the event the
    check exists to catch (register C-89).

    The axis is **exact equality on string constants**, not statement shape: it catches
    dict values and keyword arguments — ``AppwriteConfig(bucket_id=...)`` is how every
    store is configured — while a function name is not a ``Constant`` and docstrings are
    excluded outright. Two narrower drafts and their false positives are in register
    C-57; three values that cannot be told from ordinary code at all are in C-97.
    """
    # `require_sibling`, like every other reader in this file. The hand-rolled skip that
    # stood here said only "checkout not found — set VIEWS_APPWRITE", which is the
    # degraded message `require_sibling` exists to replace: it names the variable but not
    # the conventional path, so a contributor can watch it skip and not run it. Being the
    # last call site off the shared path is how a rule ends up with two behaviours.
    repo = require_sibling("views-appwrite")
    registry = _registry_current(repo)
    # Scoped by the declared partition, NOT by an inline tuple — so a new table cannot
    # be swept in by a one-word edit, and `contract` cannot be swept in at all.
    #
    # `[contract.*]` values are MIRRORED: ADR-017 §5 requires them to appear in this
    # package's source, because we write them onto every upload. Banning them here would
    # forbid the thing the contract obliges. That is not an exception to "never copy a
    # coordinate" — it is a different class, declared upstream: the registry's own header
    # says no reader scans `[contract.*]`, so no value there ever reaches a process
    # environment. The no-copy rule protects values the launcher supplies; a mirror is
    # the inverse by construction.
    scanned_sections = tuple(
        name for name, role in _TABLE_ROLE.items() if role == "CONSUMED"
    )
    # value -> every coordinate declaring it. A list, because two coordinates may share
    # a value and measured against the live registry two pairs do.
    declared_by_value: dict[str, list[str]] = {}
    for section in scanned_sections:
        for name, body in registry.get(section, {}).items():
            # No length floor: it excluded two five-character coordinates and,
            # measured, removing it keeps the suite green — so it was buying nothing
            # while narrowing a security check.
            if isinstance(body.get("value"), str) and body["value"].strip():
                declared_by_value.setdefault(body["value"], []).append(name)
    values = set(declared_by_value)
    copied = []
    for source in sorted(_PKG.rglob("*.py")):
        tree = _parsed(source)
        docstrings = _docstring_nodes(tree)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and node.value in values
                and id(node) not in docstrings
            ):
                names = ", ".join(sorted(declared_by_value[node.value]))
                copied.append(
                    f"{source.relative_to(_PKG)}:{node.lineno} carries the value "
                    f"declared for {names}"
                )
    # Markdown too — the AST half cannot see a fenced ``bash`` block, and that is exactly
    # where four production-forecasts values sat: in README.md's Configuration section,
    # two lines below the sentence promising they are never copied, in a PUBLIC
    # repository. A guard scoped to `.py` while the rule is about the repository is
    # register C-74's shape (2026-08-03).
    #
    # **What counts as a copy, and what does not.** A first draft flagged any line
    # containing a registry value and immediately fired on a dozen documents that merely
    # *name* a store in prose — a sentence counting stranded documents in the UNFAO
    # bucket, written with the bucket's declared value. That is not a
    # copy; it is a sentence. C-57 recorded the identical false-positive class over `.py`
    # and the identical lesson: when a guard cries wolf, the matching is wrong before the
    # scope is (ADR-014 §3).
    #
    # A copy is a declared NAME assigned a declared VALUE. Both halves are known before
    # the scan starts, so it matches the pair rather than parsing the line and comparing
    # what it captured. Three rounds of blindness came from that parse, all of them the
    # same shape — the pattern described one dialect of markdown (register C-57).
    #
    # The two halves need not correspond: `APPWRITE_X=<value declared for APPWRITE_Y>` is
    # the ordinary copy-paste slip, and is a copy.
    #
    # It stays a syntax match. A value merely *named* in a sentence is not a copy, and a
    # draft that fired on those was deleted for crying wolf (ADR-014 §3, C-57).
    names_alt = "|".join(sorted(_EXPECTED_NAMES))
    values_alt = "|".join(re.escape(v) for v in sorted(values, key=len, reverse=True))
    pair = re.compile(
        rf"""(?<![A-Za-z0-9_])({names_alt})\s*=\s*["'`]?({values_alt})["'`]?(?![A-Za-z0-9_])"""
    )
    tracked = subprocess.run(
        ["git", "-C", str(_REPO), "ls-files", "-z", "*.md"],
        capture_output=True, text=True, check=False, timeout=30,
    ).stdout.split("\0")
    scanned = [_REPO / name for name in tracked if name and (_REPO / name).exists()]
    assert scanned, (
        "git ls-files returned no markdown — the scan would pass over an empty set and "
        "report success (register C-74's shape). If this is not a git checkout, the "
        "guard cannot run and must say so rather than pass."
    )
    for doc in sorted(scanned):
        for number, line in enumerate(doc.read_text().splitlines(), 1):
            # findall, not search: a table row can carry two assignments and the second
            # one used to be invisible.
            for assigned, value in pair.findall(line):
                declares = ", ".join(sorted(declared_by_value[value]))
                copied.append(
                    f"{doc.relative_to(_REPO)}:{number} assigns {assigned} the value "
                    f"declared for {declares}"
                )

    assert not copied, (
        f"coordinate value(s) from the registry are copied into this repo: {copied}. The "
        "registry is referenced, never copied — values reach this package through the "
        "environment the launcher assembles, validated by assert_env_declared. In a "
        "document, write the NAME and leave the value to the launcher."
    )


def test_the_scan_reports_where_a_copy_is_and_never_what_it_is(tmp_path, monkeypatch):
    """C-89: the ``.py`` branch printed the value it forbids, on the one event it fires on.

    Reads the finished message, not the source that built it. The planted world is
    deliberately awkward — two copies, two sections, one short, one in markdown — and each
    element defeats a specific narrowing that a simpler fixture would satisfy. Register
    C-57 and C-89 carry the five mutations this is built against.
    """
    long_value, short_value = "Zq7xVb9KdLm1RnTs3Wy8Pj5Hc2Gf", "Kd7q"
    pkg = tmp_path / "views_postprocessing"
    pkg.mkdir()
    (pkg / "leaky.py").write_text(f'BUCKET_ID = "{long_value}"\n')
    (pkg / "also_leaky.py").write_text(f'ENDPOINT = "{short_value}"\n')
    # And one in markdown, so the second branch is exercised too. Without it, a `break`
    # after the first finding stops the markdown scan entirely and nothing objects —
    # measured, that mutation survived until this line existed.
    (tmp_path / "README.md").write_text(f"APPWRITE_UNFAO_BUCKET_ID={long_value}\n")
    for args in (("init", "-q"), ("add", "-A")):
        subprocess.run(["git", "-C", str(tmp_path), *args],
                       capture_output=True, text=True, check=True, timeout=30)

    here = sys.modules[__name__]
    monkeypatch.setattr(here, "_REPO", tmp_path)
    monkeypatch.setattr(here, "_PKG", pkg)
    monkeypatch.setattr(here, "require_sibling", lambda name: tmp_path)
    monkeypatch.setattr(here, "_registry_current", lambda repo: {
        "target": {"APPWRITE_UNFAO_BUCKET_ID": {"class": "target", "value": long_value}},
        "connection": {"APPWRITE_ENDPOINT": {"class": "connection", "value": short_value}},
    })

    with pytest.raises(AssertionError) as caught:
        test_no_coordinate_value_is_copied_into_this_repo()
    message = str(caught.value)

    for where, coordinate in (
        ("leaky.py", "APPWRITE_UNFAO_BUCKET_ID"),
        ("also_leaky.py", "APPWRITE_ENDPOINT"),
        ("README.md", "APPWRITE_UNFAO_BUCKET_ID"),
    ):
        assert where in message, f"{where}'s copy was not reported at all: {message}"
        assert coordinate in message, f"{coordinate} is not named: {message}"
    for value in (long_value, short_value):
        assert value not in message, (
            "THE SCAN PUBLISHED THE VALUE IT EXISTS TO HIDE. This repository is public "
            "and its CI logs are world-readable and cannot be redacted afterwards."
        )


def test_a_package_module_that_does_not_parse_is_refused_not_skipped(tmp_path, monkeypatch):
    """A malformed module must fail the scan loudly, never be stepped over: a file that
    both fails to parse and carries a coordinate would otherwise go unreported. Routed
    from #242, where the mutation survived. Register C-57."""
    pkg = tmp_path / "views_postprocessing"
    pkg.mkdir()
    (pkg / "broken.py").write_text("VALUE = 'x'\ndef (:\n")

    here = sys.modules[__name__]
    monkeypatch.setattr(here, "_PKG", pkg)
    monkeypatch.setattr(here, "require_sibling", lambda name: tmp_path)
    monkeypatch.setattr(here, "_registry_current", lambda repo: {
        "target": {"APPWRITE_UNFAO_BUCKET_ID": {"class": "target", "value": "unused"}},
    })

    with pytest.raises(AssertionError, match="does not parse"):
        test_no_coordinate_value_is_copied_into_this_repo()


def test_the_scan_understands_every_assignment_form_this_repo_writes():
    """The stopping rule, as a test: the form list comes from the corpus, not imagination.

    Every line in this repository's own tracked markdown that assigns a declared
    coordinate must be one the matcher can read. A form no document here uses is not a
    gap; a new form is taught in the same change as the document introducing it. Why that
    is the rule, and the four widenings that produced it: register C-57.
    """
    tracked = subprocess.run(
        ["git", "-C", str(_REPO), "ls-files", "-z", "*.md"],
        capture_output=True, text=True, check=False, timeout=30,
    ).stdout.split("\0")
    docs = [_REPO / n for n in tracked if n and (_REPO / n).exists()]
    assert docs, "git ls-files returned no markdown; this rule would pass over nothing"

    assigns = re.compile(
        r"(?<![A-Za-z0-9_])(" + "|".join(sorted(_EXPECTED_NAMES)) + r")\s*=\s*(\S)"
    )
    unparsed = []
    for doc in docs:
        for number, line in enumerate(doc.read_text().splitlines(), 1):
            for name, _first in assigns.findall(line):
                # The matcher is the pair form used by the scan above. If it can find the
                # name-equals shape but not the whole assignment, either the value is not
                # a coordinate (fine) or the form defeats the matcher (not fine).
                if not re.search(
                    rf"""(?<![A-Za-z0-9_]){re.escape(name)}\s*=\s*["'`]?\S""", line
                ):
                    unparsed.append(f"{doc.relative_to(_REPO)}:{number} ({name})")

    assert not unparsed, (
        f"tracked markdown assigns a coordinate in a form the no-copy matcher cannot "
        f"read: {unparsed}. Teach the matcher this form in the same change as the "
        "document that introduced it — that is the stopping rule, and it is why the "
        "form list is derived from this repository's own corpus rather than invented."
    )
