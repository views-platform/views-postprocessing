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

import ast
from pathlib import Path

import pytest

from tests.conftest import PARTNER_PACKAGES
from views_postprocessing.delivery import findability

_REPO = Path(__file__).resolve().parent.parent


def _calls_body(body) -> set[str]:
    """Names called anywhere inside a list of statements."""
    found: set[str] = set()
    for stmt in body:
        for c in ast.walk(stmt):
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Name):
                found.add(c.func.id)
    return found


def _function_source(source: str, name: str) -> str:
    """Exactly one function's source.

    Slicing to end-of-file instead would let any later occurrence in the module satisfy
    these checks — the assertion would pass for text that is not in the function at all.
    """
    fn = next(
        n for n in ast.walk(ast.parse(source))
        if isinstance(n, ast.FunctionDef) and n.name == name
    )
    return "\n".join(source.splitlines()[fn.lineno - 1:fn.end_lineno])


def test_a_found_document_passes():
    findability.assert_findable(
        "file-abc", expected_file_id="file-abc", consumer_name="un_fao", category="forecast"
    )


def test_nothing_found_is_refused():
    with pytest.raises(findability.DeliveryNotFindableError):
        findability.assert_findable(
            None, expected_file_id="x", consumer_name="un_fao", category="forecast"
        )


def test_the_refusal_names_the_query_that_found_nothing():
    with pytest.raises(findability.DeliveryNotFindableError) as excinfo:
        findability.assert_findable(
            None, expected_file_id="x", consumer_name="un_fao", category="historical"
        )
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
        findability.assert_findable(
            "", expected_file_id="x", consumer_name="un_fao", category="forecast"
        )


@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_the_manager_verifies_only_when_something_was_uploaded(partner):
    source = (_REPO / "views_postprocessing" / partner / "managers" / f"{partner}.py").read_text()
    tree = ast.parse(source)
    save = next(
        n for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "_save_contract"
    )

    def _calls(node):
        return {
            c.func.id
            for c in ast.walk(node)
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
        }

    assert "_assert_delivery_is_findable" in _calls(save), (
        f"{partner}'s _save_contract no longer runs the C-94 preflight, so an upload "
        "that lands somewhere the consumer cannot see it reports success (C-94)."
    )
    # Structural, not textual: an ordering check on substrings stays green if the call
    # is moved into the `else` branch or dedented out of the guard entirely — which is
    # the regression this message claims to prevent.
    guarded = [
        n for n in ast.walk(save)
        if isinstance(n, ast.If)
        and isinstance(n.test, ast.Name)
        and n.test.id == "upload_enabled"
        and "_assert_delivery_is_findable" in _calls_body(n.body)
    ]
    assert guarded, (
        f"{partner} runs the findability preflight outside the `if upload_enabled:` "
        "body. With the interlock holding nothing was uploaded, so the check would "
        "refuse every staged run for the absence of a delivery nobody made."
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

    preflight = _function_source(source, "_assert_delivery_is_findable")
    assert "_build_partner_read_store" in preflight, (
        f"{partner}'s preflight must use the suppressed-injection store, not the "
        "upload store, or it asks the wrong question"
    )

    # The declared name and the two legs are supplied by the CALLER, so that is where
    # they must be asserted. Looking for them in the preflight would be looking in the
    # wrong function — which the end-of-file slice used to hide.
    save = _function_source(source, "_save_contract")
    assert "product.CONSUMER_DOCUMENT_NAME" in save, (
        f"{partner} must pass the DECLARED consumer name to the preflight, never the "
        "path manager's model name that happens to equal it (C-77)"
    )
    for category in ('"forecast"', '"historical"'):
        assert category in save, (
            f"{partner} no longer verifies {category}. Both legs are checked separately "
            "because a run with one leg missing is invisible in half, and the historical "
            "leg is the one that stranded in run-0 (C-79)."
        )
    assert "manifest_file_id" in save, (
        f"{partner} no longer scopes the forecast read-back to this run's manifest, so "
        "the previous delivery's document satisfies the check (C-94)"
    )


def test_unverified_is_not_the_same_refusal_as_not_findable():
    """A store that could not be asked is a different event from an empty answer.

    Quarantining a delivery because the *check* failed would be an outage the guard
    manufactured. Same distinction as C-103 (a missing producer client vs a producer
    publishing no boundary) and C-99 (an unrecognised store result vs a real one).
    """
    exc = findability.unverified("forecast", TimeoutError("read timed out"))
    assert isinstance(exc, findability.FindabilityUnverifiedError)
    assert not isinstance(exc, findability.DeliveryNotFindableError), (
        "the two must not share a type, or a caller cannot act differently on them"
    )
    message = str(exc)
    assert "UNVERIFIED, not known invisible" in message
    assert "TimeoutError" in message and "read timed out" in message, (
        "the refusal must quote what actually stopped the check"
    )
    assert "forecast" in message, "and say which leg is unverified"


@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_the_preflight_does_not_report_a_failed_query_as_an_invisible_delivery(partner):
    source = (_REPO / "views_postprocessing" / partner / "managers" / f"{partner}.py").read_text()
    preflight = _function_source(source, "_assert_delivery_is_findable")
    assert "findability.unverified(" in preflight, (
        f"{partner}'s preflight no longer distinguishes a store error from an empty "
        "answer, so a transient network failure after a successful delivery would be "
        "reported as the delivery being invisible — and quarantined (C-94)."
    )


def test_the_previous_runs_document_does_not_satisfy_this_run():
    """The finding that made the guard worth having: without run-scoping it passes
    from delivery 2 onward exactly when a C-79 orphan appears.

    Run-1 delivered, so a document exists. Run-2's upload reports success but its
    metadata document is never created. The consumer's query returns run-1's id. Asking
    "is anything there" answers yes; asking "is what I just uploaded there" answers no.
    """
    with pytest.raises(findability.DeliveryNotFindableError) as excinfo:
        findability.assert_findable(
            "run-1-document",
            expected_file_id="run-2-document",
            consumer_name="un_fao",
            category="historical",
        )
    message = str(excinfo.value)
    assert "run-1-document" in message and "run-2-document" in message, (
        "the refusal must name both what the consumer will find and what this run "
        "uploaded, or an operator cannot tell staleness from absence"
    )
    assert "PREVIOUS" in message, (
        "the consequence — the consumer goes on serving the previous delivery — is the "
        "part that distinguishes this from an empty bucket"
    )
