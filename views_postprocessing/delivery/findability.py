"""Findability invariant: a delivered artifact must be retrievable under the name the
consumer actually queries (register C-94).

Representation-free — a lookup result and the declared identity it was looked up by.
No store types, no pandas, no frames. The caller performs the query (it owns the port);
the rule about what the answer means lives here.

**The failure this exists for is invisible by construction.** Every upload reports
success, storage is billed, and the consumer's endpoint returns empty. ADR-013 §4.1a
calls it *"invisible to the consumer, not merely degraded"*, and it has happened: run-0's
historical artifact was stranded on 2026-07-27 as a file with no metadata document
(register C-79). Nothing in this repository observed it. Every other mechanism the
platform aims at this is a **CI-time proxy** — we check our label against the registry,
the consumer checks theirs — and none of them observes the outcome of a real upload.

**Scope, stated plainly, because this entry has already been over-claimed once.** This
catches *the delivery ran and the consumer cannot see it*. It does **not** catch:

* *no delivery happened at all* — the 2026-08-12 empty bucket, which was an upstream
  destructive migration with no run since. A post-upload check observes nothing when
  there was no upload. This repository is not told when a delivery is due.
* *the bucket is fine but what is served is stale* — faoapi's warm per-key cache can
  serve stale historical over an emptied bucket.

Both are recorded as gaps in C-94 rather than dressed as things this covers.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class DeliveryNotFindableError(RuntimeError):
    """An upload succeeded, and the consumer's own query cannot find it."""


class FindabilityUnverifiedError(RuntimeError):
    """The read-back could not be performed, so findability is unknown."""


def unverified(category: str, exc: BaseException) -> FindabilityUnverifiedError:
    """The refusal for *could not ask*, which is not *asked and got nothing*.

    Distinguished for the same reason ``source_metadata`` distinguishes a missing
    producer client from a producer that publishes no boundary (C-103), and for the
    same reason ``_ContractStorePort.download`` refuses an unrecognised result rather
    than adapting to it (C-99): the two conditions call for different operator actions.
    A delivery that cannot be found is quarantined. A delivery that could not be
    *checked* may be perfectly fine, and quarantining it on a transient store error
    would be an outage manufactured by the guard.
    """
    return FindabilityUnverifiedError(
        f"the {category!r} leg uploaded, but the C-94 read-back could not be performed: "
        f"{type(exc).__name__}: {exc}. The delivery is UNVERIFIED, not known invisible — "
        "re-run the check before quarantining anything."
    )


def assert_findable(file_id, *, expected_file_id, consumer_name: str, category: str) -> None:
    """Raise unless the store returned something for the consumer's own query.

    Args:
        file_id: the result of querying the partner store for the newest document
            matching the consumer's filters. ``None`` is pipeline-core's documented
            "no match", but **any falsy value is refused**: `get_latest_file_id` also
            warns and returns ``.get("fileId", None)`` when it finds a document that
            is missing that field, so an empty id means "found something unusable"
            rather than "found". Same polarity as ``_ContractStorePort.download``,
            which refuses zero bytes for the reason C-99 records — an unrecognised
            result is refused and named, not adapted to silently.
        expected_file_id: the id THIS run uploaded for this leg — the manifest for the
            forecast leg (uploaded last, so it is the newest such document) and the
            historical artifact for its own. Without it the only available question is
            *"does any document exist under the consumer's name"*, which the previous
            delivery already answered yes to — so the check would pass on every run
            after the first, precisely when a C-79-shaped orphan appeared.
        consumer_name: the DECLARED store-document ``name`` the consumer filters on
            (``product.CONSUMER_DOCUMENT_NAME``), never a path-manager or directory
            name that happens to equal it (C-77).
        category: the delivery leg being verified — ``"forecast"`` or ``"historical"``.
            Checked separately on purpose: a run whose forecast landed and whose
            historical did not is invisible in exactly one half, and a single
            whole-delivery check would pass on it.

    Raises:
        DeliveryNotFindableError: naming the query that found nothing.
    """
    if file_id and file_id == expected_file_id:
        return
    if file_id:
        raise DeliveryNotFindableError(
            f"delivery is INVISIBLE to the consumer: the newest {category!r} document "
            f"under name == {consumer_name!r} is {file_id!r}, but this run uploaded "
            f"{expected_file_id!r}. The consumer will go on serving the PREVIOUS "
            "delivery while this one reports success — which is why the check is scoped "
            "to this run rather than asking whether any document exists (a question the "
            "previous run already answered). Quarantine and inspect the partner bucket."
        )
    raise DeliveryNotFindableError(
        f"delivery is INVISIBLE to the consumer: uploads for category {category!r} "
        f"reported success, but querying the partner store as the consumer does — "
        f"name == {consumer_name!r}, category == {category!r} — returns nothing. "
        "The artifacts may exist as files while carrying no metadata document, which "
        "is how run-0's historical leg was stranded (C-79); a document under any other "
        "name is equally invisible, because the consumer filters on this one "
        "unconditionally (ADR-013 §4.1a). Quarantine the run and check the partner "
        "bucket before re-delivering — the contract has no retraction primitive, so a "
        "correction is a new complete run."
    )


