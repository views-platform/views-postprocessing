from views_pipeline_core.managers.postprocessor.postprocessor import (
    PostprocessorManager,
    PostprocessorPathManager,
)
from views_pipeline_core.files.utils import read_dataframe
import logging
from views_pipeline_core.data.handlers import PGMDataset

from views_pipeline_core.modules.appwrite.file import AppwriteConfig
from views_pipeline_core.modules.datastore import DatastoreModule
from views_pipeline_core.managers.model import ForecastingModelManager

from views_pipeline_core.managers.ensemble import EnsemblePathManager
import pandas as pd
import io
import json
from datetime import datetime
import os
from dotenv import load_dotenv
from views_postprocessing.unfao.enrichment import _DEFAULT_LOOKUP, GaulLookupEnricher
from views_postprocessing.unfao.gaul_schema import METADATA_COLS
from views_postprocessing.unfao import extraction, frame_extraction, product, source_metadata
from views_postprocessing.unfao.wire import sink as wire_sink
from views_postprocessing.unfao.wire import source_selection
from views_postprocessing.delivery import coverage, identity, observed_range, provenance
from pathlib import Path

logger = logging.getLogger(__name__)

# Hop-A legacy selection filters (ADR-013 §11.4 transition guard). Declared, not
# inferred: the legacy production forecast is uploaded by pipeline-core's ensemble run
# with type="ensemble"; the contract's sampled_forecast_* types are disjoint by design,
# so pinning the legacy type here makes contract artifacts unselectable by this reader.
# Golden-string-tested (tests/test_selection_guard.py); change only with ADR-013.
LEGACY_FORECAST_FILTERS = {"category": "forecast", "type": "ensemble"}


class _ContractStorePort:
    """Adapts ``DatastoreModule`` to the wire ports (ADR-013 epic #105; DIP —
    ``wire/source_selection`` and ``wire/sink`` never see Appwrite types)."""

    def __init__(self, datastore: DatastoreModule) -> None:
        self._dsm = datastore

    def latest_file_id(self, filters: dict):
        return self._dsm.get_latest_file_id(filters=filters)

    def file_metadata(self, file_id: str) -> dict:
        return extraction.file_metadata(self._dsm.get_file_metadata(file_id))

    def download(self, file_id: str) -> bytes:
        return (
            self._dsm.download_prediction(file_id).to_dict().get("data", {}).get("file_bytes", None)
        )

    def upload(self, file_path, *, filename, name, doc_type, category, loa, targets) -> None:
        self._dsm.upload_data(
            file=file_path,
            filename=filename,
            name=name,
            type=doc_type,
            category=category,
            loa=loa,
            targets=targets,
        )


