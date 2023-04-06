import json
from io import BytesIO
from typing import Any, Dict, List, Type, TypeVar

import attr

from ..types import File

T = TypeVar("T", bound="BodyUploadDataset")


@attr.s(auto_attribs=True)
class BodyUploadDataset:
    """
    Attributes:
        dataset_files (List[File]): application/json
    """

    dataset_files: List[File]
    additional_properties: Dict[str, Any] = attr.ib(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        dataset_files = []
        for dataset_files_item_data in self.dataset_files:
            dataset_files_item = dataset_files_item_data.to_tuple()

            dataset_files.append(dataset_files_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "dataset_files": dataset_files,
            }
        )

        return field_dict

    def to_multipart(self) -> Dict[str, Any]:
        _temp_dataset_files = []
        for dataset_files_item_data in self.dataset_files:
            dataset_files_item = dataset_files_item_data.to_tuple()

            _temp_dataset_files.append(dataset_files_item)
        dataset_files = (None, json.dumps(_temp_dataset_files).encode(), "application/json")

        field_dict: Dict[str, Any] = {}
        field_dict.update(
            {key: (None, str(value).encode(), "text/plain") for key, value in self.additional_properties.items()}
        )
        field_dict.update(
            {
                "dataset_files": dataset_files,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        dataset_files = []
        _dataset_files = d.pop("dataset_files")
        for dataset_files_item_data in _dataset_files:
            dataset_files_item = File(payload=BytesIO(dataset_files_item_data))

            dataset_files.append(dataset_files_item)

        body_upload_dataset = cls(
            dataset_files=dataset_files,
        )

        body_upload_dataset.additional_properties = d
        return body_upload_dataset

    @property
    def additional_keys(self) -> List[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
