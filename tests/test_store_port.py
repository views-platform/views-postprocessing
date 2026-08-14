"""The store port's refusals, tested — register C-79 (``upload``) and C-99 (``download``).

**This code had zero tests until 2026-08-05**, while the comment beside it called it
"the whole mechanism". It is: pipeline-core's store, on a metadata failure *after* the
file is uploaded, logs the error and **returns** ``success=False`` rather than raising.
A caller that discards the result therefore ships a file with no metadata document —
invisible to the consumer, which is what happened to run-0's historical artifact on
2026-07-27. This port is the thing that turns that into a refusal.

``download`` is the same fault in the method next door, and it went untested here for
another nine days: it chained ``.get()`` onto an unvalidated result, so a store result
whose ``data`` was null raised ``AttributeError`` three frames away instead of naming
the file that failed. views-crafdapi lost an evening to it on 2026-08-13. C-79's own
resolution note — *an unrecognised result should be refused and named, not adapted to
silently* — was already the specification; it had simply never been applied twice.

Testable now for a reason worth stating: the standing excuse for source-scanning
manager-side facts is that the managers need Appwrite env and a views-models path
manager to instantiate. ``_ContractStorePort`` needs neither — it takes a store object
and calls four methods on it. A fake store is enough, so the excuse never applied here.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from tests.conftest import PARTNER_PACKAGES


@dataclass
class _Result:
    """Shaped like pipeline-core's ``OperationResult``: a ``success`` bool plus error."""

    success: object
    error: str | None = None


@dataclass
class _Downloaded:
    """Shaped like the store's download result: ``.to_dict()["data"]["file_bytes"]``.

    ``data`` is declared as ``object`` rather than ``dict`` on purpose — the whole of
    C-99 is what happens when it is not a dict.
    """

    data: object

    def to_dict(self):
        return {"data": self.data}


class _FakeStore:
    """Records the upload and returns whatever results the test declares."""

    def __init__(self, result, downloaded=None):
        self.result = result
        self.downloaded = downloaded
        self.calls = []
        self.downloads = []

    def upload_data(self, **kwargs):
        self.calls.append(kwargs)
        return self.result

    def download_prediction(self, file_id):
        self.downloads.append(file_id)
        return self.downloaded


def _port(partner: str, result, downloaded=None):
    """The partner's port, wrapping a fake store. Needs no Appwrite environment."""
    module = __import__(
        f"views_postprocessing.{partner}.store_port", fromlist=["_ContractStorePort"]
    )
    store = _FakeStore(result, downloaded)
    return module._ContractStorePort(store), store


def _upload(port, tmp_path):
    payload = tmp_path / "artifact.parquet"
    payload.write_bytes(b"x")
    port.upload(
        payload,
        filename=payload.name,
        name="un_fao",
        doc_type="model",
        category="historical",
        loa="pgm",
        targets=["lr_ged_sb"],
        description="{}",
    )


@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_a_successful_upload_is_accepted(partner, tmp_path):
    """The happy path must not raise, or the guard would block every delivery."""
    port, store = _port(partner, _Result(success=True))
    _upload(port, tmp_path)
    assert len(store.calls) == 1, "the port must forward exactly one upload to the store"


@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_a_reported_failure_is_refused_and_names_the_error(partner, tmp_path):
    """The defect this port exists for: uploaded file, failed metadata, success=False."""
    port, _ = _port(partner, _Result(success=False, error="metadata storage failed"))
    with pytest.raises(RuntimeError) as excinfo:
        _upload(port, tmp_path)
    message = str(excinfo.value)
    assert "metadata storage failed" in message, (
        "the refusal must carry the store's own error — an operator debugging a partial "
        "upload should not have to go find it"
    )
    assert "orphan" in message, (
        "the refusal must say what the failure MEANS: a file with no metadata document, "
        "which is invisible to the consumer rather than absent"
    )


@pytest.mark.parametrize(
    "result, why",
    [
        (None, "the store returned nothing at all"),
        (_Result(success=None), "success is None — the fail-open case C-79 named"),
        (_Result(success="ok"), "success is a truthy non-bool"),
        (object(), "the result has no success attribute"),
    ],
)
@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_an_unrecognised_result_is_refused_rather_than_assumed_good(
    partner, result, why, tmp_path
):
    """Fail CLOSED. This is the polarity fix, and it is the whole of C-79.

    The check was ``if success is False``, so every case above sailed through as though
    the upload had worked. Today ``upload_data`` has one return path and ``success`` is
    a ``bool``, so the two polarities agree — but "today" is doing a lot of work in that
    sentence, and this entry's own trigger is *when pipeline-core changes what
    ``upload_data`` returns*. Fail-open is the wrong side to be on when the question is
    whether a partner delivery actually landed.
    """
    port, _ = _port(partner, result)
    with pytest.raises(RuntimeError, match="did not fully succeed"):
        _upload(port, tmp_path)


