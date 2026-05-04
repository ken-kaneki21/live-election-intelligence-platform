import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient, ContentSettings


load_dotenv()

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "").strip()
AZURE_CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME", "election-data").strip()

FILES_TO_UPLOAD = [
    {
        "local_path": "data/processed/latest_results.csv",
        "blob_name": "processed/latest_results.csv",
        "content_type": "text/csv",
    },
    {
        "local_path": "data/processed/latest_candidate_results.csv",
        "blob_name": "processed/latest_candidate_results.csv",
        "content_type": "text/csv",
    },
    {
        "local_path": "data/processed/candidate_coverage_report.csv",
        "blob_name": "processed/candidate_coverage_report.csv",
        "content_type": "text/csv",
    },
    {
        "local_path": "data/processed/candidates_tamil_nadu.csv",
        "blob_name": "processed/candidates_tamil_nadu.csv",
        "content_type": "text/csv",
    },
]


def validate_config():
    if not AZURE_STORAGE_CONNECTION_STRING:
        raise RuntimeError(
            "AZURE_STORAGE_CONNECTION_STRING is missing. Add it in your .env file."
        )

    if not AZURE_CONTAINER_NAME:
        raise RuntimeError(
            "AZURE_CONTAINER_NAME is missing. Add it in your .env file."
        )


def get_blob_service_client():
    validate_config()
    return BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)


def ensure_container(blob_service_client):
    container_client = blob_service_client.get_container_client(AZURE_CONTAINER_NAME)

    try:
        container_client.get_container_properties()
    except Exception:
        container_client.create_container()

    return container_client


def upload_file(container_client, local_path, blob_name, content_type):
    path = Path(local_path)

    if not path.exists():
        print(f"Skipped missing file: {local_path}")
        return False

    blob_client = container_client.get_blob_client(blob_name)

    with open(path, "rb") as file:
        blob_client.upload_blob(
            file,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )

    print(f"Uploaded: {local_path} -> {blob_name}")
    return True


def upload_processed_outputs():
    blob_service_client = get_blob_service_client()
    container_client = ensure_container(blob_service_client)

    uploaded_count = 0

    for item in FILES_TO_UPLOAD:
        uploaded = upload_file(
            container_client=container_client,
            local_path=item["local_path"],
            blob_name=item["blob_name"],
            content_type=item["content_type"],
        )

        if uploaded:
            uploaded_count += 1

    metadata_text = (
        f"last_uploaded_at,{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"files_uploaded,{uploaded_count}\n"
    )

    container_client.get_blob_client("processed/upload_metadata.csv").upload_blob(
        metadata_text,
        overwrite=True,
        content_settings=ContentSettings(content_type="text/csv"),
    )

    print("\nAzure Blob sync completed.")
    print(f"Container: {AZURE_CONTAINER_NAME}")
    print(f"Files uploaded: {uploaded_count}")


if __name__ == "__main__":
    upload_processed_outputs()