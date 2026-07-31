"""The prediction store's own facts, as declared primitives (S3, #151).

Sibling of ``source_metadata`` — that module reads facts from the **producer**
(views-datafactory's zarr attributes); this one reads facts from the **store** (the
Appwrite metadata document pipeline-core's ``FileMetadata`` writes on upload). Both
exist for the same reason: to keep knowledge of a foreign payload shape in exactly
one place, so the rest of the delivery consumes primitives.

**Why this is not in ``extraction.py`` any more.** It never belonged there.
``extraction`` was the pandas→primitives seam — its job was turning a delivery
*frame* into cell ids and month arrays. ``file_metadata`` turns a *store document*
into an identity dict; it touches no representation at all. It shared a module with
the frame readers only because both were "things that unpack something", which is
not a reason to change together (CCP). When #149 retired the pandas delivery, the
frame readers became unreachable and this function was the sole survivor of a
module named for a seam it was never part of.

The one caller is ``_ContractStorePort.file_metadata`` in the manager, which adapts
``DatastoreModule`` to the wire's ports (DIP) — so the store's document shape is
known here, and nowhere above.
"""

from __future__ import annotations

# Identity fields written by pipeline-core's ``FileMetadata`` on upload. Declared,
# never inferred: a field absent from the document reads as ``None`` rather than
# raising, because absence is a fact about the document the caller may want to act
# on, not a malformed input.
FILE_META_KEYS: tuple[str, ...] = ("name", "loa", "category", "targets")


def file_metadata(record) -> dict:
    """The identity metadata of a selected prediction-store file, as a plain dict.

    Args:
        record: the ``get_file_metadata`` result from pipeline-core's
            ``DatastoreModule``. Its ``.to_dict()["data"]`` is the Appwrite metadata
            document. **This is the only place that knows that shape.**

    Returns:
        A dict with exactly ``FILE_META_KEYS``, each value taken from the document or
        ``None`` where the document does not carry it.
    """
    doc = record.to_dict().get("data", {}) or {}
    return {key: doc.get(key) for key in FILE_META_KEYS}
