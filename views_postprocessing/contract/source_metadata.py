"""Producer data-facts for the delivery — read straight from views-datafactory.

**Architectural principle (maintainer, 2026-06-26):** data-related facts — data,
metadata, validity dates, country/admin codes, ... — come from the **producer**
(views-datafactory, or viewser until it is phased out), **not** routed through
pipeline-core. pipeline-core is the orchestration framework, not a data pass-through;
depending on it for data facts couples the delivery to an unstable, mid-migration hub
(violates SDP, risks ADP cycles). This module is the **single place** the FAO delivery
asks datafactory for source metadata, so that coupling is isolated and named.

Today it serves ``last_valid_month_id`` (the time-validity boundary for S2/C-26). The
region cell-count (S1/C-34 SSOT) and other producer facts belong here too as datafactory
publishes them.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def last_valid_month_id(zarr_url: str | None = None) -> int | None:
    """The producer's last *observed* month for the served zarr (a datafactory fact).

    Reads datafactory's published ``.zattrs["last_valid_month_id"]`` directly via
    ``datafactory_query`` (a timeout-protected HTTP read of the producer's own metadata).
    Returns ``None`` if the store predates the attribute.

    Args:
        zarr_url: the served zarr; ``None`` uses datafactory's default store (which the
            FAO queryset itself uses — ``ZARR_URL = DEFAULT_REMOTE.zarr_url``).

    The import is lazy so this module loads without the heavy datafactory dependency
    present (e.g. in unit-test environments).
    """
    from datafactory_query.defaults import get_last_valid_month_id

    return get_last_valid_month_id(zarr_url)
