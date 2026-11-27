"""The audience-connection invariant: a partner's own project is never the shared shelf.

#327 asks for two connections in one delivery — the shelf read in the shared project with
one key, the audience write in the partner's own project with another — and its clause 2
is the part that needs a mechanism rather than care:

    **No fallback.** If the audience project id or key is missing, refuse — never fall
    back to writing into the shared project. A silent fallback would put CRAF'd's data
    back where FAO's key can read it.

``appwrite_env.assert_env_declared`` already refuses an *absent* name. What it cannot see
is the shape that actually happened: both coordinates **present**, both **resolving to the
same project**, because the audience slot was filled with the shelf's value — or because
the launcher exported one name and not the other and a reader took the nearest match.
That is a fallback with nothing missing, and it is indistinguishable from success at every
later step.

It is also not hypothetical. Until this module existed, ``crafd/managers/crafd.py`` read
``APPWRITE_DATASTORE_PROJECT_ID`` for **both** the shelf (`:64`) and the partner write
(`:103`) — two buckets in one project, not two projects. Arming the delivery in that state
would have published into the shared project while views-crafdapi read only its own, and
**three surfaces would have agreed nothing was delivered**: crafdapi's 503, views-models'
liveness monitor, and an operator looking in the wrong bucket. All three wrong.

Representation-free — two strings and a name. No Appwrite client, no environment, no
pipeline-core, so the refusal is observable in a unit test (the same reason
``delivery/coverage.py`` takes primitives).
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class AudienceIsolationError(ValueError):
    """The audience connection does not address a project of its own.

    A sibling of ``ValueError`` rather than of any delivery error, deliberately: nothing
    has been delivered wrongly when this raises. The *connection* is wrong, and it is
    wrong before a single byte moves — which is the only point at which refusing is free.
    """


def assert_audience_is_not_the_shelf(
    audience_project_id: str | None,
    shelf_project_id: str | None,
    *,
    consumer: str,
) -> str:
    """Return the audience project id, or refuse — declared, non-empty, and NOT the shelf.

    Args:
        audience_project_id: the value of the audience project coordinate.
        shelf_project_id: the value of the shared shelf's project coordinate.
        consumer: the declared consumer name, for the message (e.g. ``"un_crafd"``).

    Returns:
        ``audience_project_id``, so the caller can use the checked value rather than
        re-reading the environment and getting a second chance to read the wrong name.

    Raises:
        AudienceIsolationError: if the audience id is absent/blank, or equals the shelf's.
    """
    if not isinstance(audience_project_id, str) or not audience_project_id.strip():
        raise AudienceIsolationError(
            f"{consumer}: no audience project declared (got {audience_project_id!r}). "
            "The delivery writes into the audience's OWN Appwrite project and reads the "
            "shelf from the shared one; with no audience coordinate there is nowhere to "
            "write that is not the shelf. Refusing rather than falling back (#327 "
            "clause 2) — a fallback would publish where another partner's key can read "
            "it, and the consumer would report an empty endpoint rather than an error."
        )
    if isinstance(shelf_project_id, str) and audience_project_id.strip() == shelf_project_id.strip():
        raise AudienceIsolationError(
            f"{consumer}: the audience project and the shared shelf resolve to the SAME "
            "project. Both coordinates are present, so nothing is 'missing' — this is "
            "the fallback #327 clause 2 forbids, wearing the costume of a working "
            "configuration. Either the audience slot was filled with the shelf's value, "
            "or the launcher exported one name and not the other. Project ids are "
            "non-secret coordinates, and this message deliberately does NOT print them: "
            "this repository is public and its CI logs are world-readable (register "
            "C-89). Compare the two names in the launcher's environment."
        )
    # Logged at INFO because the delivery's own audit trail should record WHICH project it
    # wrote to, and the id is a non-secret coordinate — but see C-89: the VALUE is never
    # logged, only the fact that the two differ. The coordinate NAME is the operator's
    # handle for this, not the value.
    logger.info(
        "%s: audience connection is isolated from the shared shelf (two distinct "
        "projects, values not logged).",
        consumer,
    )
    return audience_project_id