def assert_all_findable(resolved: dict, *, consumer_name: str) -> None:
    """Raise unless EVERY artefact this run uploaded resolves under its own filename.

    Args:
        resolved: ``{filename: (expected_file_id, found_file_id)}`` — one entry per
            object the run uploaded, ``found_file_id`` being what the store returns
            when asked for that exact filename under the consumer's name. ``None``
            means the query found nothing.
        consumer_name: the DECLARED store-document ``name`` (C-77).

    Raises:
        DeliveryNotFindableError: naming every object that does not resolve, not the
            first — an operator auditing a partner bucket needs the whole list, and
            the whole list is the difference between "one file is missing" and
            "nothing in this run is servable".

    **Why by filename and not by id (register C-94, #312).** The first live UN-FAO
    delivery, 2026-09-29, uploaded 109 of 110 objects and reported success. The GAUL
    sidecar's bytes were identical to the previous run's, the content-addressed store
    correctly declined a second copy, ``update_document`` ran against the OLD file, and
    the port returned a **real file id for the wrong document**. views-faoapi resolves
    by ``filename``, found nothing, and refused the delivery.

    So an id is not evidence. `assert_findable` above asks whether the consumer's
    *selection* lands on this run; this asks whether each artefact the manifest
    references is *there at all*. Both are needed and neither implies the other.

    **Why every object and not a count.** Pooling upstream is deterministic (measured
    in views-models, 2026-09-29: 25 of 25 anchor cells byte-identical across a re-pool),
    and `contract/wire/naming.py` embeds the run id in every filename. A re-run
    therefore writes NEW filenames over IDENTICAL bytes, so the dedup path that took the
    sidecar takes **all 110 objects at once** — the store creates the documents, the
    count is right, and nothing is servable. A count-plus-spot-check passes that.
    Re-running is our own documented remedy for a torn run (C-105) and for a correction
    (C-22), which is what makes this the realistic case rather than the exotic one.
    """
    missing = sorted(name for name, (_, found) in resolved.items() if not found)
    wrong = sorted(
        f"{name} (expected {exp!r}, store has {found!r})"
        for name, (exp, found) in resolved.items()
        if found and found != exp
    )
    if not missing and not wrong:
        return

    total = len(resolved)
    parts = [
        f"delivery is INVISIBLE to the consumer: {len(missing) + len(wrong)} of {total} "
        f"uploaded object(s) do not resolve under name == {consumer_name!r}."
    ]
    if missing:
        parts.append(
            f"NOT FOUND by filename ({len(missing)}): {', '.join(missing)}. Every upload "
            "reported success, so these exist as ids pointing at some other document — "
            "the shape that stranded the 2026-09-29 sidecar when the store deduplicated "
            "identical bytes and updated the PREVIOUS run's file instead."
        )
    if wrong:
        parts.append(f"RESOLVES TO THE WRONG DOCUMENT ({len(wrong)}): {'; '.join(wrong)}.")
    if len(missing) + len(wrong) == total:
        parts.append(
            "NOTHING in this run is servable. If this was a re-run of an earlier one, "
            "that is the expected shape: pooling is deterministic, so a re-run writes "
            "new filenames over identical bytes and every object deduplicates at once."
        )
    parts.append(
        "The contract has no retraction primitive, so a correction is a new complete "
        "run — but re-running unchanged reproduces this. Fix the upload path first."
    )
    raise DeliveryNotFindableError(" ".join(parts))


