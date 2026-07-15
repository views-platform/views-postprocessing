"""No-collapse invariant: a sampled forecast must still be draws when it ships
(ADR-013 §6 — the boundary named by views-models#149; register #45).

Representation-free — primitives only (a 2-D numpy array + declared ints). No pandas,
no views_frames, no datastore types. The manager feeds it the payload and the *declared*
contract values (the header's ``sample_count``, the configured ``s_min``); the rule
lives here. Declare-don't-guess: nothing is inferred from the payload — the caller
states what the payload claims to be, and this invariant fails loud if it is not.

Why this matters: the whole point of the sampled-forecast wire (ADR-013) is that FAO
receives the full posterior mixture — ``(N, S≈1024)`` draws per cell — collapsed to a
point exactly once, downstream, in the summarizer. Any hop that bakes out a mean/median
or ships a mislabeled point payload silently flattens the mixture. This is the single
**policy** gate (the per-hop emission/ingest asserts are mechanism guards); it runs
before every FAO-facing forecast upload.
"""

from __future__ import annotations

import numpy as np


class DrawsCollapseError(ValueError):
    """The forecast payload is not the uncollapsed draws its header declares."""


def assert_draws_uncollapsed(
    values,
    sample_count: int,
    *,
    s_min: int,
    label: str = "forecast",
) -> None:
    """Raise unless ``values`` is genuinely the declared ``(N, sample_count)`` draws.

    Checks, in order (ADR-013 §6):

    1. ``values`` is 2-D ``(N, S)`` — a collapsed 1-D column or a stacked 3-D block is
       not a sampled forecast payload.
    2. payload ``S == sample_count`` — the header's declaration must match the bytes.
    3. ``sample_count >= s_min`` — the consumer-facing floor (2 for the walking
       skeleton; region-pinned for production). Declared by the caller from config,
       never guessed here.
    4. **Global** non-degeneracy — at least one row carries more than one distinct
       draw value. Per-row zero variance is explicitly **legal** (zero-conflict cells
       dominate PGM); only a payload where *every* row is draw-degenerate fails — that
       is a collapsed forecast wearing a sampled header, not an edge case.

    NaN note: a NaN draw compares unequal to everything (including another NaN), so a
    NaN-carrying row counts as non-degenerate here. That is deliberate — NaN payloads
    are not this invariant's job; they fail loud at the delivery null gates.

    Args:
        values: the forecast payload — a 2-D numpy array of draws, one row per
            (time, unit), one column per draw.
        sample_count: the ``sample_count`` the artifact's contract header declares.
        s_min: the minimum draw count the delivery accepts (config-declared).
        label: short tag for the message (e.g. ``"forecast"``).

    Raises:
        DrawsCollapseError: naming the failed check, expected vs found.
    """
    arr = np.asarray(values)
    if arr.ndim != 2:
        raise DrawsCollapseError(
            f"{label}: payload is {arr.ndim}-D, expected 2-D (N, S) draws — a collapsed "
            f"or mis-shaped payload must not ship as a sampled forecast."
        )
    payload_s = arr.shape[1]
    if payload_s != sample_count:
        raise DrawsCollapseError(
            f"{label}: header declares sample_count={sample_count} but the payload "
            f"carries S={payload_s} — the artifact lies about its own draws."
        )
    if sample_count < s_min:
        raise DrawsCollapseError(
            f"{label}: sample_count={sample_count} is below the delivery floor "
            f"s_min={s_min} — a (near-)point payload must not ship as a sampled forecast."
        )
    varied_rows = np.any(arr != arr[:, :1], axis=1)
    if not bool(varied_rows.any()):
        raise DrawsCollapseError(
            f"{label}: every one of the {arr.shape[0]} rows is draw-degenerate (all "
            f"{sample_count} draws identical per row) — this is a collapsed forecast "
            f"wearing a sampled header. (Per-row zero variance is legal; all-rows is not.)"
        )
