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
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from fastapi.security import OAuth2PasswordBearer
from sail_client import AuthenticatedClient, SyncAuthenticatedOperations
from sail_client.models import DatasetVersionState, UpdateDatasetVersionIn

from app.models.common import PyObjectId

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


@router.post(
    path="/upload-dataset",
    description="Upload new data to File Share",
    response_description="Dataset Id",
    response_model_by_alias=False,
    status_code=status.HTTP_201_CREATED,
    operation_id="upload_dataset",
)
async def upload_dataset(
    dataset_files: List[UploadFile] = File(description="application/json"),
    dataset_version_id: PyObjectId = Query(description="Dataset Version Id"),
    current_user_token=Depends(get_current_user),
):
    client = AuthenticatedClient(
        base_url="https://172.20.100.6:8000",
        timeout=60,
        raise_on_unexpected_status=True,
        verify_ssl=False,
        token=current_user_token,
    )
    api_client = SyncAuthenticatedOperations(client)

    # Create a working directory for this request
    random_id = base64.b64encode(os.urandom(12)).decode("utf-8")
    working_dir = os.path.join(os.getcwd(), f"./tmp/{dataset_version_id}-{random_id}")
    os.makedirs(working_dir, exist_ok=True)

    # Copy the files to the working directory
    local_files = []
    for dataset_file in dataset_files:
        shutil.copyfileobj(dataset_file.file, open(f"{working_dir}/{dataset_file.filename}", "wb"))
        local_files.append(f"{working_dir}/{dataset_file.filename}")

    # Get the dataset version
    dataset_version = api_client.get_dataset_version(str(dataset_version_id))

    # Upload only if the dataset version is in the NOT_UPLOAD state
    if dataset_version.state != DatasetVersionState.NOT_UPLOADED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Dataset version is not in NOT_UPLOAD state.")

    # Mark the dataset version as encrypting
    # await update_dataset_version(dataset_version_id, UpdateDatasetVersion_In(state=DatasetVersionState.ENCRYPTING), current_user)

    # GetConnectionStringForDatasetVersion
    connection_string = api_client.get_dataset_version_connection_string(str(dataset_version_id)).connection_string

    # Get the dataset for the dataset version
    dataset_id = dataset_version.dataset_id
    dataset = api_client.get_dataset(dataset_id)

    # Get the data federation
    data_federation_list = api_client.get_all_data_federations()
    if not data_federation_list.data_federations:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No data federation found for the dataset.")
    data_federation = data_federation_list.data_federations[0]  # type: ignore

    # GetEncryptionKeyForDataset
    encryption_key = api_client.get_dataset_key(str(data_federation.id), dataset_id=dataset_id).dataset_key

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

    # Get data model
    data_model = data_federation.data_model

    # Create a data_model zip file
    data_model_file = f"{working_dir}/data_model.json"
    data_model_zip_file = f"{working_dir}/data_model.zip"
    with open(data_model_file, "w") as f:
        f.write(str(data_model))
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
    api_client.update_dataset_version(str(dataset_version_id), UpdateDatasetVersionIn(state=DatasetVersionState.ACTIVE))

    # Delete the working directory
    shutil.rmtree(working_dir)

    return Response(status_code=200)
