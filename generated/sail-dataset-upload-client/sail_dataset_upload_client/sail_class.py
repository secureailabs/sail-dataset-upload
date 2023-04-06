from typing import Any, Union

from api.default import upload_dataset
from client import AuthenticatedClient
from models.body_upload_dataset import BodyUploadDataset
from models.http_validation_error import HTTPValidationError


class SyncApis:
    def __init__(self, client: AuthenticatedClient) -> None:
        self._client = client

    def upload_dataset(
        self,
        multipart_data: BodyUploadDataset,
        dataset_version_id: str,
    ) -> Union[Any, HTTPValidationError]:
        response = upload_dataset.sync(
            client=self._client,
            multipart_data=multipart_data,
            dataset_version_id=dataset_version_id,
        )
        if response is None:
            raise Exception("No response")

        return response
