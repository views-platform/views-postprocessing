"""The launch declarations are asserted, not inferred (S1 / #149; register C-63).

Until #149 this package inferred its delivery mode from the *absence* of config
keys: `configs.get("wire_contract")` returning `None` because a launcher never
mentioned it was indistinguishable from a deliberate `False`, and either quietly
selected a pandas path kept "until run 0 proves the contract path live" and never
removed. Two independent axes gave four delivery modes; production used one; the
other three were reachable only by omission.

These tests pin the replacement: **one path, and a refusal that names what the
launcher left out.** They are the mechanical form of ADR-003 (authority of
declarations over inference) applied to the launch config, mirroring
`test_env_declaration.py`, which does the same job for the environment.

`launch_config` is dependency-light by design — no pipeline-core, no pandas, no
frames — so these run anywhere.
"""

import pytest

from views_postprocessing.contract import launch_config
from views_postprocessing.contract.launch_config import LaunchConfigError


# ── the forecast axis: wire_contract ────────────────────────────────────────


def test_missing_wire_contract_raises_naming_the_key():
    """The key's absence must be an error, not a silent route to a retired path."""
    with pytest.raises(LaunchConfigError, match="wire_contract"):
        launch_config.assert_contract_mode({})


def test_wire_contract_false_raises_too():
    """An explicit False is not a request for the old path — it no longer exists."""
    with pytest.raises(LaunchConfigError, match="wire_contract"):
        launch_config.assert_contract_mode({"wire_contract": False})


def test_the_refusal_says_there_is_no_fallback():
    """A launcher author must not read the error as 'set it False instead'."""
    with pytest.raises(LaunchConfigError) as excinfo:
        launch_config.assert_contract_mode({})
    message = str(excinfo.value)
    assert "no fallback" in message
    assert "#149" in message  # where the retired path went, for the reader


def test_the_refusal_is_logged_before_it_is_raised(caplog):
    """ADR-008: structural failures are logged persistently AND raised.

    Not belt-and-braces — a refused launch must leave a record even if the raise is
    swallowed further up the pipeline framework, because the message is the only
    diagnostic a launcher author gets.
    """
    with caplog.at_level("ERROR"):
        with pytest.raises(LaunchConfigError):
            launch_config.assert_contract_mode({})
    assert any(r.levelname == "ERROR" for r in caplog.records), (
        "the refusal was raised without being logged (ADR-008)"
    )
    assert "wire_contract" in caplog.text


def test_the_format_refusal_is_logged_too(caplog):
    with caplog.at_level("ERROR"):
        with pytest.raises(LaunchConfigError):
            launch_config.assert_frame_native_historical("dataframe")
    assert any(r.levelname == "ERROR" for r in caplog.records)


def test_declared_contract_mode_passes():
    launch_config.assert_contract_mode({"wire_contract": True})


def test_other_keys_are_not_consulted():
    """Only the declared key decides. No inference from neighbouring config."""
    with pytest.raises(LaunchConfigError):
        launch_config.assert_contract_mode(
            {"wire_upload_enabled": True, "region": "land_gaul", "ensemble": "rusty_bucket"}
        )


# ── the historical axis: data_format ────────────────────────────────────────


def test_missing_data_format_raises_naming_the_expected_value():
    with pytest.raises(LaunchConfigError, match="feature_frame"):
        launch_config.assert_frame_native_historical(None)


def test_a_different_data_format_raises_and_reports_what_it_saw():
    """The error must name the offending value — a queryset author needs to find it."""
    with pytest.raises(LaunchConfigError) as excinfo:
        launch_config.assert_frame_native_historical("dataframe")
    assert "'dataframe'" in str(excinfo.value)


def test_declared_feature_frame_passes():
    launch_config.assert_frame_native_historical("feature_frame")


# ── the manager actually calls them ─────────────────────────────────────────