def verify(*, consumer_name: str, legs: dict, objects, resolve_latest, list_documents) -> None:
    """Run both findability questions against a partner store. The caller owns the port.

    Args:
        consumer_name: the DECLARED store-document ``name`` (C-77).
        legs: ``{category: expected_file_id}`` — does the consumer's own *selection*
            land on this run? Answered per category because a run whose forecast
            landed and whose historical did not is invisible in exactly one half.
        objects: records of every artefact uploaded — ``name``, ``file_id``,
            ``doc_type``, ``category``. Is each one *there at all*?
        resolve_latest: ``callable(filters) -> file_id | None`` (the port's
            ``latest_file_id``), for the selection question.
        list_documents: ``callable(filters) -> list[dict]`` (the port's ``documents``),
            for the per-object question.

    Raises:
        DeliveryNotFindableError: the delivery, or part of it, is invisible.
        FindabilityUnverifiedError: a query failed, so findability is UNKNOWN.

    **Why a type-scoped query and Python matching, not a filename query (#312 review).**
    The obvious implementation asks the store for ``filename == X``. It would be the
    first code on this platform to do so: ``filename`` is declared in pipeline-core's
    collection schema (`provisioning.py:101`) but **no index is declared for it
    anywhere**, and this deployment enforces index requirements on attribute lookups.
    An unsupported query would make every delivery report UNVERIFIED — a guard that
    logs "could not ask" forever while its mere presence reads as coverage. That is the
    guard-that-cannot-fire shape (**C-155**), and it is worse than the bug it replaces.

    So this uses the shape views-faoapi already proves against this store
    (`prediction/manager.py::resolve_artifact_file_ids`): query scoped to
    ``{category, type}``, match ``filename`` in Python. It also means the check asks
    the question **the consumer actually asks**, which is C-94's thesis rather than an
    approximation of it — and it costs one query per artefact type, not one per object.

    Lives here rather than in the partner managers because the logic is identical in
    both and must not diverge (the C-75 shape), and because the partner packages are
    under a ratcheting line budget whose stated response to binding is to move code
    **out of the package**.
    """
    for category, expected in legs.items():
        try:
            found = resolve_latest({"name": consumer_name, "category": category})
        except Exception as exc:  # could not ask != asked and got nothing (C-99, C-103)
            raise unverified(category, exc) from exc
        assert_findable(
            found, expected_file_id=expected, consumer_name=consumer_name, category=category
        )

    scopes = {(o["category"], o["doc_type"]) for o in objects}
    seen: dict[str, str] = {}
    for category, doc_type in sorted(scopes):
        filters = {"name": consumer_name, "category": category, "type": doc_type}
        try:
            docs = list_documents(filters)
        except Exception as exc:
            raise unverified(f"{category}/{doc_type} objects", exc) from exc
        for doc in docs or ():
            filename, file_id = doc.get("filename"), doc.get("fileId")
            if filename and file_id and filename not in seen:
                seen[filename] = file_id

    resolved = {o["name"]: (o["file_id"], seen.get(o["name"])) for o in objects}
    assert_all_findable(resolved, consumer_name=consumer_name)
    logger.info(
        "Findability preflight passed: %d leg(s) and %d object(s) resolvable under %r.",
        len(legs), len(objects), consumer_name,
    )
