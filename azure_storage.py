
import os
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

# Load secret settings from .env
load_dotenv()

connection_string = os.getenv(
    "AZURE_STORAGE_CONNECTION_STRING"
)

container_name = "bizmind-uploads"


def get_blob_container():
    if not connection_string:
        raise ValueError(
            "Azure connection string not found in .env"
        )

    blob_service = BlobServiceClient.from_connection_string(
        connection_string
    )

    return blob_service.get_container_client(container_name)


def upload_to_azure(file, filename):
    container = get_blob_container()

    blob = container.get_blob_client(filename)

    blob.upload_blob(file, overwrite=True)

    return blob.url
if __name__ == "__main__":
    try:
        container = get_blob_container()

        print("Successfully connected to Azure Blob Storage!")
        print("Container:", container.container_name)

    except Exception as error:
        print("Azure connection failed:")
        print(error)