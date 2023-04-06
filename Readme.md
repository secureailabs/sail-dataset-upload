# SAIL API Services Portal

## Api Writing Guidelines
- Endpoint decorator should be defined in the format '@api.route('/<resource_name>/<id>/<sub_resource>/<id>.../?query_params')'
- Endpoint decorator should at least contain description, response_description, operation_id, response_model, status_code
- APIs should return same type of objects for every success response, the response codes can be different though
- Endpoint decorator should contain response_model if the response is a json object
- If there are path parameters, they should have a description in the function definition
- If there are query parameters, they should have a description in the function definition


Example of a good endpoint decorator:
```python
@router.get(
    path="/data-federations",
    description="Get list of all the data federations",
    response_description="List of data federations",
    response_model=GetMultipleDataFederation_Out,
    response_model_by_alias=False,
    response_model_exclude_unset=True,
    status_code=status.HTTP_200_OK,
    operation_id="get_all_data_federations",
)
async def get_all_data_federations(
    data_submitter_id: Optional[PyObjectId] = Query(default=None, description="UUID of Data Submitter in the data federation"),
    researcher_id: Optional[PyObjectId] = Query(default=None, description="UUID of Researcher in the data federation"),
    dataset_id: Optional[PyObjectId] = Query(default=None, description="UUID of Dataset in the data federation"),
    current_user: TokenData = Depends(get_current_user),
) -> GetMultipleDataFederation_Out:
```

## Generators
<TBD>

### API documentation
The api is automatically generated from the openapi spec which can be found on http(s)://<hostname>:8000/docs
The static generated redoc html documentatation html file is also available in docs/index.html which can be viewed in a browser.

### Client SDK

#### Typescript client
<TBD>

#### Python client
```
pip install git+https://github.com/secureailabs/openapi-python-client.git
```
This will install the openapi-python-client package in your virtual environment. You can now use the package to generate a python client for the api using the generator script in `make generate_client`.
Make sure to activate the virtual environment before running the generator script and update the IP address in the script to point to the api server.

## Deployment
Build the docker image using:
`make build_image`

Push the docker image to the docker registry using:
`make push_image`
Note: export the following values before pushing:
```
export AZURE_SUBSCRIPTION_ID="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export AZURE_TENANT_ID="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export AZURE_CLIENT_ID="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export AZURE_CLIENT_SECRET="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export DOCKER_REGISTRY_NAME="developmentdockerregistry"
```
