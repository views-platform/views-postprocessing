from views_pipeline_core.managers.postprocessor.postprocessor import (
    PostprocessorManager,
    PostprocessorPathManager,
)
import logging

from views_pipeline_core.modules.appwrite.file import AppwriteConfig
from views_pipeline_core.modules.datastore import DatastoreModule
from views_pipeline_core.managers.model import ForecastingModelManager

from views_pipeline_core.managers.ensemble import EnsemblePathManager
from datetime import datetime
import os
from views_pipeline_core.modules.dataloaders.datafactory_contract import declared_data_format
from views_postprocessing.contract import frame_extraction, gaul_lookup, historical, launch_config, source_metadata
from views_postprocessing.crafd import appwrite_env, product
from views_postprocessing.crafd.store_port import _ContractStorePort
from views_postprocessing.contract.wire import sink as wire_sink
from views_postprocessing.contract.wire import source_selection
from views_postprocessing.delivery import coverage, findability, observed_range, provenance
from pathlib import Path

logger = logging.getLogger(__name__)



def _build_prod_forecasts_store(ensemble_name: str | None) -> DatastoreModule:
    """The shared internal store (ADR-013's "shared shelf"), built from the
    launcher-assembled environment (validated fail-loud; þing-01 #134 — no dotenv is
    loaded here).

    pipeline-core's ``DatastoreModule.get_predictions_by_metadata`` injects an automatic
    ``name == model_name`` filter on every lookup. The contract read must **not** have
    it: ADR-013 artifacts are named ``{run_id}__{target}__m{month}.arrow.parquet``
    (never the bare ensemble name), so an injected ``name == "rusty_bucket"`` matches
    nothing and also clobbers the wire layer's own run-id / target / name filters.
    Suppressed unconditionally below — the retired legacy reader was the only caller
    that needed it on (#149).

    **A function, not a method (register C-40).** It reads no manager state: the
    ensemble name arrives as an argument rather than through ``self.configs``, and the
    ``EnsemblePathManager`` is local — it used to be assigned to
    ``self.ensemble_path_manager`` and then read exactly once, four lines later, in this
    same body. Nothing else in either partner package, or in views-models, ever read it.
    A method-local value wearing the costume of manager state.

    The gain is C-40's consequence (a): this is callable, and its refusals observable,
    with **no manager instance, no views-models path manager and no Appwrite
    environment** — see ``tests/test_store_construction.py``.
    """
    if not ensemble_name:
        err_msg = "Ensemble name must be provided in configs with the `ensemble` key for forecasting. Cannot proceed."
        logger.error(err_msg)
        raise ValueError(err_msg)
    path_manager = EnsemblePathManager(ensemble_name_or_path=ensemble_name, validate=False)

    appwrite_env.assert_env_declared(
        appwrite_env.CONNECTION_ENV + appwrite_env.PROD_FORECASTS_ENV,
        store="production_forecasts datastore",
    )
    appwrite_config = AppwriteConfig(
        path_manager=path_manager,
        endpoint=os.getenv("APPWRITE_ENDPOINT"),
        project_id=os.getenv("APPWRITE_DATASTORE_PROJECT_ID"),
        credentials=os.getenv("APPWRITE_DATASTORE_API_KEY"),
        auth_method="api_key",
        cache_ttl_hours=24,
        bucket_id=os.getenv("APPWRITE_PROD_FORECASTS_BUCKET_ID"),
        bucket_name=os.getenv("APPWRITE_PROD_FORECASTS_BUCKET_NAME"),
        collection_id=os.getenv("APPWRITE_PROD_FORECASTS_COLLECTION_ID"),
        collection_name=os.getenv("APPWRITE_PROD_FORECASTS_COLLECTION_NAME"),
        database_id=os.getenv("APPWRITE_METADATA_DATABASE_ID"),
        database_name=os.getenv("APPWRITE_METADATA_DATABASE_NAME"),
    )
    datastore = DatastoreModule(appwrite_file_manager_config=appwrite_config)
    # Suppress the automatic name==model_name filter (see docstring). model_path is used
    # by DatastoreModule only for that injection and for uploads; the contract read
    # neither uploads nor performs any model-scoped lookup.
    datastore.model_path = None
    return datastore


