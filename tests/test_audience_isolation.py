"""The audience-connection rule, and the one line in the manager that depends on it.

Two halves, and the second half is the one that was missing when this file was first
written (#356 review, 2026-11-27). Nine tests exercised
``contract/audience.assert_audience_is_not_the_shelf`` directly and every one of them
passed with the rule **deleted from the manager**: the whole call could be removed, or its
two project ids transposed, or the checked return value replaced with a fresh
``os.getenv`` of the shelf's name, and the suite stayed green. A rule nothing binds to its
call site is a rule the next refactor silently removes — this repository's register calls
that shape *"a guard that cannot fail"* (cluster O), and it had just registered C-125 for
a different instance of it.

So the manager tests below assert on the ``AppwriteConfig`` actually built, never on the
rule in isolation. They are the ones that fail if the call goes away.
"""

from __future__ import annotations

import pytest

from views_postprocessing.contract.audience import (
    AudienceIsolationError,
    assert_audience_is_not_the_shelf,
)

#: A complete, fictitious audience environment. Values are obviously-fake coordinates: no
#: real project id, bucket id or key appears in this repository's source (C-89 — it is
#: public and its CI logs are world-readable).
_SHELF_PROJECT = "shelf-project-fake"
_SHELF_KEY = "shelf-key-fake"
_AUDIENCE_PROJECT = "audience-project-fake"
_AUDIENCE_KEY = "audience-key-fake"

_FULL_ENV = {
    "APPWRITE_ENDPOINT": "https://appwrite.invalid/v1",
    "APPWRITE_DATASTORE_PROJECT_ID": _SHELF_PROJECT,
    "APPWRITE_DATASTORE_API_KEY": _SHELF_KEY,
    "APPWRITE_CRAFD_PROJECT_ID": _AUDIENCE_PROJECT,
    "APPWRITE_CRAFD_PUBLISHER_API_KEY": _AUDIENCE_KEY,
    "APPWRITE_CRAFD_BUCKET_ID": "crafd-bucket-fake",
    "APPWRITE_CRAFD_BUCKET_NAME": "crafd_bucket",
    "APPWRITE_CRAFD_COLLECTION_ID": "crafd-collection-fake",
    "APPWRITE_CRAFD_COLLECTION_NAME": "crafd",
    "APPWRITE_METADATA_DATABASE_ID": "metadata-database-fake",
    "APPWRITE_METADATA_DATABASE_NAME": "file_metadata",
}


def _isolated(**overrides):
    """Call the rule with a complete, isolated set of values, overriding some."""
    kwargs = dict(
        audience_project_id=_AUDIENCE_PROJECT,
        shelf_project_id=_SHELF_PROJECT,
        audience_credential=_AUDIENCE_KEY,
        shelf_credential=_SHELF_KEY,
        consumer="un_crafd",
    )
    kwargs.update(overrides)
    return assert_audience_is_not_the_shelf(**kwargs)


# --------------------------------------------------------------------------------------
# The rule on its own
# --------------------------------------------------------------------------------------


def test_two_distinct_connections_are_accepted_and_the_checked_value_is_returned():
    assert _isolated() == _AUDIENCE_PROJECT


def test_an_audience_that_resolves_to_the_shelf_is_refused():
    with pytest.raises(AudienceIsolationError, match="SAME project"):
        _isolated(audience_project_id=_SHELF_PROJECT)


def test_surrounding_whitespace_does_not_defeat_the_comparison():
    with pytest.raises(AudienceIsolationError, match="SAME project"):
        _isolated(audience_project_id=f"  {_SHELF_PROJECT}\n")


def test_the_returned_value_is_the_one_that_was_compared_not_the_raw_input():
    """A launcher reading a coordinate from a file hands over a trailing newline.

    The comparison strips before comparing, so an unstripped return would put a value
    into the ``X-Appwrite-Project`` header that this function never checked — failing as
    an invalid header or a 404 deep inside the SDK, after the entire read and transform
    has already run.
    """
    assert _isolated(audience_project_id=f"  {_AUDIENCE_PROJECT}\n") == _AUDIENCE_PROJECT


