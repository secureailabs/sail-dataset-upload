from typing import List, Optional

from pydantic import BaseModel


class SeriesDataModel(BaseModel):
    type: str
    series_name: str
    series_data_model_id: str
    list_value: Optional[List[str]]
    unit: Optional[str] = None
    min: Optional[float] = None
    max: Optional[float] = None
    resolution: Optional[float] = None


class DataFrameDataModel(BaseModel):
    type: str
    data_frame_name: str
    data_frame_data_model_id: str
    list_series_data_model: List[SeriesDataModel]


class DataModel(BaseModel):
    type: str
    tabular_dataset_data_model_id: str
    list_data_frame_data_model: List[DataFrameDataModel]