def _build_partner_store(model_path) -> DatastoreModule:
    """The partner-facing store (`crafd_bucket`) — a function for the same reason as above.

    ``model_path`` is the framework's own path manager, so it is passed in rather than
    reached for. That is the whole difference between this and a method, and it is what
    lets the environment contract be checked without standing up a manager.
    """
    return DatastoreModule(appwrite_file_manager_config=_partner_appwrite_config(model_path))


def _partner_appwrite_config(model_path) -> AppwriteConfig:
    """Env → ``AppwriteConfig`` for the partner bucket. Declared names only; the values
    live in the environment and are never read into this repository's source."""
    appwrite_env.assert_env_declared(
        appwrite_env.CONNECTION_ENV + appwrite_env.CRAFD_ENV,
        store="crafd_bucket datastore",
    )
    return AppwriteConfig(
        path_manager=model_path,
        endpoint=os.getenv("APPWRITE_ENDPOINT"),
        project_id=os.getenv("APPWRITE_DATASTORE_PROJECT_ID"),
        credentials=os.getenv("APPWRITE_DATASTORE_API_KEY"),
        auth_method="api_key",
        cache_ttl_hours=24,
        bucket_id=os.getenv("APPWRITE_CRAFD_BUCKET_ID"),
        bucket_name=os.getenv("APPWRITE_CRAFD_BUCKET_NAME"),
        collection_id=os.getenv("APPWRITE_CRAFD_COLLECTION_ID"),
        collection_name=os.getenv("APPWRITE_CRAFD_COLLECTION_NAME"),
        database_id=os.getenv("APPWRITE_METADATA_DATABASE_ID"),
        database_name=os.getenv("APPWRITE_METADATA_DATABASE_NAME"),
    )


def _build_partner_read_store(model_path) -> DatastoreModule:
    """The partner store for the C-94 read-back, with pipeline-core's automatic
    ``name == model_name`` filter suppressed — otherwise the preflight would verify the
    views-models directory name, which equals the declared consumer name only by
    coincidence (**C-77**). C-94 records why it reuses the write key.
    """
    store = DatastoreModule(appwrite_file_manager_config=_partner_appwrite_config(model_path))
    store.model_path = None
    return store


def _assert_delivery_is_findable(model_path, consumer_name: str, uploaded: dict) -> None:
    """C-94: ask the store the question the consumer asks, and refuse silence.

    A function, not a method (C-40 (a)) — its refusal is observable without a manager
    or an Appwrite environment. ``uploaded`` maps each leg to the file id THIS run put
    there; `delivery/findability.py` carries why that scoping is the whole guard.
    """
    for category, expected in uploaded.items():
        try:
            port = _ContractStorePort(_build_partner_read_store(model_path))
            found = port.latest_file_id({"name": consumer_name, "category": category})
        except Exception as exc:  # could not ask != asked and got nothing (C-99, C-103)
            raise findability.unverified(category, exc) from exc
        findability.assert_findable(
            found, expected_file_id=expected, consumer_name=consumer_name, category=category
        )
    logger.info("Findability preflight passed: both legs retrievable under %r.", consumer_name)