@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_the_refusal_names_what_it_actually_got(partner, tmp_path):
    """A refusal an operator cannot act on is barely better than no refusal.

    ``success=None`` and ``success=False`` are different faults — one is a store that
    reported a failure, the other a store whose contract moved. The message has to
    separate them or the next person re-runs the delivery instead of reading a changelog.
    """
    port, _ = _port(partner, _Result(success=None))
    with pytest.raises(RuntimeError) as excinfo:
        _upload(port, tmp_path)
    assert "success=None" in str(excinfo.value)


@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_the_port_forwards_every_declared_field(partner, tmp_path):
    """The port is a four-method seam; dropping a field here loses it silently.

    ``name`` in particular is what the consumer filters on (register C-77) — an upload
    that arrives without it is stored, billed, and unretrievable.
    """
    port, store = _port(partner, _Result(success=True))
    _upload(port, tmp_path)
    forwarded = store.calls[0]
    # Note `doc_type` -> `type`: the port renames it on the way through, because
    # `type` is the store's field name and a builtin here. That rename is the kind of
    # thing a seam quietly loses, which is why the field list is asserted rather than
    # assumed.
    for field in ("file", "filename", "name", "type", "category", "loa", "targets",
                  "description"):
        assert field in forwarded, f"the port dropped {field!r} on its way to the store"
    assert forwarded["name"] == "un_fao"
    assert forwarded["category"] == "historical"
    assert forwarded["type"] == "model", "doc_type must arrive as the store's `type`"


# ---------------------------------------------------------------------------
# `download` — the same polarity, on the method C-79 missed (register C-99).
# ---------------------------------------------------------------------------

_FILE_ID = "68b0f2c19a4e7d3c5a11"


def _download(port):
    return port.download(_FILE_ID)


@pytest.mark.parametrize("payload", [b"shard-bytes", bytearray(b"shard-bytes")])
@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_a_downloaded_artifact_is_returned_as_bytes(partner, payload):
    """The happy path, and the one conversion the port is allowed to make.

    ``bytearray`` is accepted and normalised because it is bytes by any useful
    definition; everything else is refused below. If this test did not exist the
    refusal could be tightened until nothing passed and the suite would not notice.
    """
    port, store = _port(partner, _Result(success=True), _Downloaded({"file_bytes": payload}))
    assert _download(port) == b"shard-bytes"
    assert store.downloads == [_FILE_ID], "the port must forward the pinned id unchanged"


@pytest.mark.parametrize(
    "downloaded, why",
    [
        (_Downloaded(None), "data is present and null — the crash of 2026-08-13"),
        (_Downloaded({}), "data carries no file_bytes at all"),
        (_Downloaded({"file_bytes": None}), "file_bytes is present and null"),
        (_Downloaded({"file_bytes": ""}), "file_bytes is a str, not bytes"),
        (_Downloaded({"file_bytes": b""}), "file_bytes is bytes but empty"),
        (_Downloaded("not-a-dict"), "data is not a mapping"),
        (None, "the store returned nothing at all"),
        (object(), "the result has no to_dict()"),
    ],
)
@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_a_download_that_is_not_bytes_is_refused_rather_than_returned_as_none(
    partner, downloaded, why
):
    """Fail CLOSED. This is C-79's polarity applied to the method next door.

    The original ``.get("data", {}).get("file_bytes", None)`` handled exactly one of
    these — a *missing* ``data`` key. Every other row here either returned ``None`` to a
    caller that could not tell it from an empty artifact, or raised ``AttributeError``
    from inside a dict comprehension three frames away.

    ``b""`` is refused with the rest deliberately: no shard, sidecar or manifest is ever
    zero-length, so an empty payload is a failed download wearing a valid type, and
    returning it only moves the same crash to the parser.
    """
    port, _ = _port(partner, _Result(success=True), downloaded)
    with pytest.raises(RuntimeError, match="did not return usable bytes"):
        _download(port)


@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_the_download_refusal_names_the_file_id_and_what_it_got(partner):
    """The defect was never that it failed — it was that the failure said nothing.

    The crash an operator actually saw was ``'NoneType' object has no attribute 'get'``,
    raised inside a dict comprehension over pinned ids. It named no file, did not say a
    download had failed, and sent views-crafdapi looking for an OOM kill that turned out
    to be a different process. The id is in hand at this point; a refusal that drops it
    is barely better than the crash.
    """
    port, _ = _port(partner, _Result(success=True), _Downloaded(None))
    with pytest.raises(RuntimeError) as excinfo:
        _download(port)
    message = str(excinfo.value)
    assert _FILE_ID in message, "the refusal must name the file_id it was given"
    assert "download" in message, "the refusal must say that a DOWNLOAD failed"
    assert "NoneType" in message, (
        "the refusal must name what it actually got, or the reader cannot tell a store "
        "that returned nothing from one whose result shape moved"
    )
