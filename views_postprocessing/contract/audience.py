"""The audience-connection invariant: a partner's own connection is never the shared shelf.

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
``APPWRITE_DATASTORE_PROJECT_ID`` for **both** the shelf and the partner write — two
buckets in one project, not two projects. Arming the delivery in that state would have
published into the shared project while views-crafdapi read only its own, and **three
surfaces would have agreed nothing was delivered**: crafdapi's 503, views-models' liveness
monitor, and an operator looking in the wrong bucket. All three wrong.

**Both halves of a connection are checked, not just the project.** A connection is a
project id *and* a credential, and an Appwrite key authenticates against exactly one
project — so a run holding the audience's project with the shelf's key is as broken as the
collision above, and fails as a 401 deep inside the delivery rather than as a refusal
naming the coordinate. The same copy-paste that fills the audience project slot with the
shelf's value fills the key slot the same way. Credentials are compared and **never
printed, logged or included in a message**; the comparison needs neither.

**Why ``contract/`` and not ``delivery/``.** ADR-012 puts representation-free invariants —
*what makes a delivery valid* — in ``delivery/``, and partner-neutral machinery — *how a
delivery is built* — in ``contract/``. Nothing has been delivered when this refuses, and
no delivered artifact is being judged: what is wrong is the connection the delivery would
be built on. That is the second question, so this lives beside the other build-time
machinery. It is representation-free all the same (four strings and a name: no Appwrite
client, no environment read, no pipeline-core), which is what makes the refusal observable
in a unit test.
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


def _refuse(message: str) -> None:
    """Log at ERROR and raise — ADR-008 §'Raised structural failures must be logged'.

    Both are required and neither substitutes for the other: the raise halts the run, the
    log is what survives in the launcher's persistent output after the process is gone.
    Without this, a mis-wired connection left the quieter trace of the two — the refusal
    wrote nothing while a *successful* isolation check wrote an INFO line.
    """
    logger.error(message)
    raise AudienceIsolationError(message)


def assert_audience_is_not_the_shelf(
    *,
    audience_project_id: str | None,
    shelf_project_id: str | None,
    audience_credential: str | None,
    shelf_credential: str | None,
    consumer: str,
) -> str:
    """Return the audience project id, stripped — or refuse.

    Every parameter is keyword-only, and that is load-bearing rather than style: the four
    values are same-typed strings read from four similarly spelled coordinates, so a
    positional call site can transpose audience and shelf and still satisfy a *symmetric*
    equality check. The refusal would pass and the delivery would address the shelf. The
    keyword-only marker makes that slip unexpressible, which matters most for the clone
    this module exists to serve (#337).

    Args:
        audience_project_id: value of the audience project coordinate.
        shelf_project_id: value of the shared shelf's project coordinate.
        audience_credential: value of the audience's key slot. Compared, never printed.
        shelf_credential: value of the shelf's key slot. Compared, never printed.
        consumer: the declared consumer name, for the message (e.g. ``"un_crafd"``).

    Returns:
        ``audience_project_id.strip()`` — the value that was *checked*. Returning the
        unstripped original would hand the Appwrite client a value this function never
        compared: a launcher reading a coordinate out of a file gets a trailing newline,
        the comparison passes on the stripped forms, and the raw value goes into an HTTP
        header to fail as a 404 after the whole read and transform has run. The caller
        uses the return value rather than re-reading the environment, because a second
        read is a second chance to read the wrong coordinate name.

    Raises:
        AudienceIsolationError: if either project id is absent or blank, if the two
            projects are the same, or if the two credentials are the same.
    """
    if not isinstance(audience_project_id, str) or not audience_project_id.strip():
        _refuse(
            f"{consumer}: no audience project declared (got {audience_project_id!r}). "
            "The delivery writes into the audience's OWN Appwrite project and reads the "
            "shelf from the shared one; with no audience coordinate there is nowhere to "
            "write that is not the shelf. Refusing rather than falling back (#327 "
            "clause 2) — a fallback would publish where another partner's key can read "
            "it, and the consumer would report an empty endpoint rather than an error."
        )
    if not isinstance(shelf_project_id, str) or not shelf_project_id.strip():
        _refuse(
            f"{consumer}: the shelf project coordinate is absent or blank (got "
            f"{shelf_project_id!r}), so isolation CANNOT BE PROVEN and this refuses "
            "rather than reporting success. A gate whose input is missing must report a "
            "refusal or a skip, never a pass (the polarity C-113 was closed to fix): the "
            "earlier shape of this check compared nothing in exactly this case and then "
            "logged that the two projects were distinct. On the delivery's own path the "
            "shelf coordinate is asserted before this is reached, so reaching it here "
            "means the launcher exported the audience names and not the shelf's."
        )
    if audience_project_id.strip() == shelf_project_id.strip():
        _refuse(
            f"{consumer}: the audience project and the shared shelf resolve to the SAME "
            "project. Both coordinates are present, so nothing is 'missing' — this is "
            "the fallback #327 clause 2 forbids, wearing the costume of a working "
            "configuration. Either the audience slot was filled with the shelf's value, "
            "or the launcher exported one name and not the other. Project ids are "
            "non-secret coordinates, and this message deliberately does NOT print them: "
            "this repository is public and its CI logs are world-readable (register "
            "C-89). Compare the two names in the launcher's environment."
        )
    if (
        isinstance(audience_credential, str)
        and isinstance(shelf_credential, str)
        and audience_credential.strip()
        and audience_credential.strip() == shelf_credential.strip()
    ):
        _refuse(
            f"{consumer}: the audience and the shelf resolve to the SAME credential. The "
            "two projects differ, so the project check above passed — but an Appwrite key "
            "authenticates against exactly one project, so one of these two connections "
            "cannot work and will fail as a 401 somewhere inside the delivery instead of "
            "here. Neither value is printed, and the comparison did not need them: "
            "compare the two key coordinate NAMES in the launcher's environment."
        )
    # Logged at INFO because the delivery's own audit trail should record that it addressed
    # a project of its own — but see C-89: no VALUE is logged, only the fact that the two
    # connections differ. The coordinate NAME is the operator's handle for this.
    logger.info(
        "%s: audience connection is isolated from the shared shelf (distinct projects and "
        "distinct credentials, values not logged).",
        consumer,
    )
    return audience_project_id.strip()
