"""The store port's refusal, tested — register C-79.

**This code had zero tests until 2026-08-05**, while the comment beside it called it
"the whole mechanism". It is: pipeline-core's store, on a metadata failure *after* the
file is uploaded, logs the error and **returns** ``success=False`` rather than raising.
A caller that discards the result therefore ships a file with no metadata document —
invisible to the consumer, which is what happened to run-0's historical artifact on
2026-07-27. This port is the thing that turns that into a refusal.

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


class _FakeStore:
    """Records the upload and returns whatever result the test declares."""

    def __init__(self, result):
        self.result = result
        self.calls = []

    def upload_data(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def _port(partner: str, result):
    """The partner's port, wrapping a fake store. Needs no Appwrite environment."""
    pytest.importorskip("views_pipeline_core", reason="the port wraps its DatastoreModule")
    module = __import__(
        f"views_postprocessing.{partner}.managers.{partner}", fromlist=["_ContractStorePort"]
    )
    store = _FakeStore(result)
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
