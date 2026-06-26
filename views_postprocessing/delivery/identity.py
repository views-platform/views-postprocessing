"""Forecast-file identity invariant: deliver the forecast we asked for, not whatever
landed last (register C-25, S3).

Representation-free — primitives only (plain dicts of file metadata). No pandas, no
datastore types. The manager feeds it the selected file's identity via
``views_postprocessing/unfao/extraction.py``; the rule lives here.

Why this matters: the FAO forecast is selected from the prediction store by ``category``
alone (newest-wins) — no filter on ensemble name or level. Today only the production
ensemble uploads with ``category="forecast"``, so the newest file is the right one *by
circumstance, not by contract*. This guard fails loud if the selected file's identity
does not match the configured ensemble, so a stray upload (a test run, a second model, a
backfill) can never be silently shipped to the partner.
"""

from __future__ import annotations


class ForecastIdentityError(ValueError):
    """The selected forecast file does not match the requested ensemble identity."""


def assert_forecast_identity(
    selected: dict, expected: dict, *, label: str = "forecast"
) -> None:
    """Raise unless ``selected`` matches ``expected`` on every key ``expected`` names.

    Only the keys present in ``expected`` are checked (e.g. ``{"name", "loa"}``); any other
    metadata on ``selected`` (targets, category, timestamps) is ignored. This keeps the
    caller in control of what identity means without the invariant guessing.

    Args:
        selected: metadata of the file actually selected for delivery.
        expected: the identity the configured ensemble requires; each key must match.
        label: short tag for the message (e.g. ``"forecast"``).

    Raises:
        ForecastIdentityError: naming every mismatched key, expected vs found.
    """
    mismatches = {
        key: (expected[key], selected.get(key))
        for key in expected
        if selected.get(key) != expected[key]
    }
    if mismatches:
        detail = ", ".join(
            f"{key}: expected {exp!r}, found {got!r}"
            for key, (exp, got) in mismatches.items()
        )
        raise ForecastIdentityError(
            f"{label}: identity mismatch — {detail}. A stray upload to the prediction "
            f"store would otherwise ship the wrong predictions to the partner."
        )
