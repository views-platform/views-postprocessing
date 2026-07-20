"""Gid-set parity invariant: the sidecar covers exactly the forecast's cells
(ADR-013 §5.2).

Representation-free — primitives only (two iterables of ints). A sidecar missing
a forecast cell would silently strip that cell's geography downstream; a sidecar
carrying extra cells claims geography for forecasts that don't exist. Both fail
loud here, naming the offenders.

Separate from ``coverage.py`` on purpose: coverage's reason to change is the
region product definition (expected cell counts, exclusion pins); parity's is the
wire contract. Different closures, different files.
"""

from __future__ import annotations


class GidParityError(ValueError):
    """Sidecar and forecast gid sets differ."""


def assert_gid_set_parity(forecast_gids, sidecar_gids, *, label: str = "sidecar") -> None:
    """Raise unless the two gid sets are identical (§5.2)."""
    forecast = {int(g) for g in forecast_gids}
    sidecar = {int(g) for g in sidecar_gids}
    if forecast == sidecar:
        return
    missing = sorted(forecast - sidecar)
    extra = sorted(sidecar - forecast)
    raise GidParityError(
        f"{label}: gid sets differ (§5.2) — {len(missing)} forecast cell(s) missing "
        f"from the sidecar (first: {missing[:5]}), {len(extra)} extra sidecar cell(s) "
        f"(first: {extra[:5]})."
    )