@pytest.mark.parametrize("partner", ["unfao", "crafd"])
def test_the_manager_asserts_every_launch_axis(partner):
    """Source-scan: the manager pulls the full pipeline-core framework and cannot be
    imported in every test environment (the repo's standing pattern — see
    `test_env_declaration.py`). What matters is that no axis is left to `.get()`
    with a silent default.

    Parametrised over both partners, and covering `assert_region_declared`, because
    a guard audit removed that call from both managers with the whole suite green:
    the scan read one file and listed two of the three assertions (2026-11-18, ME1).
    """
    from pathlib import Path

    source = (
        Path(__file__).resolve().parent.parent
        / "views_postprocessing" / partner / "managers" / f"{partner}.py"
    ).read_text()

    assert "launch_config.assert_contract_mode(" in source
    assert "launch_config.assert_frame_native_historical(" in source
    assert "launch_config.assert_region_declared(" in source, (
        f"{partner}: the region axis is read by both coverage gates, so a manager "
        "that does not assert it ships a delivery whose gates chose themselves "
        "(C-113)."
    )
    # And the inference it replaced must not survive anywhere.
    assert 'configs.get("wire_contract")' not in source, (
        "the manager still branches on wire_contract — S1 replaced that fork with a "
        "single refusal (C-63)."
    )


# --- C-113: the region is a declaration, not something to omit ---------------------


def test_a_missing_region_is_refused_naming_the_key():
    """The omission that disabled both coverage gates while reading as supported.

    `configs.get("region")` returned None, and None took the same path through
    `delivery.coverage` as a region that is declared but not yet pinned — so a
    delivery shipped with its cell curation and its completeness check both having
    done nothing. Same shape as C-83: the absence of an answer given the shape of
    an answer (ADR-003).
    """
    with pytest.raises(launch_config.LaunchConfigError, match="region"):
        launch_config.assert_region_declared({"wire_contract": True})


@pytest.mark.parametrize("region", [None, "", "   ", 0, False, ["land_gaul"], 7])
def test_a_blank_or_non_string_region_is_refused_too(region):
    # Declared-don't-infer applies to the TYPE as well: a region that is not a
    # non-empty string cannot select a manifest, and must not reach the gates as
    # though it had. (C-123 registers the general version of this gap elsewhere.)
    # `match=` matters: without it this test cannot tell "you declared no region"
    # from "that region is unrecognised", and a check that collapses the two walks
    # through it (guard audit 2026-11-18, mutations MD3/MD4b/MD9).
    with pytest.raises(launch_config.LaunchConfigError, match="did not declare"):
        launch_config.assert_region_declared({"region": region})


def test_the_refusal_distinguishes_itself_from_an_unpinned_region():
    # The message must not send the reader to pin a region that is already declared:
    # the unpinned case is supported and is a different fix.
    with pytest.raises(launch_config.LaunchConfigError) as excinfo:
        launch_config.assert_region_declared({})
    message = str(excinfo.value)
    assert "not yet" in message and "pinned" in message
    assert "stays launchable" in message


def test_a_known_region_passes_whether_or_not_it_is_pinned():
    # africa_me_legacy is deliberately unpinned and MUST stay launchable — the
    # falsification stub that prescribed refusing it would have grounded it.
    assert launch_config.assert_region_declared({"region": "land_gaul"}) is None
    assert launch_config.assert_region_declared({"region": "africa_me_legacy"}) is None


@pytest.mark.parametrize("region", ["lnd_gaul", "land-gaul", "not_pinned_anywhere"])
def test_an_unrecognised_region_is_refused_at_launch(region):
    """Found by review 2026-11-18, and this test replaces one that pinned the defect.

    The line above used to assert that `region: "not_pinned_anywhere"` LAUNCHED. It
    does not any more, and the reason is that a name nobody recognises is not the
    unpinned case: it misses both lookups in `delivery.coverage`, so both gates skip.
    Refusing at launch means the operator hears about a misspelling before any store
    call, not from a run log after the delivery shipped unchecked.
    """
    with pytest.raises(launch_config.LaunchConfigError, match="does not recognise"):
        launch_config.assert_region_declared({"region": region})


def test_the_unrecognised_refusal_names_the_regions_it_knows():
    # So the fix is in the message: either the name is wrong, or the region is new
    # and must be declared in one named place.
    with pytest.raises(launch_config.LaunchConfigError) as excinfo:
        launch_config.assert_region_declared({"region": "lnd_gaul"})
    message = str(excinfo.value)
    assert "land_gaul" in message and "africa_me_legacy" in message
    assert "KNOWN_REGIONS" in message