class CRAFDPostProcessorManager(PostprocessorManager, ForecastingModelManager):
    def __init__(
        self,
        model_path: PostprocessorPathManager,
        wandb_notifications: bool = True,
        use_prediction_store: bool = False,
    ) -> None:
        super().__init__(model_path, wandb_notifications, use_prediction_store)

        # Add your custom initialization below
        logger.info(f"Initializing {self.__class__.__name__}")
        self._forecast_resolution = None  # {target: TargetLease}, set by _read
        self._historical_frame = None  # views_frames.FeatureFrame, set by _read

    def _read_historical_frame(self):
        """#126: historical actuals as a views_frames.FeatureFrame — the first
        production consumer of pipeline-core's frame-native fetch. Same clip
        policy as the legacy path (producer-sourced boundary, degrade-open)."""
        frame = self._data_loader.get_feature_frame(
            partition="forecasting", use_saved=False, level="pgm", validate=True
        )
        try:
            lv = source_metadata.last_valid_month_id(self.configs.get("zarr_url"))
        except source_metadata.ProducerClientUnavailable:
            # NOT degrade-open. A producer client that will not load is a broken
            # environment, not a producer that publishes no boundary — and the whole
            # point of the two branches is that they are different conditions (C-103).
            raise
        except Exception:
            logger.warning(
                "last_valid_month_id could not be read; skipping the observed-range "
                "clip (degrade-open, C-26). Any unobserved months above the producer's "
                "boundary WILL ship as observed history in this delivery.",
                exc_info=True,
            )
            lv = None
        if lv is None:
            self._historical_frame = frame
            return
        fabricated = observed_range.fabricated_months(frame_extraction.months_of(frame), lv)
        if len(fabricated):
            logger.warning(
                "Dropping %d fabricated (unobserved) month(s) above last_valid_month_id=%d.",
                len(fabricated), lv,
            )
            frame = frame_extraction.drop_months_above(frame, lv)
        self._historical_frame = frame

    def _read_historical_data(self):
        """Historical actuals, frame-native only (#126).

        The queryset must DECLARE ``data_format: feature_frame`` — pipeline-core's
        ``declared_data_format`` is the one gate, and a queryset that declares
        anything else is refused rather than quietly read through a retired pandas
        path (register C-63, #149).
        """
        # Declaration first: the check reads the queryset, not the loader, so a
        # refused config must not pay for loader construction.
        #
        # Read ONCE, and distinguish "could not import it" from "it declares the wrong
        # thing" (register C-83). Passing None straight into `declared_data_format`
        # turns a failed import into a confident, wrong claim about the config.
        queryset = self._model_path.get_queryset()
        launch_config.assert_queryset_was_importable(queryset)
        launch_config.assert_frame_native_historical(declared_data_format(queryset))
        self._initialize_data_loader()
        self._read_historical_frame()

    def _read_forecast_data_contract(self):
        """ADR-013 contract inbound (epic #105; streaming since the run-0 OOM fix):
        RESOLVE the newest fully-manifested run — manifests + pinned shard
        file_ids only, no heavy bytes. Frames materialize one target at a time
        inside the sink at _save (each lease loads → verifies → curates → is
        released). The `wire/` package owns the policy; this method only adapts
        the store (DIP) and declares the product facts (region curation +
        coverage expectations live in the lease, where frames exist)."""
        port = _ContractStorePort(_build_prod_forecasts_store(self.configs.get("ensemble")))
        region = self.configs.get("region")
        self._forecast_resolution = source_selection.resolve_run(
            port,
            expected_targets=product.TARGETS,
            expected_ensemble=self.configs["ensemble"],
            excluded_gids=coverage.excluded_for(region),
            expected_cells=coverage.expected_for(region),
        )
        run_id = next(iter(self._forecast_resolution.values())).run_id
        logger.info(
            "Contract inbound resolved: run %s (%d targets leased; region=%r; "
            "heavy fetch deferred to delivery).",
            run_id,
            len(self._forecast_resolution),
            region,
        )

    def _read_forecast_data(self):
        """Forecast inbound — ADR-013 contract only.

        The launcher must DECLARE ``wire_contract: True``. The pandas reader this
        key used to select was retired in #149; omitting the key is a refusal, not
        a fallback (register C-63).
        """
        launch_config.assert_contract_mode(self.configs)
        self._read_forecast_data_contract()

    def _read(self) -> any:
        self._read_historical_data()
        self._read_forecast_data()

    def _transform(self) -> None:
        """No-op by design.

        Geography is not joined into either payload: the historical artifact
        attaches it at build time (``contract/historical.py``) and the forecast ships
        it as the §5 GAUL sidecar, built in the sink at ``_save``. The hook stays
        so the Template Method's phases remain truthful.
        """
        return

    def _validate(self) -> None:
        """Assert the read produced what the save needs, then check coverage.

        Neither payload is null-gated here. The historical artifact's metadata
        null-gate fires at build time (``historical.assert_metadata_complete``);
        the forecast's guarantees are the wire's own verified chain — content
        hashes, header/payload asserts, and per-target coverage inside each
        lease's ``load()``, plus the §6 no-collapse gate and gid parity at
        ``_save``. This phase asserts the RESOLUTION happened, keeping the
        Template Method's phases truthful: ``_read`` resolves, ``_save``
        materializes.
        """
        if self._historical_frame is None:
            raise ValueError("no historical frame — _read did not run.")
        if self._forecast_resolution is None:
            raise ValueError("no resolved forecast run — _read did not resolve.")
        logger.info(
            "Historical is frame-native: the metadata null-gate is enforced at "
            "artifact build (historical.assert_metadata_complete)."
        )
        self._check_coverage()

    def _check_coverage(self) -> None:
        """Log delivered cell counts and enforce the region coverage contract (S1/C-34).

        Orchestration only: extract primitives via ``frame_extraction``, then call
        the representation-free ``delivery.coverage`` invariant — the rule is
        *called*, not embedded. The count-gate fires only for regions pinned in
        ``coverage.EXPECTED_CELLS``; an unpinned/unresolved region logs a skipped gate
        rather than guessing.

        Only the historical leg is checked here. Forecast coverage is asserted
        inside each lease's ``load()``, where the frame actually exists — see
        ``wire/source_selection``.
        """
        region = self.configs.get("region")
        expected = coverage.expected_for(region)
        excluded = coverage.excluded_for(region)
        for label, cells, n_rows in [self._historical_coverage_source()]:
            logger.info(
                "%s delivery coverage: %d distinct cells, %d rows.",
                label,
                len(cells),
                n_rows,
            )
            # GAUL-uncovered cells the curated region must drop (S4/C-30) — checked
            # before the count gate so a leaked island names itself, not "over-coverage
            # by 1". Empty for unpinned regions (e.g. africa_me_legacy keeps its ocean
            # cells), so this is a no-op there.
            if excluded:
                coverage.assert_no_excluded_cells(cells, excluded, label=label)
            if expected is not None:
                coverage.assert_complete_coverage(cells, expected, label=label)
            else:
                logger.warning(
                    "Coverage count-gate skipped for %s: region %r is not pinned in "
                    "delivery.coverage.EXPECTED_CELLS — verify and pin before relying on it.",
                    label,
                    region,
                )

    def _save_contract(self) -> dict:
        """ADR-013 contract outbound (epic #105): the composed sink delivers the run.

        The §11.4 interlock is enforced by ``wire.sink`` itself: with the default
        ``product.UPLOAD_ENABLED=False`` (overridable only by the explicit
        ``wire_upload_enabled`` launch-config key), artifacts are staged locally and
        ZERO store calls occur. First live enablement is gated on C-161 closure.
        """
        if self._forecast_resolution is None:
            raise ValueError(
                "contract _save called without a resolved run — _read must run first."
            )
        # ONE read of the 888 KB lookup per delivery (#152/C-66), threaded to both
        # consumers — each takes it as a parameter (DIP), so neither reaches for the
        # file itself.
        lookup = gaul_lookup.load()
        upload_enabled = bool(self.configs.get("wire_upload_enabled", product.UPLOAD_ENABLED))
        store = _ContractStorePort(_build_partner_store(self._model_path)) if upload_enabled else None
        # The wire is partner-neutral (#153): the manager supplies CRAF'd's product
        # facts explicitly rather than the mechanism reaching for them.
        summary = wire_sink.deliver_run(
            self._forecast_resolution,
            lookup=lookup,
            staging_dir=Path(self._model_path.data_generated) / "wire_contract",
            consumer_name=product.CONSUMER_DOCUMENT_NAME,
            s_min=product.S_MIN,
            store=store,
            upload_enabled=upload_enabled,
        )
        # Historical leg (#126): the CRAF'd product ships actuals alongside the wire —
        # frame-built, same artifact shape the FAO delivery already ships, same interlock.
        if self._historical_frame is None:
            raise ValueError(
                "contract _save: no historical frame — the un_crafd descriptor must "
                "declare data_format: feature_frame (#126)."
            )
        hist_path, hist_description, _ = self._build_historical_artifact(
            Path(summary["staging_dir"]), lookup
        )
        if upload_enabled:
            hist_file_id = store.upload(
                hist_path,
                filename=hist_path.name,
                # The DECLARED consumer name, not `self._model_path.model_name`
                # (register C-77). Both resolve to the same string today, because
                # `model_name` is the views-models directory name and that directory
                # happens to match — but only one of them is a declaration. The other
                # is a filesystem coincidence in a different repository, and a
                # directory rename there would strand this artifact silently: the
                # consumer filters on the declared name, finds nothing, and reports
                # an empty endpoint rather than an error (ADR-013 §4.1a).
                name=product.CONSUMER_DOCUMENT_NAME,
                doc_type="model",
                category="historical",
                loa="pgm",
                targets=list(self.configs.get("targets", [])),
                description=hist_description,
            )
            logger.info("uploaded %s (historical, run %s)", hist_path.name, summary["run_id"])
            # C-94: nothing above observes the OUTCOME of an upload. Every call
            # reported success in run-0 too, and the historical leg still stranded.
            _assert_delivery_is_findable(
                self._model_path,
                product.CONSUMER_DOCUMENT_NAME,
                {"forecast": summary["manifest_file_id"], "historical": hist_file_id},
            )
        else:
            logger.info(
                "Interlock holding: historical artifact staged at %s (no store calls).",
                hist_path,
            )
        summary["historical"] = hist_path.name
        return summary

    def _save(self) -> dict:
        """Deliver the run — ADR-013 contract only (#149)."""
        return self._save_contract()

    def _historical_coverage_source(self):
        """(label, cells, n_rows) for the historical frame."""
        return (
            "historical",
            frame_extraction.cells_of(self._historical_frame),
            self._historical_frame.n_rows,
        )

    def _historical_frame_description(self, table, timestamp: str) -> str:
        """The C-15 provenance description for the frame-built historical artifact."""
        region = self.configs.get("region")
        prov = provenance.build_provenance(
            lookup_version=gaul_lookup.version(),
            region=region,
            expected_cell_count=coverage.expected_for(region),
            actual_cell_count=len(frame_extraction.cells_of(self._historical_frame)),
            unmapped_count=historical.unmapped_cell_count(table),
        )
        return provenance.compact_description(prov)

    def _build_historical_artifact(self, directory, lookup) -> tuple:
        """Frame-built historical artifact staged into ``directory``; returns
        (path, description, timestamp). Null-gate enforced here (fail loud).

        ``lookup`` is the already-read GAUL table (injected, not fetched — #152).
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        table = historical.build_historical_table(self._historical_frame, lookup)
        historical.assert_metadata_complete(table)
        path = Path(directory) / f"historical_dataset_{timestamp}.parquet"
        historical.write_historical_artifact(table, path)
        return path, self._historical_frame_description(table, timestamp), timestamp
