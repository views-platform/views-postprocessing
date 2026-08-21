"""The prediction store behind a four-method port — the DIP seam of ADR-013 epic #105.

``wire/source_selection`` and ``wire/sink`` drive the store through this object and
never see the client's types. That is the whole point of the seam, so the constructor
takes **any** object carrying the four methods below rather than naming a concrete
client class — the contract is the methods, not the type.

Both refusals here are the same rule applied twice: *an unrecognised result should be
refused and named, not adapted to silently.* ``upload`` learned it as register C-79
(2026-08-05), ``download`` as C-99 (2026-08-14) after the shape it did not check cost
views-crafdapi an evening. Tests: ``tests/test_store_port.py``.
"""

from views_postprocessing.contract import store_metadata


class _ContractStorePort:
    """Adapts a prediction-store client to the wire ports.

    ``datastore`` is any object exposing ``get_latest_file_id``, ``get_file_metadata``,
    ``download_prediction`` and ``upload_data``.
    """

    def __init__(self, datastore) -> None:
        self._dsm = datastore

    def latest_file_id(self, filters: dict):
        return self._dsm.get_latest_file_id(filters=filters)

    def file_metadata(self, file_id: str) -> dict:
        return store_metadata.file_metadata(self._dsm.get_file_metadata(file_id))

    def download(self, file_id: str) -> bytes:
        """Fetch a pinned artifact's bytes, refusing any result that is not bytes.

        Fail CLOSED, for the reason C-79 recorded of ``upload`` below: *an unrecognised
        result should be refused and named, not adapted to silently.* Register C-99.
        """
        result = self._dsm.download_prediction(file_id)
        # `.get("data", {})` was the defect: when the key is PRESENT and null the default
        # never applies, so `.get("file_bytes")` raised AttributeError three frames away
        # in a dict comprehension, naming neither the file_id nor the fact that a
        # download had failed (views-crafdapi#44, 2026-08-13 — it cost an evening).
        to_dict = getattr(result, "to_dict", None)
        payload = to_dict() if callable(to_dict) else None
        data = payload.get("data") if isinstance(payload, dict) else None
        file_bytes = data.get("file_bytes") if isinstance(data, dict) else None

        if isinstance(file_bytes, (bytes, bytearray)):
            if file_bytes:
                return bytes(file_bytes)
            # Zero bytes is refused too: no shard, sidecar or manifest is ever empty, and
            # returning b"" only moves the same failure to the parser.
            observed = "'file_bytes' was present but empty (0 bytes)"
        else:
            observed = (
                f"the store result was {type(result).__name__}, its 'data' was "
                f"{type(data).__name__}, its 'file_bytes' was {type(file_bytes).__name__}"
            )
        raise RuntimeError(
            f"download of file_id {file_id!r} did not return usable bytes: {observed}. "
            "Refused here, where the file_id is still in hand — the caller assembles "
            "these by name and cannot tell a failed download from an empty artifact."
        )

    def upload(self, file_path, *, filename, name, doc_type, category, loa, targets, description=None) -> str | None:
        result = self._dsm.upload_data(
            file=file_path,
            filename=filename,
            name=name,
            type=doc_type,
            category=category,
            loa=loa,
            targets=targets,
            description=description,
        )
        # On a metadata failure the store logs, then RETURNS success=False with the
        # file already uploaded (pipeline-core modules/appwrite/file.py — the file is
        # the claim; its line number moves between releases). It never raises, so a
        # caller that discards the result ships an invisible orphan: run-0's historical
        # artifact, 2026-07-27. This check is the whole mechanism.
        #
        # **Refuse unless success is explicitly True** (register C-79). The earlier
        # `if success is False` failed OPEN: a result that was None, or lacked the
        # attribute, or carried a non-bool, sailed through as though the upload had
        # worked. Today `upload_data` has a single return path and `success` is a
        # `bool` dataclass field, so the two polarities agree — but the moment that
        # stops being true is exactly this entry's trigger, and fail-open is the wrong
        # side to be on when the subject is "did the delivery actually land".
        #
        # The old `to_dict()` fallback is gone with it: dead on the real path, and an
        # unrecognised result should be refused and named, not adapted to silently.
        success = getattr(result, "success", None)
        if success is not True:
            error = getattr(result, "error", None) or "unknown store error"
            raise RuntimeError(
                f"upload of {filename!r} did not fully succeed (file may be an orphan "
                f"without a metadata document): {error}. The store reported "
                f"success={success!r} (result type {type(result).__name__})."
            )
        # The uploaded file's id, so the C-94 read-back can be scoped to THIS run.
        # Discarding it (as this did until 2026-08-19) makes the only available check
        # "is there any document under the consumer's name", which the previous run
        # already satisfies — so the guard could never fail from delivery 2 onward.
        data = getattr(result, "data", None)
        return data.get("file_id") if isinstance(data, dict) else None
