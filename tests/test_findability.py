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


def test_the_preflight_does_not_report_a_failed_query_as_an_invisible_delivery():
    """The distinction must survive wherever the query loop lives.

    It used to live in each partner manager and this test read it there. #312 moved it
    into `delivery/findability.verify` — one copy instead of two, and out of the partner
    packages, whose line budget says to move code out rather than raise it. The claim is
    unchanged: a store that could not be asked must not be reported as an invisible
    delivery. Only its address changed, so the test follows it rather than being deleted.

    Behavioural, not a source scan, now that the logic is reachable without a manager.
    """
    def explodes(_filters):
        raise TimeoutError("read timed out")

    with pytest.raises(findability.FindabilityUnverifiedError):
        findability.verify(
            consumer_name="un_fao", legs={"forecast": "a"}, objects=[],
            resolve_latest=explodes, list_documents=explodes,
        )

    # and the same for the per-object half, which #312 added
    with pytest.raises(findability.FindabilityUnverifiedError) as caught:
        findability.verify(
            consumer_name="un_fao", legs={},
            objects=[{"name": "run__sidecar.parquet", "file_id": "a",
                      "doc_type": "sampled_forecast_sidecar", "category": "forecast"}],
            resolve_latest=explodes, list_documents=explodes,
        )
    assert "sampled_forecast_sidecar" in str(caught.value), (
        "an unverified scope must name which artefact type could not be checked"
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


# ── #312: every artefact, by the consumer's own resolution shape ─────────────


def _objects(names, doc_type="sampled_forecast_shard", category="forecast"):
    return [
        {"name": n, "file_id": f"id-{n}", "doc_type": doc_type, "category": category}
        for n in names
    ]


def _store(landed: dict):
    """A store answering the way views-faoapi queries it: type-scoped, filename in
    the document. `landed` maps filename -> fileId for what is actually retrievable."""
    def list_documents(_filters):
        return [{"filename": n, "fileId": fid} for n, fid in landed.items()]
    return list_documents


def _never(_filters):
    raise AssertionError("the selection query must not run when legs is empty")


def test_the_2026_09_29_incident_is_caught():
    """The regression case: 109 of 110 uploaded, every call reported success.

    The sidecar's bytes matched the previous run's, the store declined a second copy,
    `update_document` ran against the OLD file, and the port returned a real file id
    for the wrong document. The consumer resolves by filename, found nothing, refused.
    """
    objects = _objects(["run2__shard0.parquet", "run2__shard1.parquet"])
    objects += _objects(["run2__sidecar.parquet"], "sampled_forecast_sidecar")
    landed = {o["name"]: o["file_id"] for o in objects if "sidecar" not in o["name"]}

    with pytest.raises(findability.DeliveryNotFindableError) as caught:
        findability.verify(
            consumer_name="un_fao", legs={}, objects=objects,
            resolve_latest=_never, list_documents=_store(landed),
        )
    message = str(caught.value)
    assert "run2__sidecar.parquet" in message, "the refusal must name the missing object"
    assert "1 of 3" in message
    assert "NOTHING in this run is servable" not in message, (
        "one missing object is not a total failure; the message must not overstate"
    )


def test_the_selection_check_alone_would_have_passed_the_incident():
    """Why the per-object half had to be added rather than the dict widened.

    Shards, sidecar and manifest all carry category="forecast" and the manifest is
    uploaded last, so the newest forecast document is always the manifest. The
    selection check is satisfied by the very run that is unservable.
    """
    findability.verify(
        consumer_name="un_fao", legs={"forecast": "id-manifest"}, objects=[],
        resolve_latest=lambda _f: "id-manifest", list_documents=_never,
    )


def test_a_deterministic_rerun_losing_everything_says_so():
    """The worst case, and the one our own remedy triggers.

    Pooling is deterministic and naming.py embeds the run id in every filename, so a
    re-run writes NEW names over IDENTICAL bytes and every object deduplicates at once.
    The store creates the documents, the count is right, nothing is servable — and
    re-running is what C-105 and C-22 tell an operator to do.
    """
    objects = _objects([f"run2__shard{i}.parquet" for i in range(4)])
    with pytest.raises(findability.DeliveryNotFindableError) as caught:
        findability.verify(
            consumer_name="un_fao", legs={}, objects=objects,
            resolve_latest=_never, list_documents=_store({}),
        )
    message = str(caught.value)
    assert "4 of 4" in message
    assert "NOTHING in this run is servable" in message
    assert "re-running unchanged reproduces this" in message, (
        "the refusal must not send an operator at the remedy that reproduces the fault"
    )


def test_an_object_resolving_to_the_wrong_document_is_refused():
    """Content-hash dedup returns a REAL id for the WRONG document, so a check that
    only asked "did I get an id back" passes the incident. This one does not."""
    objects = _objects(["run2__sidecar.parquet"], "sampled_forecast_sidecar")
    with pytest.raises(findability.DeliveryNotFindableError) as caught:
        findability.verify(
            consumer_name="un_fao", legs={}, objects=objects,
            resolve_latest=_never,
            list_documents=_store({"run2__sidecar.parquet": "id-from-run1"}),
        )
    message = str(caught.value)
    assert "WRONG DOCUMENT" in message
    assert "id-from-run1" in message


def test_the_query_is_type_scoped_and_costs_one_per_type_not_one_per_object():
    """The #312 review finding: `filename` is declared but NOT indexed, and nothing on
    the platform queries it. This uses views-faoapi's proven shape instead — scope by
    {category, type}, match filename in Python — which also collapses 110 lookups to
    one per artefact type."""
    objects = _objects([f"s{i}.parquet" for i in range(50)])
    objects += _objects(["sidecar.parquet"], "sampled_forecast_sidecar")
    objects += _objects(["hist.parquet"], "model", "historical")
    seen = []

    def list_documents(filters):
        seen.append(filters)
        assert "filename" not in filters, (
            "queried by filename — that attribute has no index and this deployment "
            "enforces index requirements, so the guard would return UNVERIFIED forever"
        )
        return [{"filename": o["name"], "fileId": o["file_id"]} for o in objects]

    findability.verify(
        consumer_name="un_fao", legs={}, objects=objects,
        resolve_latest=_never, list_documents=list_documents,
    )
    assert len(seen) == 3, f"expected one query per (category, type), got {len(seen)}"
    assert {tuple(sorted(f.items())) for f in seen} == {
        (("category", "forecast"), ("name", "un_fao"), ("type", "sampled_forecast_shard")),
        (("category", "forecast"), ("name", "un_fao"), ("type", "sampled_forecast_sidecar")),
        (("category", "historical"), ("name", "un_fao"), ("type", "model")),
    }


def test_a_fully_landed_run_passes():
    objects = _objects(["a.parquet"]) + _objects(["m.json"], "sampled_forecast_manifest")
    landed = {o["name"]: o["file_id"] for o in objects}
    findability.verify(
        consumer_name="un_fao", legs={"forecast": "id-m.json"}, objects=objects,
        resolve_latest=lambda _f: "id-m.json", list_documents=_store(landed),
    )


@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_the_manager_hands_the_preflight_every_uploaded_object(partner):
    """The wiring half. The rule above is worth nothing if the call site passes two ids.

    That is exactly what shipped: `{"forecast": ..., "historical": ...}` — the commit
    marker and the historical leg, while 108 shards and the sidecar went unasked (#312).
    """
    source = (_REPO / "views_postprocessing" / partner / "managers" / f"{partner}.py").read_text()
    call = next(
        n for n in ast.walk(ast.parse(source))
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id == "_assert_delivery_is_findable"
    )
    assert len(call.args) == 4, (
        f"{partner} calls the preflight with {len(call.args)} arguments; it needs the "
        "per-object map as well as the per-leg one, or the sidecar goes unasked again"
    )
    passed = ast.unparse(call.args[3])
    assert "uploaded_objects" in passed, (
        f"{partner}'s object map is {passed!r} — it must come from the sink's upload "
        "ledger, which is the only record of what this run actually put in the bucket"
    )
    assert "hist" in passed, (
        f"{partner} omits the historical artefact from the per-object check; it is "
        "uploaded by the manager, so the sink's ledger does not contain it"
    )


def test_the_sink_carries_its_upload_ledger_out():
    """The ledger already existed for the torn-run refusal (C-105) and stayed local.
    The manager cannot verify what it is not told."""
    source = (_REPO / "views_postprocessing" / "contract" / "wire" / "sink.py").read_text()
    deliver = _function_source(source, "deliver_run")
    assert 'summary["uploaded_objects"]' in deliver, (
        "deliver_run no longer exports the upload ledger, so the #312 per-object "
        "preflight has nothing to check against"
    )


def test_an_unreadable_store_answer_is_unverified_not_an_invisible_delivery():
    """#312 review, finding 1 — a polarity bug, and the worst kind.

    The parse used to sit OUTSIDE the try. If the store returned objects rather than
    dicts, or renamed its keys, `doc.get` raised, `seen` stayed empty, and every object
    was reported NOT FOUND — firing the full "NOTHING in this run is servable" refusal
    on a perfectly healthy delivery. A failure of the CHECK must never quarantine the
    DELIVERY; that is the whole of C-99 and C-103 and this module says so twice.
    """
    class NotADict:
        pass

    objects = _objects([f"s{i}.parquet" for i in range(3)])
    with pytest.raises(findability.FindabilityUnverifiedError) as caught:
        findability.verify(
            consumer_name="un_fao", legs={}, objects=objects,
            resolve_latest=_never, list_documents=lambda _f: [NotADict()],
        )
    message = str(caught.value)
    assert "UNVERIFIED, not known invisible" in message
    assert "sampled_forecast_shard" in message, "and name the scope that could not be read"


def test_a_missing_upload_ledger_fails_loudly_rather_than_shrinking_the_check():
    """#312 review, finding 2 — the silent fallback.

    `summary.get("uploaded_objects", [])` would have let the per-object guard quietly
    shrink to the single historical object and log "preflight passed", leaving the 108
    shards, the sidecar and the manifest unasked — the precise shape of the bug being
    fixed. Declared access instead: the key is guaranteed on every path that reaches
    the guard, so its absence is a defect and must read as one (ADR-003).
    """
    for partner in PARTNER_PACKAGES:
        source = (_REPO / "views_postprocessing" / partner / "managers" / f"{partner}.py").read_text()
        assert 'summary.get("uploaded_objects"' not in source, (
            f"{partner} defaults the upload ledger; a sink that stopped exporting it "
            "would silently reduce the guard to one object instead of failing"
        )
        assert 'summary["uploaded_objects"]' in source


def test_a_correct_delivery_passes_whatever_order_the_store_returns():
    """#312 re-review: document order is unspecified, so the check must not depend on it.

    `search_files_by_metadata` appends only `Query.equal` per filter and never an
    `order_desc`/`order_asc` (pipeline-core `modules/appwrite/file.py:1045-1050`). A
    "first match wins" rule would have been a coin flip presented as a tie-break. The
    question we actually have — is the id THIS run uploaded present under the name —
    needs no ordering at all, so the same delivery must pass in any permutation.
    """
    objects = _objects(["a.parquet", "b.parquet"])
    docs = [{"filename": o["name"], "fileId": o["file_id"]} for o in objects]
    # a stale document from a previous run, sharing a filename, returned FIRST
    stale = [{"filename": "a.parquet", "fileId": "id-from-run1"}]

    for order in ([*stale, *docs], [*docs, *stale], [docs[1], stale[0], docs[0]]):
        findability.verify(
            consumer_name="un_fao", legs={}, objects=objects,
            resolve_latest=_never, list_documents=lambda _f, o=order: o,
        )


def test_a_name_carrying_only_another_runs_id_is_still_refused():
    """Order-independence must not become permissiveness. If the only documents under
    a filename belong to some other run, this run's object did not land."""
    objects = _objects(["a.parquet"])
    with pytest.raises(findability.DeliveryNotFindableError) as caught:
        findability.verify(
            consumer_name="un_fao", legs={}, objects=objects,
            resolve_latest=_never,
            list_documents=lambda _f: [
                {"filename": "a.parquet", "fileId": "id-run1"},
                {"filename": "a.parquet", "fileId": "id-run0"},
            ],
        )
    message = str(caught.value)
    assert "WRONG DOCUMENT" in message
    assert "id-run0" in message and "id-run1" in message, (
        "the refusal must show every id the store holds under that name, not one"
    )