@pytest.mark.parametrize("absent", [None, "", "   ", 42], ids=["none", "empty", "blank", "non-str"])
def test_an_absent_or_blank_audience_project_is_refused(absent):
    with pytest.raises(AudienceIsolationError, match="no audience project declared"):
        _isolated(audience_project_id=absent)


@pytest.mark.parametrize("absent", [None, "", "   ", b"shelf"], ids=["none", "empty", "blank", "bytes"])
def test_an_absent_shelf_project_is_refused_rather_than_reported_as_isolated(absent, caplog):
    """The polarity C-113 was closed to fix: a gate with a missing input is not a pass.

    The first version of this rule guarded the comparison on the shelf operand alone, so
    an absent shelf skipped the comparison entirely and then logged *"two distinct
    projects"* — a self-certifying success that had compared nothing. A `bytes` shelf id
    whose content equals the audience's is the same hole with a type instead of a blank.
    """
    with pytest.raises(AudienceIsolationError, match="CANNOT BE PROVEN"):
        _isolated(shelf_project_id=absent)
    assert "isolated from the shared shelf" not in caplog.text


def test_two_distinct_projects_sharing_one_credential_are_refused():
    """An Appwrite key authenticates against exactly one project, so one of the two
    connections cannot work — and it would surface as a 401 inside the delivery rather
    than as a refusal naming the coordinate."""
    with pytest.raises(AudienceIsolationError, match="SAME credential"):
        _isolated(audience_credential=_SHELF_KEY)


def test_no_refusal_prints_a_project_id_or_a_credential():
    """C-89: this repository is public and its CI logs are world-readable."""
    secrets = (_SHELF_PROJECT, _SHELF_KEY, _AUDIENCE_KEY)
    cases = (
        {"audience_project_id": _SHELF_PROJECT},
        {"shelf_project_id": None},
        {"audience_credential": _SHELF_KEY},
    )
    for case in cases:
        with pytest.raises(AudienceIsolationError) as caught:
            _isolated(**case)
        message = str(caught.value)
        for secret in secrets:
            assert secret not in message, f"{case} leaked {secret!r}"


def test_the_consumer_name_is_in_every_refusal():
    for case in ({"audience_project_id": None}, {"shelf_project_id": None},
                 {"audience_project_id": _SHELF_PROJECT}, {"audience_credential": _SHELF_KEY}):
        with pytest.raises(AudienceIsolationError) as caught:
            _isolated(**case)
        assert "un_crafd" in str(caught.value)


def test_every_refusal_is_logged_at_error_as_well_as_raised(caplog):
    """ADR-008: *"Logging must occur before or at the point of raising. Logging is not a
    substitute for raising; raising is not a substitute for logging."* Without this, a
    mis-wired connection left the quieter trace of the two — nothing in the persistent log
    on failure, an INFO line on success."""
    import logging

    with caplog.at_level(logging.ERROR):
        with pytest.raises(AudienceIsolationError):
            _isolated(audience_project_id=_SHELF_PROJECT)
    assert [r for r in caplog.records if r.levelno >= logging.ERROR], (
        "the refusal raised but logged nothing at ERROR"
    )


def test_the_project_ids_cannot_be_passed_positionally():
    """Four same-typed strings from four similarly spelled coordinates: a positional call
    site can transpose audience and shelf and still satisfy a symmetric equality check,
    returning the SHELF as the audience project while the rule reports isolation. The
    keyword-only marker makes the slip unexpressible — most importantly for #337, the
    clone this module exists to serve."""
    with pytest.raises(TypeError):
        assert_audience_is_not_the_shelf(  # type: ignore[misc]
            _AUDIENCE_PROJECT, _SHELF_PROJECT, consumer="un_crafd"
        )


