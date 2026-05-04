import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient, ContentSettings


load_dotenv()


AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "").strip()
AZURE_BLOB_CONTAINER = os.getenv("AZURE_BLOB_CONTAINER", "election-data").strip()


FILES_TO_UPLOAD = [
    {
        "local_path": "data/processed/latest_results.csv",
        "blob_name": "processed/latest_results.csv",
    },
    {
        "local_path": "data/processed/latest_candidate_results.csv",
        "blob_name": "processed/latest_candidate_results.csv",
    },
    {
        "local_path": "data/processed/candidate_coverage_report.csv",
        "blob_name": "processed/candidate_coverage_report.csv",
    },
    {
        "local_path": "data/processed/candidates_tamil_nadu.csv",
        "blob_name": "processed/candidates_tamil_nadu.csv",
    },
]


def validate_azure_config():
    if not AZURE_STORAGE_CONNECTION_STRING:
        raise RuntimeError(
            "AZURE_STORAGE_CONNECTION_STRING is missing. Add it in your .env file."
        )

    if not AZURE_BLOB_CONTAINER:
        raise RuntimeError(
            "AZURE_BLOB_CONTAINER is missing. Add it in your .env file."
        )


def get_blob_service_client():
    validate_azure_config()
    return BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)


def ensure_container_exists(blob_service_client):
    container_client = blob_service_client.get_container_client(AZURE_BLOB_CONTAINER)

    try:
        container_client.get_container_properties()
        print(f"Azure container exists: {AZURE_BLOB_CONTAINER}")
    except Exception:
        print(f"Azure container not found. Creating: {AZURE_BLOB_CONTAINER}")
        container_client.create_container()

    return container_client


def upload_file(container_client, local_path, blob_name):
    path = Path(local_path)

    if not path.exists():
        print(f"Skipped missing file: {local_path}")
        return {
            "local_path": local_path,
            "blob_name": blob_name,
            "status": "missing",
            "size_bytes": 0,
        }

    size_bytes = path.stat().st_size

    with open(path, "rb") as file:
        container_client.upload_blob(
            name=blob_name,
            data=file,
            overwrite=True,
            content_settings=ContentSettings(content_type="text/csv"),
        )

    print(f"Uploaded: {local_path} -> {blob_name} ({size_bytes} bytes)")

    return {
        "local_path": local_path,
        "blob_name": blob_name,
        "status": "uploaded",
        "size_bytes": size_bytes,
    }


def upload_processed_files():
    print("\n" + "=" * 80)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Azure upload started")
    print("=" * 80)

    blob_service_client = get_blob_service_client()
    container_client = ensure_container_exists(blob_service_client)

    results = []

    for item in FILES_TO_UPLOAD:
        result = upload_file(
            container_client=container_client,
            local_path=item["local_path"],
            blob_name=item["blob_name"],
        )
        results.append(result)

    uploaded_count = sum(1 for item in results if item["status"] == "uploaded")
    missing_count = sum(1 for item in results if item["status"] == "missing")

    print("\nAzure upload summary:")
    print(f"Uploaded files: {uploaded_count}")
    print(f"Missing files: {missing_count}")
    print(f"Container: {AZURE_BLOB_CONTAINER}")

    print("=" * 80)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Azure upload completed")
    print("=" * 80)

    return results


if __name__ == "__main__":
    upload_processed_files()