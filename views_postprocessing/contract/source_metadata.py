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


class ProducerClientMissing(RuntimeError):
    """``datafactory_query`` is not importable, so no producer fact can be read."""


def last_valid_month_id(zarr_url: str | None = None) -> int | None:
    """The producer's last *observed* month for the served zarr (a datafactory fact).

    Reads datafactory's published ``.zattrs["last_valid_month_id"]`` directly via
    ``datafactory_query`` (a timeout-protected HTTP read of the producer's own metadata).
    Returns ``None`` if the store predates the attribute.

    Args:
        zarr_url: the served zarr; ``None`` uses datafactory's default store (which the
            FAO queryset itself uses — ``ZARR_URL = DEFAULT_REMOTE.zarr_url``).

    Raises:
        ProducerClientMissing: if ``datafactory_query`` cannot be imported.

    **The dependency is the launcher's to supply, and it does.** ``datafactory_query``
    ships inside ``views-datafactory``; it is not separately installable and it is not
    declared in this repository's ``pyproject.toml``. Both launchers declare it —
    views-models ``postprocessors/{un_fao,un_crafd}/requirements.txt`` pin
    ``views-datafactory>=1.9.0,<2.0.0``. The import stays lazy so this module, and
    everything that imports it, loads in a unit-test environment without the producer's
    (heavy) package present.

    **Why the absence raises rather than returning None (register C-103).** The caller
    degrades open when the boundary is unavailable — a deliberate C-26 decision, because
    a producer that publishes no ``last_valid_month_id`` is a normal, older store. But a
    *missing client* is not that. It is a broken environment, and returning ``None`` for
    it would make the two indistinguishable and ship the unobserved zero-padded tail as
    observed history. Same shape as C-60, where a provenance stamp degraded to
    ``"unknown"`` on a bare except and made every delivery untraceable.

    This is defence in depth rather than the first line: a missing ``datafactory_query``
    already fails earlier and louder, because the postprocessor's ``config_queryset``
    imports it at module scope and raises, which ``launch_config.
    assert_queryset_was_importable`` turns into a refusal before any frame is read
    (C-83). Verified 2026-08-17. This guard exists for the paths that gate does not
    cover — a direct caller, a future launcher, a partner that does not go through the
    same queryset.
    """
    try:
        from datafactory_query.defaults import get_last_valid_month_id
    except ImportError as exc:
        err_msg = (
            "datafactory_query is not importable, so the producer's "
            "last_valid_month_id cannot be read. It ships inside views-datafactory "
            "(there is no separate distribution), and the launcher is expected to "
            "supply it: pip install 'views-datafactory>=1.9.0,<2.0.0'. Refusing rather "
            "than reporting 'no boundary published', which is a different condition and "
            "would let unobserved months ship as observed history (C-103, C-26)."
        )
        logger.error(err_msg)  # ADR-008: logged persistently AND raised
        raise ProducerClientMissing(err_msg) from exc

    return get_last_valid_month_id(zarr_url)