# --------------------------------------------------------------------------------------
# The manager — the half that binds the rule to the line that decides the project
# --------------------------------------------------------------------------------------


@pytest.fixture
def audience_env(monkeypatch):
    """A complete CRAF'd environment, with every other ``APPWRITE_`` name removed.

    Removal matters: a maintainer's populated shell has twice made tests in this
    repository pass for the wrong reason (C-81).
    """
    import os

    for name in [k for k in os.environ if k.startswith("APPWRITE_")]:
        monkeypatch.delenv(name, raising=False)
    for name, value in _FULL_ENV.items():
        monkeypatch.setenv(name, value)
    return monkeypatch


def _crafd_manager_module():
    pytest.importorskip(
        "views_pipeline_core",
        reason="the builder constructs a pipeline-core AppwriteConfig; it is a declared "
        "dependency, so this skip means a broken environment rather than a valid one",
    )
    return __import__(
        "views_postprocessing.crafd.managers.crafd",
        fromlist=["_partner_appwrite_config"],
    )


def test_the_built_config_addresses_the_audience_project_and_not_the_shelf(audience_env):
    """The claim #327 clause 2 actually makes, asserted on the object that carries it.

    This is the test that fails if the isolation call is deleted from
    ``_partner_appwrite_config``, if its two project ids are transposed, or if
    ``project_id=`` is quietly repointed at the shelf's coordinate — all three of which
    left the suite green before this existed.
    """
    module = _crafd_manager_module()
    config = module._partner_appwrite_config(model_path=None)

    assert config.project_id == _AUDIENCE_PROJECT
    assert config.project_id != _SHELF_PROJECT
    assert config.credentials == _AUDIENCE_KEY
    assert config.credentials != _SHELF_KEY


def test_the_manager_refuses_when_both_project_coordinates_hold_the_shelf(audience_env):
    """The collision an absence check cannot see, at the call site rather than in a unit.

    Deleting the rule from the manager makes this the failing test, because the refusal is
    the behaviour being asserted — not the rule's own return value.
    """
    audience_env.setenv("APPWRITE_CRAFD_PROJECT_ID", _SHELF_PROJECT)
    module = _crafd_manager_module()
    with pytest.raises(AudienceIsolationError, match="SAME project"):
        module._partner_appwrite_config(model_path=None)


def test_the_manager_refuses_when_both_key_coordinates_hold_the_shelf_key(audience_env):
    audience_env.setenv("APPWRITE_CRAFD_PUBLISHER_API_KEY", _SHELF_KEY)
    module = _crafd_manager_module()
    with pytest.raises(AudienceIsolationError, match="SAME credential"):
        module._partner_appwrite_config(model_path=None)


def test_the_manager_refuses_when_the_shelf_project_is_not_exported(audience_env):
    """``APPWRITE_DATASTORE_PROJECT_ID`` is the isolation check's second operand and is
    now declared on this path. Before that it was asserted only inside a *different*
    function on a *different* path, so a standalone call — a retry tool, a re-delivery, a
    clone exporting the audience names only — reached the check with nothing to compare.
    """
    audience_env.delenv("APPWRITE_DATASTORE_PROJECT_ID", raising=False)
    module = _crafd_manager_module()
    with pytest.raises(EnvironmentError, match="APPWRITE_DATASTORE_PROJECT_ID"):
        module._partner_appwrite_config(model_path=None)


def test_a_trailing_newline_on_the_audience_project_never_reaches_the_client(audience_env):
    """``APPWRITE_CRAFD_PROJECT_ID=$(cat ...)`` is how a launcher acquires a coordinate."""
    audience_env.setenv("APPWRITE_CRAFD_PROJECT_ID", f"{_AUDIENCE_PROJECT}\n")
    module = _crafd_manager_module()
    assert module._partner_appwrite_config(model_path=None).project_id == _AUDIENCE_PROJECT
