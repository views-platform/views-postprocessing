"""The C-94 findability preflight: does the consumer's own query find the delivery?

Two layers, matching how the repo tests every other delivery invariant: the rule on
primitives here, and the wiring — that the manager actually calls it, and calls it
through a store whose injected name filter is suppressed — as declaration checks.

The wiring checks are source reads rather than behavioural ones. Constructing a manager
needs pipeline-core, a views-models path manager and a live Appwrite environment (C-40),
and the properties worth holding are two lines: that the preflight runs only when
something was uploaded, and that it asks under the DECLARED consumer name rather than
the path manager's (C-77).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.conftest import PARTNER_PACKAGES
from views_postprocessing.delivery import findability

_REPO = Path(__file__).resolve().parent.parent


def test_a_found_document_passes():
    findability.assert_findable("file-abc", consumer_name="un_fao", category="forecast")


def test_nothing_found_is_refused():
    with pytest.raises(findability.DeliveryNotFindableError):
        findability.assert_findable(None, consumer_name="un_fao", category="forecast")


def test_the_refusal_names_the_query_that_found_nothing():
    with pytest.raises(findability.DeliveryNotFindableError) as excinfo:
        findability.assert_findable(None, consumer_name="un_fao", category="historical")
    message = str(excinfo.value)
    assert "un_fao" in message, "the refusal must name the consumer name it queried by"
    assert "historical" in message, "and which leg was invisible"
    assert "INVISIBLE" in message, (
        "the message must say the delivery is invisible rather than degraded — that "
        "distinction is ADR-013 §4.1a and it is what tells an operator to quarantine"
    )


def test_an_empty_string_file_id_is_not_treated_as_found():
    """`None` is the documented 'no match', but a store returning '' is not a find.

    pipeline-core's `get_latest_file_id` warns and returns None on no match, and warns
    again if a match is missing its `fileId` field — in which case it returns whatever
    `.get("fileId", None)` produced. A falsy id is not something to deliver on.
    """
    with pytest.raises(findability.DeliveryNotFindableError):
        findability.assert_findable("", consumer_name="un_fao", category="forecast")


@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_the_manager_verifies_only_when_something_was_uploaded(partner):
    source = (_REPO / "views_postprocessing" / partner / "managers" / f"{partner}.py").read_text()
    save = source[source.index("def _save_contract"):source.index("    def _save(")]
    assert "_assert_delivery_is_findable(" in save, (
        f"{partner}'s _save_contract no longer runs the C-94 preflight, so an upload "
        "that lands somewhere the consumer cannot see it reports success (C-94)."
    )
    call = save.index("_assert_delivery_is_findable(")
    interlock = save.index("if upload_enabled:")
    assert interlock < call, (
        f"{partner} runs the findability preflight outside the upload interlock. With "
        "the interlock holding nothing was uploaded, so the check would refuse every "
        "staged run for the absence of a delivery nobody made."
    )


@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_the_preflight_queries_the_declared_name_not_the_path_managers(partner):
    """C-77: the two are equal today by coincidence, and only one is a declaration."""
    source = (_REPO / "views_postprocessing" / partner / "managers" / f"{partner}.py").read_text()

    assert "_build_partner_read_store" in source, (
        f"{partner} lost the read-back store builder; without it "
        "`get_latest_file_id` merges the path manager's model name into the query"
    )
    builder = source[source.index("def _build_partner_read_store"):source.index("class ")]
    assert "store.model_path = None" in builder, (
        f"{partner}'s read-back store no longer suppresses pipeline-core's automatic "
        "`name == model_name` filter, so the preflight verifies the views-models "
        "directory name instead of the declared consumer name. A rename there would "
        "leave this check green while the delivery went dark (C-77)."
    )

    preflight = source[source.index("def _assert_delivery_is_findable"):]
    assert "product.CONSUMER_DOCUMENT_NAME" in preflight, (
        f"{partner}'s preflight must query the DECLARED consumer name (C-77)"
    )
    assert "_build_partner_read_store" in preflight, (
        f"{partner}'s preflight must use the suppressed-injection store, not the "
        "upload store, or it asks the wrong question"
    )
    for category in ('"forecast"', '"historical"'):
        assert category in preflight, (
            f"{partner}'s preflight no longer checks {category}. Both legs are verified "
            "separately because a run with one leg missing is invisible in half, and "
            "the historical leg is the one that stranded in run-0 (C-79)."
        )
