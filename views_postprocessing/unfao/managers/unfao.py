from views_pipeline_core.managers.postprocessor.postprocessor import (
    PostprocessorManager,
    PostprocessorPathManager,
)
from views_pipeline_core.files.utils import read_dataframe
from views_pipeline_core.configs.pipeline import PipelineConfig
import logging
from views_pipeline_core.data.handlers import PGMDataset

from views_pipeline_core.modules.appwrite.file import AppwriteConfig
from views_pipeline_core.modules.datastore import DatastoreModule
from views_pipeline_core.managers.model import ForecastingModelManager

from views_pipeline_core.managers.ensemble import EnsembleManager, EnsemblePathManager
import polars as pl
import pandas as pd
import io
from argparse import Namespace
from datetime import datetime
import os
from dotenv import load_dotenv
from views_postprocessing.unfao.mapping.mapping import get_default_mapper
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
        self._mapper = get_default_mapper()
        self.ensemble_path_manager = None

    def _read_historical_data(self):
        # Historical Data
        path_raw = self._model_path.data_raw  # Path to raw data
        path_artifacts = self._model_path.artifacts  # Path to save model artifacts
        run_type = "forecasting"  # e.g., "calibration", "validation", "forecasting"
        
        self._data_loader.get_data(
                use_saved=False,
                validate=False,
                self_test=False,
                partition=run_type
            )
        current_month = datetime.now().strftime("%Y-%m")
        artifact_name = f"{run_type}_viewser_df_{current_month}"
        self._historical_dataframe = read_dataframe(
            path_raw / f"{run_type}_viewser_df{PipelineConfig.dataframe_format}"
        )  # Dataframe obtained from viewser
        partitioner_dict = (
            self._data_loader.partition_dict
        )  # Partition dict from ViewsDataLoader
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
        
        # appwrite_config = AppwriteConfig(
        #     path_manager=self.ensemble_path_manager,
        #     endpoint=os.getenv("APPWRITE_ENDPOINT"),
        #     project_id=os.getenv("APPWRITE_DATASTORE_PROJECT_ID"),
        #     credentials=os.getenv("APPWRITE_DATASTORE_API_KEY"),
        #     auth_method="api_key",
        #     cache_ttl_hours=24,
        #     bucket_id=os.getenv("APPWRITE_UNFAO_BUCKET_ID"),
        #     bucket_name=os.getenv("APPWRITE_UNFAO_BUCKET_NAME"),
        #     collection_name=os.getenv("APPWRITE_UNFAO_COLLECTION_NAME"),
        #     collection_id=os.getenv("APPWRITE_UNFAO_COLLECTION_ID"),
        #     database_id=os.getenv("APPWRITE_DATABASE_ID"),
        #     database_name=os.getenv("APPWRITE_DATABASE_NAME"),
        # )
        # appwrite_config = AppwriteConfig(
        #     path_manager=self._model_path,
        #     endpoint=os.getenv("APPWRITE_ENDPOINT"),
        #     project_id=os.getenv("APPWRITE_DATASTORE_PROJECT_ID"),
        #     credentials=os.getenv("APPWRITE_DATASTORE_API_KEY"),
        #     auth_method="api_key",
        #     cache_ttl_hours=24,
        #     bucket_id=os.getenv("APPWRITE_UNFAO_FORECASTS_BUCKET_ID"),
        #     bucket_name=os.getenv("APPWRITE_UNFAO_FORECASTS_BUCKET_NAME"),
        #     collection_id=os.getenv("APPWRITE_UNFAO_COLLECTION_ID"),
        #     collection_name=os.getenv("APPWRITE_UNFAO_COLLECTION_NAME"),
        #     database_id=os.getenv("APPWRITE_METADATA_DATABASE_ID"),
        #     database_name=os.getenv("APPWRITE_METADATA_DATABASE_NAME"),
        # )

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
        filter_cols = [
            dataset._time_id,
            dataset._entity_id,
            "pg_xcoord",
            "pg_ycoord",
            "country_iso_a3",
            "admin1_gaul1_code",
            "admin1_gaul1_name",
            "admin1_gaul0_code",
            "admin1_gaul0_name",
            "admin2_gaul2_code",
            "admin2_gaul2_name",
        ]
        raw_result = self._mapper.enrich_dataframe_with_pg_info(
            dataset.dataframe.reset_index(),
            pg_id_col=dataset._entity_id,
            time_id_col=dataset._time_id,
            only_metadata=True,
            batch_size=1000
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
        _necessary_metadata_cols = ["pg_xcoord",
            "pg_ycoord",
            "country_iso_a3",
            "admin1_gaul1_code",
            "admin1_gaul1_name",
            "admin1_gaul0_code",
            "admin1_gaul0_name",
            "admin2_gaul2_code",
            "admin2_gaul2_name"]
        
        for col in _necessary_metadata_cols:
            if col in self._historical_dataframe.columns:
            #     if self._historical_dataframe[col].isnull().any():
            #         raise ValueError(f"Historical dataframe is missing values in required metadata column: {col}. Found {self._historical_dataframe[col].isnull().sum()} null values.")
                continue
            else:
                raise ValueError(f"Historical dataframe is missing required metadata column: {col}. Found columns: {self._historical_dataframe.columns.tolist()}")
        logger.info("Historical dataframe metadata validation passed.")
        
        for col in _necessary_metadata_cols:
            if col in self._forecast_dataframe.columns:
            #     if self._forecast_dataframe[col].isnull().any():
            #         raise ValueError(f"Forecast dataframe is missing values in required metadata column: {col}. Found {self._forecast_dataframe[col].isnull().sum()} null values.")
                continue
            else:
                raise ValueError(f"Forecast dataframe is missing required metadata column: {col}. Found columns: {self._forecast_dataframe.columns.tolist()}")
        logger.info("Forecast dataframe metadata validation passed.")

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
        historical_file_path = self._model_path.data_generated / f"historical_dataset_{timestamp}.parquet"
        forecast_file_path = self._model_path.data_generated / f"forecast_dataset_{timestamp}.parquet"

        self._historical_dataframe.to_parquet(
            historical_file_path
        )
        dsm.upload_predictions(file=historical_file_path, 
                       filename=Path(historical_file_path).name, 
                       name=self._model_path.model_name,
                       loa="pgm",
                       type="model", targets=self.configs.get("targets", []),
                       description="This is a test DataFrame.", category="historical")

        self._forecast_dataframe.to_parquet(
            forecast_file_path
        )
        dsm.upload_predictions(file=forecast_file_path, 
                       filename=Path(forecast_file_path).name,
                       name=self.ensemble_path_manager.model_name,
                       loa="pgm",
                       type="model", targets=["pred_ln_sb_best", "pred_ln_ns_best", "pred_ln_os_best", "pred_ln_sb_prob", "pred_ln_ns_prob", "pred_ln_os_prob"], 
                       description="This is a test DataFrame.", category="forecast")