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
from datetime import datetime
import os
from dotenv import load_dotenv
from views_postprocessing.unfao.enrichment import GaulLookupEnricher
from views_postprocessing.unfao.gaul_schema import METADATA_COLS
from views_postprocessing.unfao import extraction, source_metadata
from views_postprocessing.delivery import coverage, observed_range
from pathlib import Path

logger = logging.getLogger(__name__)


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

    def _read_forecast_data(self):
        # Forecast Data
        ensemble_name = self.configs.get("ensemble", None)
        if not ensemble_name:
            raise ValueError("Ensemble name must be provided in configs with the `ensemble` key for forecasting. Cannot proceed.")
        
        self.ensemble_path_manager = EnsemblePathManager(ensemble_name_or_path=ensemble_name, validate=False)
        # ensemble_configs = EnsembleManager(
        #     ensemble_path=self.ensemble_path_manager,
        # ).configs

        # loa = ensemble_configs.get("level", None)
        loa = "pgm"
        if not loa:
            raise ValueError("level must be defined in the ensemble configurations (e.g, pgm, cm). Cannot proceed.")
        
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

        try:
            prediction_store_manager = DatastoreModule(appwrite_file_manager_config=appwrite_config)
            self._forecast_dataframe = pd.read_parquet(io.BytesIO(prediction_store_manager.download_latest_file(filters={"category": "forecast"}).to_dict().get("data", {}).get("file_bytes", None)))

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
        

    # def _append_lat_lon(self):
    #     self._historical_dataframe = self._historical_dataframe.join(self._historical_dataset.get_lat_lon())
    #     self._forecast_dataframe = self._forecast_dataframe.join(self._forecast_dataset.get_lat_lon())

    # def _append_isoa3(self):
    #     self._historical_dataframe = self._historical_dataframe.join(self._historical_dataset.get_isoab())
    #     self._forecast_dataframe = self._forecast_dataframe.join(self._forecast_dataset.get_isoab())

    # def _append_name(self):
    #     self._historical_dataframe = self._historical_dataframe.join(self._historical_dataset.get_name())
    #     self._forecast_dataframe = self._forecast_dataframe.join(self._forecast_dataset.get_name())

    def _transform(
        self,
    ) -> list:
        # self._append_m49()
        # self._append_lat_lon()
        # self._append_isoa3()
        # self._append_name()
        self._historical_dataframe = self._append_metadata(self._historical_dataset)
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
        """
        lv = source_metadata.last_valid_month_id(self.configs.get("zarr_url"))
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
        for label, df in (
            ("historical", self._historical_dataframe),
            ("forecast", self._forecast_dataframe),
        ):
            cells = extraction.cells_of(df)
            logger.info(
                "%s delivery coverage: %d distinct cells, %d rows.",
                label,
                len(cells),
                len(df),
            )
            if expected is not None:
                coverage.assert_complete_coverage(cells, expected, label=label)
            else:
                logger.warning(
                    "Coverage count-gate skipped for %s: region %r is not pinned in "
                    "delivery.coverage.EXPECTED_CELLS — verify and pin before relying on it.",
                    label,
                    region,
                )

    def _save(self) -> list:
        if self._historical_dataset is None or self._forecast_dataset is None:
            raise ValueError("Datasets could not be initialized properly.")
        
        # self._historical_dataset.dataframe.to_parquet(
        #     self._model_path.data_generated / "historical_dataset.parquet"
        # )
        # self._forecast_dataset.dataframe.to_parquet(
        #     self._model_path.data_generated / "forecast_dataset.parquet"
        # )

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
        enrichment_description = f"Enriched with geographic metadata on {timestamp} using precomputed GAUL lookup (ADR-011, version={self._enricher.lookup_version})."
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
                       description=enrichment_description, category="historical")

        self._forecast_dataframe.to_parquet(
            forecast_file_path
        )
        dsm.upload_data(file=forecast_file_path,
                       filename=Path(forecast_file_path).name,
                       name=self.ensemble_path_manager.model_name,
                       loa="pgm",
                       type="model", targets=["pred_ln_sb_best", "pred_ln_ns_best", "pred_ln_os_best", "pred_ln_sb_prob", "pred_ln_ns_prob", "pred_ln_os_prob"],
                       description=enrichment_description, category="forecast")
