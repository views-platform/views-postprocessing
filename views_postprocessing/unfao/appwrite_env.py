"""The Appwrite-seam environment this package requires, DECLARED (þing-01 P1, #134).

Names follow **the Appwrite Seam Contract**'s coordinate registry (connection +
target classes) plus the one operator-issued secret slot. The contract is homed in
views-appwrite and referenced by pinned URL, never copied — copies were the
platform's original failure (þing-01 sáttmál S6):

    https://github.com/views-platform/views-appwrite/blob/c7b597e/docs/ADRs/platform/coordinate_registry.toml

That pin is registry **v1.5.2** — declared below as
``SEAM_CONTRACT_VERSION`` / ``SEAM_CONTRACT_COMMIT`` so the pin is a value a test can
check rather than a fact buried in prose. A pinned URL does not rot, but it does go
stale, and nothing in this repository could previously tell you it had (register C-57).

**Pin from the tip of `main`, never from a sibling checkout's `HEAD`** (#196). The
first pin taken here was resolved with `git -C ../views-appwrite rev-parse HEAD` on a
checkout that happened to be sitting on an unmerged feature branch. That commit
declared v1.4.0, never reached `main`, and was withdrawn. A pin is a claim about what
the contract *says*; `HEAD` answers a different question — what someone was working
on.

The LAUNCHER assembles the environment
(views-models M3: run.sh reads the owned registry; the secret stays the operator
slot) — this package loads no dotenv and validates fail-loud instead (verdict D6).
The old implicit borrow (`load_dotenv(ensemble_path_manager.dotenv)`) was the
runtime edge of the platform's copy-chain (þing-01 sáttmál S6) and is dead.

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
#: declaration against that edition of the registry. ``tests/test_env_declaration.py``
#: enforces the pair against a local views-appwrite checkout when one is present.
SEAM_CONTRACT_VERSION = "1.5.2"
SEAM_CONTRACT_COMMIT = "c7b597e"

CONNECTION_ENV = (
    "APPWRITE_ENDPOINT",
    "APPWRITE_DATASTORE_PROJECT_ID",
    "APPWRITE_DATASTORE_API_KEY",  # secret slot — the value must never be logged
)
PROD_FORECASTS_ENV = (
    "APPWRITE_PROD_FORECASTS_BUCKET_ID",
    "APPWRITE_PROD_FORECASTS_BUCKET_NAME",
    "APPWRITE_PROD_FORECASTS_COLLECTION_ID",
    "APPWRITE_PROD_FORECASTS_COLLECTION_NAME",
    "APPWRITE_METADATA_DATABASE_ID",
    "APPWRITE_METADATA_DATABASE_NAME",
)
UNFAO_ENV = (
    "APPWRITE_UNFAO_BUCKET_ID",
    "APPWRITE_UNFAO_BUCKET_NAME",
    "APPWRITE_UNFAO_COLLECTION_ID",
    "APPWRITE_UNFAO_COLLECTION_NAME",
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
