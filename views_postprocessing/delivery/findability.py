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


class DeliveryNotFindableError(RuntimeError):
    """An upload succeeded, and the consumer's own query cannot find it."""


def assert_findable(file_id, *, consumer_name: str, category: str) -> None:
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
    if file_id:
        return
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
