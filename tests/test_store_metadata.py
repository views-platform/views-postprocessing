"""Unit tests for the prediction store's identity seam (unfao/store_metadata.py).

Renamed from `test_extraction.py` in #151. That file tested two unrelated things: the
pandas→primitives frame readers (unreachable since #149 retired the pandas delivery,
and superseded by `frame_extraction.py`) and `file_metadata`, which unpacks a *store
document* and touches no representation at all. The frame-reader tests went with the
module; these survive with the function that outlived it.
"""

from views_postprocessing.unfao import store_metadata


class _FakeResult:
    """Stands in for a DatastoreModule.get_file_metadata OperationResult."""

    def __init__(self, document):
        self._document = document

    def to_dict(self):
        return {"data": self._document, "code": "FOUND"}


def test_file_metadata_normalizes_record_to_identity_dict():
    record = _FakeResult(
        {
            "name": "fatalities_ensemble",
            "loa": "pgm",
            "category": "forecast",
            "targets": ["pred_a", "pred_b"],
            "$id": "doc123",  # appwrite system fields are dropped
            "fileId": "file456",
        }
    )
    assert store_metadata.file_metadata(record) == {
        "name": "fatalities_ensemble",
        "loa": "pgm",
        "category": "forecast",
        "targets": ["pred_a", "pred_b"],
    }


def test_file_metadata_missing_fields_become_none():
    record = _FakeResult({"name": "m"})
    assert store_metadata.file_metadata(record) == {
        "name": "m",
        "loa": None,
        "category": None,
        "targets": None,
    }
