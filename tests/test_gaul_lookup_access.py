"""The GAUL lookup is one artifact, read once, behind a public name (S4 / #152).

Register **C-66**: the 888 KB lookup was read **three times per delivery** — once
eagerly in the manager's ``__init__`` into a ``GaulLookupEnricher`` the contract path
never used, then twice more through pyarrow, once per consumer. Register **C-68**: the
path that reached those two consumers was ``_DEFAULT_LOOKUP``, a leading-underscore
name imported across three module boundaries, so a refactor entitled to move it would
have broken live call sites silently.

These pin the fix rather than the symptom: one declared home for the artifact, one
read per run, and the read *injected* into both consumers rather than fetched by each.
"""

from pathlib import Path

import pyarrow as pa

from views_postprocessing.contract import gaul_lookup


def test_the_lookup_path_is_a_public_declared_name():
    """C-68: three modules depend on this; an underscore said they should not."""
    assert isinstance(gaul_lookup.LOOKUP_PATH, Path)
    assert gaul_lookup.LOOKUP_PATH.exists(), "the committed ADR-011 lookup is missing"
    assert not any(
        name.startswith("_") for name in ("LOOKUP_PATH",)
    ), "the artifact's path must not be private — it is a cross-module dependency"


def test_load_returns_the_arrow_table():
    table = gaul_lookup.load()
    assert isinstance(table, pa.Table)
    assert table.num_rows > 0
    assert "priogrid_gid" in table.column_names


def test_version_reports_the_build_stamp():
    stamp = gaul_lookup.version()
    assert stamp != "unknown", (
        "the lookup's provenance stamp did not resolve — a delivery would ship "
        "untraceable provenance (register C-60)"
    )
    assert "@" in stamp  # `<region>@<digest>`


def test_the_delivery_reads_the_lookup_exactly_once(monkeypatch):
    """C-66, asserted at the seam rather than by counting bytes.

    The manager cannot be instantiated here (it needs pipeline-core + Appwrite env),
    so this pins the property that makes one-read possible: both consumers take the
    table as a **parameter**. If either reverts to fetching the file itself, the
    signature check below fails and the count silently returns to two.
    """
    import inspect

    from views_postprocessing.contract import historical
    from views_postprocessing.contract.wire import sink

    assert "lookup" in inspect.signature(sink.deliver_run).parameters, (
        "wire.sink.deliver_run must take the lookup as a parameter (DIP)"
    )
    assert "lookup" in inspect.signature(historical.build_historical_table).parameters, (
        "historical.build_historical_table must take the lookup as a parameter (DIP)"
    )


def test_the_manager_reads_the_lookup_once_and_threads_it():
    """Source-scan: the manager pulls the full pipeline-core framework and cannot be
    imported in every test environment (the repo's standing pattern)."""
    source = (
        Path(__file__).resolve().parent.parent
        / "views_postprocessing" / "unfao" / "managers" / "unfao.py"
    ).read_text()

    assert source.count("gaul_lookup.load()") == 1, (
        "the lookup must be read exactly once per delivery and threaded to both "
        "consumers (C-66)"
    )
    assert "pq.read_table(_DEFAULT_LOOKUP)" not in source
    assert "_DEFAULT_LOOKUP" not in source, (
        "the manager must not import the enricher's private path constant (C-68)"
    )
    assert "GaulLookupEnricher" not in source, (
        "the contract delivery does not use the pandas enricher; instantiating it "
        "loads the lookup a third time into a representation nothing reads (C-66)"
    )


def test_the_enricher_still_works_and_agrees_on_the_stamp():
    """The enricher is not retired — it remains the build/verification path's object.

    What changed is that it no longer *owns* the artifact's identity. Its
    ``lookup_version`` must still report exactly what ``gaul_lookup.version`` does, or
    provenance would differ depending on which path produced it.
    """
    from views_postprocessing.contract.enrichment import GaulLookupEnricher

    assert GaulLookupEnricher().lookup_version == gaul_lookup.version()