class UNFAOPostProcessorManager(PostprocessorManager, ForecastingModelManager):
    def __init__(
        self,
        model_path: PostprocessorPathManager,
        wandb_notifications: bool = True,
        use_prediction_store: bool = False,
    ) -> None:
        super().__init__(model_path, wandb_notifications, use_prediction_store)

        # Add your custom initialization below
        logger.info(f"Initializing {self.__class__.__name__}")
        self._historical_dataframe = None
        self._forecast_dataframe = None

        self._historical_dataset = None
        self._forecast_dataset = None
        self._forecast_run = None  # contract mode: {target: (frame, headers)}
        self._enricher = GaulLookupEnricher()
        self.ensemble_path_manager = None

    def _read_historical_data(self):
        self._initialize_data_loader()
        run_type = "forecasting"

        self._data_loader.get_data(
                use_saved=False,
                validate=False,
                self_test=False,
                partition=run_type
            )
        self._historical_dataframe = read_dataframe(
            self._data_loader.cached_data_path
        )
        self._clip_observed_history()
        self._historical_dataset = PGMDataset(
            source=self._historical_dataframe, targets=self.configs.get("targets")
        )

    def _prod_forecasts_datastore(self) -> DatastoreModule:
        """The shared internal store (ADR-013's 'shared shelf'), configured from the
        declared ensemble's environment. Used by both the legacy and contract reads."""
        ensemble_name = self.configs.get("ensemble", None)
        if not ensemble_name:
            err_msg = "Ensemble name must be provided in configs with the `ensemble` key for forecasting. Cannot proceed."
            logger.error(err_msg)
            raise ValueError(err_msg)
        self.ensemble_path_manager = EnsemblePathManager(ensemble_name_or_path=ensemble_name, validate=False)
        # ensemble_configs = EnsembleManager(
        #     ensemble_path=self.ensemble_path_manager,
        # ).configs

        # loa = ensemble_configs.get("level", None)
        loa = "pgm"
        if not loa:
            err_msg = "level must be defined in the ensemble configurations (e.g, pgm, cm). Cannot proceed."
            logger.error(err_msg)
            raise ValueError(err_msg)
        
        # Force it to the correct .env just to be safe
        load_dotenv(dotenv_path=str(self.ensemble_path_manager.dotenv))

        appwrite_config = AppwriteConfig(
            path_manager=self.ensemble_path_manager,
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
        return DatastoreModule(appwrite_file_manager_config=appwrite_config)

    def _read_forecast_data_contract(self):
        """ADR-013 contract inbound (epic #105): assemble the newest fully-manifested
        run — declared targets awaited, declared ensemble verified. The `wire/`
        package owns the policy; this method only adapts the store (DIP)."""
        port = _ContractStorePort(self._prod_forecasts_datastore())
        self._forecast_run = source_selection.fetch_run(
            port,
            expected_targets=product.TARGETS,
            expected_ensemble=self.configs["ensemble"],
        )
        # Declared-region curation (C-30/S4, at the anti-corruption layer): the
        # producer publishes its full model grid; the FAO product excludes the
        # declared GAUL-uncovered cells. Explicit frozenset, never inference.
        excluded = coverage.excluded_for(self.configs.get("region"))
        if excluded:
            self._forecast_run = {
                target: (frame_extraction.drop_units(frame, excluded), headers)
                for target, (frame, headers) in self._forecast_run.items()
            }
            logger.info(
                "Declared-region curation applied: %d excluded cells dropped per "
                "target (region=%r).",
                len(excluded),
                self.configs.get("region"),
            )
        run_id = next(iter(self._forecast_run.values()))[1][0]["run_id"]
        logger.info(
            "Contract inbound: run %s assembled (%d targets).",
            run_id,
            len(self._forecast_run),
        )

    def _read_forecast_data(self):
        # Explicit declared mode (ADR-013; never inferred from store contents).
        if self.configs.get("wire_contract"):
            self._read_forecast_data_contract()
            return
        loa = "pgm"
        try:
            prediction_store_manager = self._prod_forecasts_datastore()

            # Resolve the newest legacy forecast, then verify its identity before
            # delivering it (S3/C-25): a stray upload must not be silently shipped as
            # the configured ensemble. The `type` pin is the Hop-A legacy transition
            # guard (ADR-013 §11.4): legacy ensemble forecasts carry type="ensemble"
            # (pipeline-core EnsemblePathManager._target), disjoint from the contract's
            # sampled_forecast_* vocabulary — so pipeline-core#269's shard/manifest
            # uploads can never be selected by this legacy reader.
            file_id = prediction_store_manager.get_latest_file_id(filters=LEGACY_FORECAST_FILTERS)
            if file_id is None:
                raise FileNotFoundError(
                    f"No forecast file found in the prediction store (filters={LEGACY_FORECAST_FILTERS})."
                )
            selected = extraction.file_metadata(prediction_store_manager.get_file_metadata(file_id))
            # Identity contract: the producer's FileMetadata `name`/`loa` written on upload
            # must equal the configured ensemble's model_name/loa. Verified against
            # pipeline-core's code but NOT a live upload (register C-25) — confirm at the
            # first real run. The guard fails loud (not silent) if the contract is off, so
            # a mismatch surfaces immediately rather than shipping the wrong file.
            expected = {"name": self.ensemble_path_manager.model_name, "loa": loa}
            logger.info("Selected forecast file identity: %s (expected %s).", selected, expected)
            identity.assert_forecast_identity(selected, expected)

            self._forecast_dataframe = pd.read_parquet(io.BytesIO(prediction_store_manager.download_prediction(file_id).to_dict().get("data", {}).get("file_bytes", None)))

            self._forecast_dataset = PGMDataset(self._forecast_dataframe)
        except Exception as e:
            logger.error(
                f"Encountered an error while trying to download the latest forecast data for level {loa} from Datastore: {e}",
                exc_info=True,
            )
            raise

    def _read(self) -> any:
        self._read_historical_data()
        self._read_forecast_data()

    def _append_metadata(self, dataset: PGMDataset) -> pd.DataFrame:
        filter_cols = [dataset._time_id, dataset._entity_id, *METADATA_COLS]
        raw_result = self._enricher.enrich_dataframe_with_pg_info(
            dataset.dataframe.reset_index(),
            pg_id_col=dataset._entity_id,
            time_id_col=dataset._time_id,
            only_metadata=True,
        )
        
        raw_result = raw_result[filter_cols].set_index([dataset._time_id, dataset._entity_id])
        return dataset.dataframe.join(raw_result)

    def _transform(
        self,
    ) -> list:
        self._historical_dataframe = self._append_metadata(self._historical_dataset)
        if self.configs.get("wire_contract"):
            # Contract mode: the forecast is frames, not a dataframe; geography ships
            # as the §5 sidecar (built at _save), never joined into the payload.
            return
        self._forecast_dataframe = self._append_metadata(self._forecast_dataset)

    def _validate(self) -> pd.DataFrame:
        _necessary_metadata_cols = METADATA_COLS

        for col in _necessary_metadata_cols:
            if col not in self._historical_dataframe.columns:
                err_msg = f"Historical dataframe is missing required metadata column: {col}. Found columns: {self._historical_dataframe.columns.tolist()}"
                logger.error(err_msg)
                raise ValueError(err_msg)
            null_count = self._historical_dataframe[col].isnull().sum()
            if null_count > 0:
                err_msg = f"Historical dataframe has {null_count} null values in required metadata column: {col} ({null_count}/{len(self._historical_dataframe)} rows)."
                logger.error(err_msg)
                raise ValueError(err_msg)
        logger.info("Historical dataframe metadata validation passed.")

        if self.configs.get("wire_contract"):
            # Contract mode: forecast-side null-gating is replaced by the wire's own
            # verified chain (hashes + header/payload asserts at read; §6 gate + gid
            # parity at _save). Coverage still applies, via the frame seam.
            self._check_coverage()
            return

        for col in _necessary_metadata_cols:
            if col not in self._forecast_dataframe.columns:
                err_msg = f"Forecast dataframe is missing required metadata column: {col}. Found columns: {self._forecast_dataframe.columns.tolist()}"
                logger.error(err_msg)
                raise ValueError(err_msg)
            null_count = self._forecast_dataframe[col].isnull().sum()
            if null_count > 0:
                err_msg = f"Forecast dataframe has {null_count} null values in required metadata column: {col} ({null_count}/{len(self._forecast_dataframe)} rows)."
                logger.error(err_msg)
                raise ValueError(err_msg)
        logger.info("Forecast dataframe metadata validation passed.")

        self._check_coverage()

    def _clip_observed_history(self) -> None:
        """Drop fabricated (unobserved) months from the historical delivery (S2/C-26).

        The historical request runs to the current calendar month, but UCDP data ends
        earlier (reporting lag) at datafactory's ``last_valid_month_id``; the tail months
        are zero-padding, not observed zeros, and would ship to FAO as "zero conflict".

        The boundary is read straight from the **producer** (views-datafactory) via
        ``source_metadata`` — never pipeline-core. Only the *historical* (observed) frame
        is clipped; the forecast frame is future-dated by design and untouched.

        Degrade-open policy: if the boundary cannot be resolved — the store predates the
        attribute (``None``) or the producer read fails (network) — the clip is skipped
        with a WARNING rather than blocking delivery. Both unresolved cases are treated
        identically so a transient datafactory hiccup does not crash the historical read.
        """
        try:
            lv = source_metadata.last_valid_month_id(self.configs.get("zarr_url"))
        except Exception as e:  # producer unreachable — degrade open, like lv is None
            logger.warning(
                "last_valid_month_id could not be read from datafactory (%s); the "
                "historical delivery was NOT clipped to observed range (C-26 guard "
                "skipped).",
                e,
            )
            return
        if lv is None:
            logger.warning(
                "last_valid_month_id unavailable from datafactory; the historical "
                "delivery was NOT clipped to observed range (C-26 guard skipped)."
            )
            return
        fabricated = observed_range.fabricated_months(
            extraction.months_of(self._historical_dataframe), lv
        )
        if len(fabricated):
            logger.warning(
                "Clipping %d fabricated (unobserved) month(s) > last_valid_month_id=%d "
                "from the historical delivery: %s",
                len(fabricated),
                lv,
                fabricated.tolist(),
            )
            self._historical_dataframe = extraction.drop_months_above(
                self._historical_dataframe, lv
            )

    def _check_coverage(self) -> None:
        """Log delivered cell counts and enforce the region coverage contract (S1/C-34).

        Orchestration only: extract primitives via ``extraction`` (the pandas seam),
        then call the representation-free ``delivery.coverage`` invariant — the rule is
        *called*, not embedded. The count-gate fires only for regions pinned in
        ``coverage.EXPECTED_CELLS``; an unpinned/unresolved region logs a skipped gate
        rather than guessing.
        """
        region = self.configs.get("region")
        expected = coverage.expected_for(region)
        excluded = coverage.excluded_for(region)
        if self.configs.get("wire_contract"):
            # Forecast cells come from the frame seam; targets share one cell set
            # (enforced again at the sink, §4.2). Historical stays the pandas seam.
            first_frame = next(iter(self._forecast_run.values()))[0]
            sources = [
                ("historical", extraction.cells_of(self._historical_dataframe), len(self._historical_dataframe)),
                ("forecast", frame_extraction.cells_of(first_frame), first_frame.n_rows),
            ]
        else:
            sources = [
                ("historical", extraction.cells_of(self._historical_dataframe), len(self._historical_dataframe)),
                ("forecast", extraction.cells_of(self._forecast_dataframe), len(self._forecast_dataframe)),
            ]
        for label, cells, n_rows in sources:
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
        import pyarrow.parquet as pq

        upload_enabled = bool(self.configs.get("wire_upload_enabled", product.UPLOAD_ENABLED))
        store = _ContractStorePort(self._unfao_datastore()) if upload_enabled else None
        return wire_sink.deliver_run(
            self._forecast_run,
            lookup=pq.read_table(_DEFAULT_LOOKUP),
            staging_dir=Path(self._model_path.data_generated) / "wire_contract",
            store=store,
            upload_enabled=upload_enabled,
        )

    def _unfao_datastore(self) -> DatastoreModule:
        """The FAO-facing store (`unfao_bucket`)."""
        return DatastoreModule(appwrite_file_manager_config=self._unfao_appwrite_config())

    def _unfao_appwrite_config(self) -> AppwriteConfig:
        return AppwriteConfig(
            path_manager=self._model_path,
            endpoint=os.getenv("APPWRITE_ENDPOINT"),
            project_id=os.getenv("APPWRITE_DATASTORE_PROJECT_ID"),
            credentials=os.getenv("APPWRITE_DATASTORE_API_KEY"),
            auth_method="api_key",
            cache_ttl_hours=24,
            bucket_id=os.getenv("APPWRITE_UNFAO_BUCKET_ID"),
            bucket_name=os.getenv("APPWRITE_UNFAO_BUCKET_NAME"),
            collection_id=os.getenv("APPWRITE_UNFAO_COLLECTION_ID"),
            collection_name=os.getenv("APPWRITE_UNFAO_COLLECTION_NAME"),
            database_id=os.getenv("APPWRITE_METADATA_DATABASE_ID"),
            database_name=os.getenv("APPWRITE_METADATA_DATABASE_NAME"),
        )

    def _save(self) -> list:
        # Explicit declared mode (ADR-013; never inferred).
        if self.configs.get("wire_contract"):
            return self._save_contract()

        if self._historical_dataset is None or self._forecast_dataset is None:
            err_msg = "Datasets could not be initialized properly."
            logger.error(err_msg)
            raise ValueError(err_msg)

        unfao_appwrite_config = AppwriteConfig(
            path_manager=self._model_path,
            endpoint=os.getenv("APPWRITE_ENDPOINT"),
            project_id=os.getenv("APPWRITE_DATASTORE_PROJECT_ID"),
            credentials=os.getenv("APPWRITE_DATASTORE_API_KEY"),
            auth_method="api_key",
            cache_ttl_hours=24,
            bucket_id=os.getenv("APPWRITE_UNFAO_BUCKET_ID"),
            bucket_name=os.getenv("APPWRITE_UNFAO_BUCKET_NAME"),
            collection_id=os.getenv("APPWRITE_UNFAO_COLLECTION_ID"),
            collection_name=os.getenv("APPWRITE_UNFAO_COLLECTION_NAME"),
            database_id=os.getenv("APPWRITE_METADATA_DATABASE_ID"),
            database_name=os.getenv("APPWRITE_METADATA_DATABASE_NAME"),
        )
        dsm = DatastoreModule(appwrite_file_manager_config=unfao_appwrite_config)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        historical_file_path = self._model_path.data_generated / f"historical_dataset_{timestamp}.parquet"
        forecast_file_path = self._model_path.data_generated / f"forecast_dataset_{timestamp}.parquet"

        self._historical_dataframe.to_parquet(
            historical_file_path
        )
        dsm.upload_data(file=historical_file_path,
                       filename=Path(historical_file_path).name,
                       name=self._model_path.model_name,
                       loa="pgm",
                       type="model", targets=self.configs.get("targets", []),
                       description=self._delivery_description(self._historical_dataframe, timestamp),
                       category="historical")

        self._forecast_dataframe.to_parquet(
            forecast_file_path
        )
        dsm.upload_data(file=forecast_file_path,
                       filename=Path(forecast_file_path).name,
                       name=self.ensemble_path_manager.model_name,
                       loa="pgm",
                       type="model", targets=["pred_ln_sb_best", "pred_ln_ns_best", "pred_ln_os_best", "pred_ln_sb_prob", "pred_ln_ns_prob", "pred_ln_os_prob"],
                       description=self._delivery_description(self._forecast_dataframe, timestamp),
                       category="forecast")

    def _delivery_description(self, df: pd.DataFrame, timestamp: str) -> str:
        """Human prefix + structured provenance (S5/C-15) for an upload's metadata.

        Sources every provenance field from the actual delivery — the enricher's lookup
        version, the configured region, the S1 coverage counts, the post-enrich unmapped
        count — and serializes the representation-free ``delivery.provenance`` dict into
        the only structured carrier ``upload_data`` exposes today (the ``description``
        free-text field; a dedicated metadata field is requested upstream, C-15).
        """
        region = self.configs.get("region")
        prov = provenance.build_provenance(
            lookup_version=self._enricher.lookup_version,
            region=region,
            expected_cell_count=coverage.expected_for(region),
            actual_cell_count=len(extraction.cells_of(df)),
            unmapped_count=extraction.unmapped_cell_count(df, METADATA_COLS),
        )
        return (
            f"Enriched with geographic metadata on {timestamp} using precomputed GAUL "
            f"lookup (ADR-011, version={self._enricher.lookup_version}). "
            f"provenance={json.dumps(prov, separators=(',', ':'))}"
        )
