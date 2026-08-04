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

import ast
import importlib
import inspect
import logging
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

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


def test_version_reports_the_declared_build_stamp():
    """C-60: the stamp is read from one declared key, not reconstructed.

    This used to assert ``stamp != "unknown"`` — a real check while ``version()``
    could *return* that placeholder. It no longer can: the branch is gone and the
    function raises instead. What is worth pinning now is the shape a delivery
    traces by.
    """
    stamp = gaul_lookup.version()
    assert "@" in stamp, f"expected `<region>@<short digest>`, got {stamp!r}"
    region, digest = stamp.split("@", 1)
    assert region and len(digest) == 8, stamp


def test_version_raises_rather_than_degrading_when_the_key_is_absent(tmp_path):
    """The load-bearing half of C-60's fix, without which it is unproven.

    An artifact built before the declared key existed — or by a future builder that
    forgets it — must stop the delivery, not hand it a placeholder that reads like a
    version. ``"unknown"`` in a provenance record is worse than a crash: it is
    written, stored and shipped, and nothing downstream can tell it from a real stamp.
    """
    unstamped = tmp_path / "no_version.parquet"
    pq.write_table(pa.table({"priogrid_gid": pa.array([1, 2, 3])}), unstamped)
    with pytest.raises(gaul_lookup.LookupVersionError, match="lookup_version"):
        gaul_lookup.version(unstamped)


def test_version_logs_before_it_raises(tmp_path, caplog):
    """ADR-008:48/51, matching the shape S1 (#182) gave the entry validators."""
    unstamped = tmp_path / "no_version.parquet"
    pq.write_table(pa.table({"priogrid_gid": pa.array([1])}), unstamped)
    with caplog.at_level(logging.ERROR):
        with pytest.raises(gaul_lookup.LookupVersionError):
            gaul_lookup.version(unstamped)
    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert len(errors) == 1 and "lookup_version" in errors[0].getMessage()


def test_version_no_longer_knows_the_producers_ledger_schema():
    """The declare-don't-infer half: the consumer stopped traversing upstream shape.

    ``version()`` reached three levels into views-datafactory's ingestion ledger —
    ``source_provenance`` → ``land_gaul_region`` → ``content_digest`` — inside a bare
    ``except … pass``. A rename upstream made every delivery untraceable with no
    signal. The builder composes the stamp now; this reads one key.

    **Tested by mechanism, not by word.** An earlier draft scanned the file for those
    key names and failed on the docstring above, which names them in order to explain
    the fix. Prose that records why a thing changed is not the thing. So this asserts
    the two capabilities the traversal required and the degrade depended on: JSON
    decoding of the producer's blob, and an exception handler that swallows. Neither
    can be present without the defect being reachable, and neither is triggered by a
    sentence.
    """
    module = importlib.import_module("views_postprocessing.contract.gaul_lookup")
    tree = ast.parse(inspect.getsource(module))

    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert "json" not in imports, (
        "gaul_lookup imports json again — decoding the producer's provenance blob is "
        "how the consumer came to know views-datafactory's schema (register C-60)."
    )

    handlers = [n for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler)]
    assert not handlers, (
        f"gaul_lookup has {len(handlers)} exception handler(s). The stamp degraded to "
        '"unknown" through a bare `except … pass`; this module now declares or raises.'
    )


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
    # The `GaulLookupEnricher` assertion that stood here was removed with the class in
    # #90 (register C-75). A guard against a symbol that no longer exists cannot fail,
    # and a test that cannot fail is decoration (ADR-014 §2). What it protected — one
    # read per delivery — is the first assertion in this function and still bites.


def test_the_artifacts_identity_comes_from_one_declared_reader():
    """The stamp has exactly one source, and it is the one the delivery reads.

    **This test used to assert that `GaulLookupEnricher.lookup_version` agreed with
    `gaul_lookup.version()`** — two readers of the same fact, checked against each
    other. The enricher was retired in #90/C-75 as an object with no production caller,
    so the agreement it policed no longer has two sides. What survives is the property
    that mattered: the version the delivery stamps into its provenance is read from the
    artifact, and resolves.
    """
    version = gaul_lookup.version()
    assert version, "the lookup must declare a version; C-60 made this raise rather than degrade"
    assert "@" in version, (
        f"lookup_version must be '<region>@<digest>', got {version!r} — the delivery "
        "carries this verbatim into its provenance record (C-15)."
    )
