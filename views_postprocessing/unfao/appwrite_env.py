"""The Appwrite-seam environment this package requires, DECLARED (þing-01 P1, #134).

Names follow the PLATFORM-001 coordinate registry (connection + target classes)
plus the one operator-issued secret slot. The LAUNCHER assembles the environment
(views-models M3: run.sh reads the owned registry; the secret stays the operator
slot) — this package loads no dotenv and validates fail-loud instead (verdict D6).
The old implicit borrow (`load_dotenv(ensemble_path_manager.dotenv)`) was the
runtime edge of the platform's copy-chain (þing-01 sáttmál S6) and is dead.

Deliberately dependency-light: no pipeline-core imports, so the declaration is
importable (and testable) everywhere.
"""

from __future__ import annotations

import os

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
    or raise naming ALL missing variables — never a partial config that half-works."""
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        raise EnvironmentError(
            f"{store}: the launcher did not assemble the required environment — "
            f"missing {missing}. Coordinates come from the PLATFORM-001 registry "
            "(views-models run.sh declares its sourcing); the secret is the "
            "operator slot. This package no longer loads any dotenv (#134)."
        )
