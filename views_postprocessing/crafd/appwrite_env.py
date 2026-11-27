"""The Appwrite-seam environment this package requires, DECLARED (þing-01 P1, #134).
Clone of ``unfao/appwrite_env.py`` for the CRAF'd delivery (its own outbound bucket).

Names follow **the Appwrite Seam Contract**'s coordinate registry (connection +
target classes) plus the one operator-issued secret slot. The contract is homed in
views-appwrite and referenced by pinned URL, never copied — copies were the
platform's original failure (þing-01 sáttmál S6):

    https://github.com/views-platform/views-appwrite/blob/a251cb8/docs/ADRs/platform/coordinate_registry.toml

That pin is registry **v1.9.1** — declared below as ``SEAM_CONTRACT_VERSION`` /
``SEAM_CONTRACT_COMMIT`` so the pin is a value a test can check rather than a fact
buried in prose. A pinned URL does not rot, but it does go stale, and nothing in this
repository could previously tell you it had (register C-57).

**The first pin taken here predated its own coordinates having values**, so it was stale
by commit and not only by version, and no test could see it — the drift check was scoped
to the FAO package by name. Register **C-57** holds the commits and dates; the check is
now scoped to both packages.

**Pin from the tip of `main`, never from a sibling checkout's `HEAD`** (#196).

The LAUNCHER assembles the environment
(views-models M3: run.sh reads the owned registry; the secret stays the operator
slot) — this package loads no dotenv and validates fail-loud instead (verdict D6).

Deliberately dependency-light: no pipeline-core imports, so the declaration is
importable (and testable) everywhere.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

#: The Appwrite Seam Contract edition these names were verified against, and the commit
#: this repo cites. **A version string and a sha are not coordinate values** — the
#: registry forbids copying its values, and nothing here copies one. What is recorded is
#: *which edition was read*, which is exactly what makes drift detectable.
#:
#: Bumping these is not bookkeeping: it asserts that someone re-checked this module's
#: declaration against that edition. ``tests/test_env_declaration.py`` enforces the pair,
#: here and in ``unfao`` alike, against a local views-appwrite checkout when present.
SEAM_CONTRACT_VERSION = "1.9.1"
SEAM_CONTRACT_COMMIT = "a251cb8"

#: The SHELF connection: the shared project the delivery READS. Unchanged by #327.
CONNECTION_ENV = (
    "APPWRITE_ENDPOINT",
    "APPWRITE_DATASTORE_PROJECT_ID",
    "APPWRITE_DATASTORE_API_KEY",  # secret slot — the value must never be logged
)

#: Alias: "CONNECTION_ENV" stopped being unambiguous once a second connection existed.
#: The old name stays — the launcher and tests reference it (#327).
SHELF_CONNECTION_ENV = CONNECTION_ENV

#: The AUDIENCE connection: CRAF'd's OWN Appwrite project, which this delivery WRITES to
#: (#327) — a different *project* from the shelf above, not another bucket in it.
#: ``APPWRITE_CRAFD_PROJECT_ID`` is registry-declared from edition 1.8.0.
#:
#: ``APPWRITE_CRAFD_PUBLISHER_API_KEY`` is MINTED by a registry slot of its own, added in
#: edition **v1.9.1** (views-appwrite#211 → PR #212, merged 2026-11-27); the spelling this
#: module was built against was adopted unchanged. A key authenticates against exactly one
#: project, so the shelf key cannot reach the audience project, and one env-var name cannot
#: carry two live values in one process — **#327**, views-appwrite#208.
#:
#: The pin below names v1.9.1 at views-appwrite ``main``'s tip (PR #213, tag
#: ``appwrite-seam-v1.9.1``), as #196 requires. Read the registry with
#: ``git show <commit>:<path>``, never a working tree: a pin set that way named an edition
#: its commit did not carry, unseen because both guards ran below the floor — **C-125**.
AUDIENCE_CONNECTION_ENV = (
    "APPWRITE_ENDPOINT",
    "APPWRITE_CRAFD_PROJECT_ID",
    "APPWRITE_CRAFD_PUBLISHER_API_KEY",  # secret slot — the value must never be logged
)
PROD_FORECASTS_ENV = (
    "APPWRITE_PROD_FORECASTS_BUCKET_ID",
    "APPWRITE_PROD_FORECASTS_BUCKET_NAME",
    "APPWRITE_PROD_FORECASTS_COLLECTION_ID",
    "APPWRITE_PROD_FORECASTS_COLLECTION_NAME",
    "APPWRITE_METADATA_DATABASE_ID",
    "APPWRITE_METADATA_DATABASE_NAME",
)
CRAFD_ENV = (
    "APPWRITE_CRAFD_BUCKET_ID",
    "APPWRITE_CRAFD_BUCKET_NAME",
    "APPWRITE_CRAFD_COLLECTION_ID",
    "APPWRITE_CRAFD_COLLECTION_NAME",
    "APPWRITE_METADATA_DATABASE_ID",
    "APPWRITE_METADATA_DATABASE_NAME",
)


def assert_env_declared(names: tuple, *, store: str) -> None:
    """Entry validation (þing-01 D6): every required name resolved and non-empty,
    or raise naming ALL missing variables — never a partial config that half-works.

    Logs at ERROR before raising (ADR-008): the refusal must survive in the run's
    log, not only in a traceback the operator no longer has. Names only — the
    resolved value of a variable is never read, and never logged.

    Args:
        names: the environment-variable names this store requires.
        store: the store being configured, for the message.

    Raises:
        EnvironmentError: naming every missing variable.
    """
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        # `missing` holds NAMES, never values: membership is decided by
        # `os.getenv(name)` being falsy, and the resolved value is never read.
        # That is what makes this loggable at all — CONNECTION_ENV carries the
        # APPWRITE_DATASTORE_API_KEY secret slot.
        err_msg = (
            f"{store}: the launcher did not assemble the required environment — "
            f"missing {missing}. Coordinates come from the Appwrite Seam Contract's "
            "coordinate registry, homed in views-appwrite (views-models run.sh "
            "declares its sourcing); the secret is the operator slot. This package "
            "no longer loads any dotenv (#134)."
        )
        logger.error(err_msg)  # ADR-008: logged persistently AND raised
        raise EnvironmentError(err_msg)
