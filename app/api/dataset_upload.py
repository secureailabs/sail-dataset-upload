# -------------------------------------------------------------------------------
# Engineering
# dataset_upload.py
# -------------------------------------------------------------------------------
"""APIs to encrypt and upload dataset to azure file share"""
# -------------------------------------------------------------------------------
# Copyright (C) 2022 Secure Ai Labs, Inc. All Rights Reserved.
# Private and Confidential. Internal Use Only.
#     This software contains proprietary information which shall not
#     be reproduced or transferred to other documents and shall not
#     be disclosed to others for any purpose without
#     prior written permission of Secure Ai Labs, Inc.
# -------------------------------------------------------------------------------

import base64
import json
import os
import shutil
from typing import List
from zipfile import ZipFile

from azure.storage.fileshare import ShareFileClient
from Crypto.Cipher import AES
from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, Response, UploadFile, status
from fastapi.security import OAuth2PasswordBearer
from sail_client import AuthenticatedClient
from sail_client.api.default import (
    get_all_data_federations,
    get_data_model_dataframe_info,
    get_data_model_info,
    get_data_model_series_info,
    get_dataset,
    get_dataset_key,
    get_dataset_version,
    get_dataset_version_connection_string,
    update_dataset_version,
)
from sail_client.models import (
    DatasetEncryptionKeyOut,
    DatasetVersionState,
    GetDataModelDataframeOut,
    GetDataModelOut,
    GetDataModelSeriesOut,
    GetDatasetOut,
    GetDatasetVersionConnectionStringOut,
    GetDatasetVersionOut,
    GetMultipleDataFederationOut,
    UpdateDatasetVersionIn,
)

from app.models.common import PyObjectId
from app.models.data_model import DataFrameDataModel, DataModel, SeriesDataModel

router = APIRouter()


def create_zip_from_files(zip_file, files):
    with ZipFile(zip_file, "w") as zipObj:
        for file in files:
            zipObj.write(file)


def encrypt_file_in_place(file, key, nonce):
    # Check the size of the key and nonce
    if len(key) != 32:
        raise Exception("The key must be 256 bits")
    if len(nonce) != 12:
        raise Exception("The nonce must be 96 bits")

    # Read the file into a byte array
    with open(file, "rb") as f:
        file_bytes = f.read()

    # Convert the key and nonce to bytes
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)

    # Encrypt the file
    ciphertext, tag = cipher.encrypt_and_digest(file_bytes)

    # Write the encrypted file back to disk
    with open(file, "wb") as f:
        f.write(ciphertext)

    return tag


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    return token


def get_secret(secret_name: str) -> str:
    """Get the secret value from the environment variable"""
    return os.environ[secret_name]


def encrypt_and_upload(
    current_user_token: str,
    dataset_version_id: PyObjectId,
    dataset_files: List[UploadFile],
):
    api_client = AuthenticatedClient(
        base_url=get_secret("SAIL_API_SERVICE_URL"),
        timeout=60,
        raise_on_unexpected_status=True,
        verify_ssl=False,
        token=current_user_token,
        follow_redirects=False,
    )

    # Create a working directory for this request
    random_id = base64.b64encode(os.urandom(12)).decode("utf-8")
    working_dir = os.path.join(os.getcwd(), f"./tmp/{str(dataset_version_id)}-{random_id}")

    try:
        os.makedirs(working_dir, exist_ok=True)

        # Copy the files to the working directory
        local_files = []
        for dataset_file in dataset_files:
            shutil.copyfileobj(dataset_file.file, open(f"{working_dir}/{dataset_file.filename}", "wb"))
            local_files.append(f"{working_dir}/{dataset_file.filename}")

        # Get the dataset version
        dataset_version = get_dataset_version.sync(client=api_client, dataset_version_id=str(dataset_version_id))
        assert type(dataset_version) == GetDatasetVersionOut

        # Upload only if the dataset version is in the NOT_UPLOAD state
        if dataset_version.state != DatasetVersionState.NOT_UPLOADED:
            raise Exception("Dataset version is not in NOT_UPLOAD state.")

        # Mark the dataset version as encrypting
        update_dataset_version.sync(
            client=api_client,
            dataset_version_id=str(dataset_version_id),
            json_body=UpdateDatasetVersionIn(state=DatasetVersionState.ENCRYPTING),
        )

        # GetConnectionStringForDatasetVersion
        connection_string_req = get_dataset_version_connection_string.sync(
            client=api_client, dataset_version_id=str(dataset_version_id)
        )
        assert type(connection_string_req) == GetDatasetVersionConnectionStringOut
        connection_string = connection_string_req.connection_string

        # Get the dataset for the dataset version
        dataset_id = dataset_version.dataset_id
        dataset = get_dataset.sync(client=api_client, dataset_id=dataset_id)
        assert type(dataset) == GetDatasetOut

        # Get the data federation
        data_federation_list = get_all_data_federations.sync(client=api_client)
        assert type(data_federation_list) == GetMultipleDataFederationOut
        if not data_federation_list.data_federations:
            raise Exception("No data federation found for the dataset.")
        data_federation = data_federation_list.data_federations[0]  # type: ignore

        # GetEncryptionKeyForDataset
        encryption_key_response = get_dataset_key.sync(
            client=api_client, data_federation_id=str(data_federation.id), dataset_id=dataset_id
        )
        assert type(encryption_key_response) == DatasetEncryptionKeyOut
        encryption_key = encryption_key_response.dataset_key

        # Create a dataset header
        dataset_header = {}
        dataset_header["dataset_id"] = dataset_id
        dataset_header["dataset_name"] = dataset.name
        dataset_header["data_federation_id"] = data_federation.id
        dataset_header["data_federation_name"] = data_federation.name
        dataset_header["dataset_packaging_format"] = "csvv1"

        # Create a zip package with the data files
        data_content_zip_file = f"{working_dir}/data_content.zip"
        create_zip_from_files(data_content_zip_file, local_files)

        # Encrypt the data content zip file
        nonce = os.urandom(12)
        key = base64.b64decode(encryption_key)
        tag = encrypt_file_in_place(data_content_zip_file, key, nonce)

        # Create a file with name dataset_header.json
        dataset_header_file = f"{working_dir}/dataset_header.json"
        dataset_header["aes_tag"] = base64.b64encode(tag).decode("utf-8")
        dataset_header["aes_nonce"] = base64.b64encode(nonce).decode("utf-8")
        with open(dataset_header_file, "w") as f:
            f.write(json.dumps(dataset_header))

        # TODO: Get data model
        data_model_id = data_federation.data_model_id
        if type(data_model_id) != str:
            raise Exception("No data model found for the data federation.")

        data_model = get_data_model_info.sync(client=api_client, data_model_id=data_model_id)
        if type(data_model) != GetDataModelOut:
            raise Exception("Error parsing data model.")

        data_model_full = DataModel(
            type=data_model.name, tabular_dataset_data_model_id=data_model.id, list_data_frame_data_model=[]
        )
        for dataframe_id in data_model.data_model_dataframes:
            # Get the data model dataframe
            data_model_dataframe = get_data_model_dataframe_info.sync(
                client=api_client, data_model_dataframe_id=dataframe_id
            )
            if type(data_model_dataframe) != GetDataModelDataframeOut:
                raise Exception("Error parsing data model dataframe.")

            # Get the data model dataframe series
            data_model_dataframe_series = get_data_model_dataframe_info.sync(
                client=api_client, data_model_dataframe_id=dataframe_id
            )
            if type(data_model_dataframe_series) != GetDataModelDataframeOut:
                raise Exception("Error parsing data model dataframe.")

            # Create a dataframe
            dataframe = DataFrameDataModel(
                type=data_model_dataframe.name,
                data_frame_name=data_model_dataframe.name,
                data_frame_data_model_id=data_model_dataframe.id,
                list_series_data_model=[],
            )

            # Fetch all the series
            for series_id in data_model_dataframe.data_model_series:
                # Get the data model series
                data_model_series = get_data_model_series_info.sync(client=api_client, data_model_series_id=series_id)
                if type(data_model_series) != GetDataModelSeriesOut:
                    raise Exception("Error parsing data model series.")

                # Create a series
                series = SeriesDataModel(
                    type=data_model_series.series_schema.type,
                    series_name=data_model_series.name,
                    series_data_model_id=data_model_series.id,
                    list_value=data_model_series.series_schema.list_value
                    if type(data_model_series.series_schema.list_value) == List
                    else [],
                    unit=data_model_series.series_schema.unit
                    if type(data_model_series.series_schema.unit) == str
                    else None,
                    min=data_model_series.series_schema.min_
                    if type(data_model_series.series_schema.min_) == float
                    else None,
                    max=data_model_series.series_schema.max_
                    if type(data_model_series.series_schema.max_) == float
                    else None,
                    resolution=data_model_series.series_schema.resolution
                    if type(data_model_series.series_schema.resolution) == float
                    else None,
                )

                # Add the series to the dataframe
                dataframe.list_series_data_model.append(series)

            # Add the dataframe to the data model
            data_model_full.list_data_frame_data_model.append(dataframe)

        data_model_txt = data_model_full.json(exclude_unset=True)

        # Create a data_model zip file
        data_model_file = f"{working_dir}/data_model.json"
        data_model_zip_file = f"{working_dir}/data_model.zip"
        with open(data_model_file, "w") as f:
            f.write(data_model_txt)
        create_zip_from_files(data_model_zip_file, [f"{working_dir}/data_model.json"])

        # Create a zip file with the dataset header, data model and data content
        big_zip_files = [dataset_header_file, data_model_zip_file, data_content_zip_file]
        dataset_file = f"{working_dir}/dataset_{dataset_version_id}.zip"
        create_zip_from_files(dataset_file, big_zip_files)

        # Upload the zip file to the Azure File Share
        with open(dataset_file, "rb") as f:
            # Upload the files created tar file to Azure file share using the sas token
            file_client = ShareFileClient.from_file_url(file_url=connection_string)
            file_client.create_file(size=f.tell())
            file_client.upload_file(f)

        # Mark the dataset version as ready
        update_dataset_version.sync(
            client=api_client,
            dataset_version_id=str(dataset_version_id),
            json_body=UpdateDatasetVersionIn(state=DatasetVersionState.ACTIVE),
        )

        # Delete the working directory
        shutil.rmtree(working_dir)
    except Exception as e:
        # Mark the dataset version as failed
        update_dataset_version.sync(
            client=api_client,
            dataset_version_id=str(dataset_version_id),
            json_body=UpdateDatasetVersionIn(state=DatasetVersionState.ERROR),
        )
        # Delete the working directory
        shutil.rmtree(working_dir)
        raise e


@router.post(
    path="/upload-dataset",
    description="Upload new data to File Share",
    response_description="Dataset Id",
    response_model_by_alias=False,
    status_code=status.HTTP_201_CREATED,
    operation_id="upload_dataset",
)
async def upload_dataset(
    background_tasks: BackgroundTasks,
    dataset_files: List[UploadFile] = File(description="application/json"),
    dataset_version_id: PyObjectId = Query(description="Dataset Version Id"),
    current_user_token=Depends(get_current_user),
):
    background_tasks.add_task(encrypt_and_upload, current_user_token, dataset_version_id, dataset_files)
    return Response(status_code=status.HTTP_202_ACCEPTED)
