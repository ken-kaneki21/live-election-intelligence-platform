import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


PARTY_REFRESH_SECONDS = 300          # 5 minutes
CANDIDATE_REBUILD_SECONDS = 1800     # 30 minutes

PROJECT_ROOT = Path(__file__).resolve().parent

PARTY_SCRIPT = PROJECT_ROOT / "eci_party_auto_ingest.py"
CANDIDATE_SCRIPT = PROJECT_ROOT / "eci_candidate_auto_ingest_v2.py"

PARTY_OUTPUT = PROJECT_ROOT / "data" / "processed" / "latest_results.csv"
CANDIDATE_OUTPUT = PROJECT_ROOT / "data" / "processed" / "latest_candidate_results.csv"
CANDIDATE_COVERAGE_OUTPUT = PROJECT_ROOT / "data" / "processed" / "candidate_coverage_report.csv"
TAMIL_NADU_CANDIDATE_OUTPUT = PROJECT_ROOT / "data" / "processed" / "candidates_tamil_nadu.csv"

FILES_TO_UPLOAD = [
    {
        "local_path": PARTY_OUTPUT,
        "blob_path": "processed/latest_results.csv",
        "label": "Party-level processed dataset",
    },
    {
        "local_path": CANDIDATE_OUTPUT,
        "blob_path": "processed/latest_candidate_results.csv",
        "label": "Candidate-level processed dataset",
    },
    {
        "local_path": CANDIDATE_COVERAGE_OUTPUT,
        "blob_path": "processed/candidate_coverage_report.csv",
        "label": "Candidate coverage report",
    },
    {
        "local_path": TAMIL_NADU_CANDIDATE_OUTPUT,
        "blob_path": "processed/candidates_tamil_nadu.csv",
        "label": "Tamil Nadu candidate dataset",
    },
]


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_environment():
    load_dotenv(PROJECT_ROOT / ".env")


def run_command(command, label):
    print("\n" + "=" * 80)
    print(f"[{timestamp()}] Starting: {label}")
    print("=" * 80)
    print("Command:", " ".join(command))

    try:
        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.stdout:
            print("\nSTDOUT:")
            print(result.stdout)

        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)

        if result.returncode == 0:
            print(f"[{timestamp()}] Completed successfully: {label}")
            return True

        print(f"[{timestamp()}] Failed: {label}")
        print(f"Return code: {result.returncode}")
        return False

    except Exception as error:
        print(f"[{timestamp()}] Exception while running {label}: {error}")
        return False


def run_party_ingestion():
    if not PARTY_SCRIPT.exists():
        print(f"Party script not found: {PARTY_SCRIPT}")
        return False

    return run_command(
        [sys.executable, str(PARTY_SCRIPT)],
        "Party-level election trend ingestion",
    )


def rebuild_candidate_dataset():
    if not CANDIDATE_SCRIPT.exists():
        print(f"Candidate scraper v2 not found: {CANDIDATE_SCRIPT}")
        return False

    return run_command(
        [sys.executable, str(CANDIDATE_SCRIPT), "--rebuild-only"],
        "Candidate dataset rebuild from partial raw data",
    )


def run_candidate_manual_visible():
    if not CANDIDATE_SCRIPT.exists():
        print(f"Candidate scraper v2 not found: {CANDIDATE_SCRIPT}")
        return False

    return run_command(
        [sys.executable, str(CANDIDATE_SCRIPT), "--visible"],
        "Candidate-level visible browser scraping",
    )


def get_azure_client():
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "election-data")

    if not connection_string:
        print("Azure upload skipped: AZURE_STORAGE_CONNECTION_STRING is missing.")
        return None, None

    try:
        from azure.storage.blob import BlobServiceClient
    except ImportError:
        print("Azure upload skipped: azure-storage-blob is not installed.")
        print("Install it using: pip install azure-storage-blob")
        return None, None

    try:
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(container_name)

        try:
            container_client.create_container()
            print(f"Azure container created: {container_name}")
        except Exception:
            pass

        return container_client, container_name

    except Exception as error:
        print(f"Azure client creation failed: {error}")
        return None, None


def upload_file_to_azure(container_client, local_path, blob_path, label):
    if not local_path.exists():
        print(f"Azure upload skipped for {label}: file missing -> {local_path}")
        return False

    try:
        blob_client = container_client.get_blob_client(blob_path)

        with open(local_path, "rb") as file:
            blob_client.upload_blob(file, overwrite=True)

        print(f"Azure upload successful: {label} -> {blob_path}")
        return True

    except Exception as error:
        print(f"Azure upload failed for {label}: {error}")
        return False


def upload_processed_outputs_to_azure():
    print("\n" + "=" * 80)
    print(f"[{timestamp()}] Starting: Azure processed file upload")
    print("=" * 80)

    container_client, container_name = get_azure_client()

    if container_client is None:
        print("Azure upload not completed.")
        return False

    upload_results = []

    for item in FILES_TO_UPLOAD:
        result = upload_file_to_azure(
            container_client=container_client,
            local_path=item["local_path"],
            blob_path=item["blob_path"],
            label=item["label"],
        )
        upload_results.append(result)

    successful_uploads = sum(upload_results)
    total_uploads = len(upload_results)

    print(f"\nAzure container: {container_name}")
    print(f"Azure upload summary: {successful_uploads}/{total_uploads} files uploaded.")

    return successful_uploads > 0


def print_file_status():
    print("\nCurrent output files:")

    output_files = [
        ("Party output", PARTY_OUTPUT),
        ("Candidate output", CANDIDATE_OUTPUT),
        ("Candidate coverage output", CANDIDATE_COVERAGE_OUTPUT),
        ("Tamil Nadu candidate output", TAMIL_NADU_CANDIDATE_OUTPUT),
    ]

    for label, file_path in output_files:
        if file_path.exists():
            print(f"{label} exists: {file_path}")
            print(f"{label} modified: {datetime.fromtimestamp(file_path.stat().st_mtime)}")
        else:
            print(f"{label} missing: {file_path}")


def run_loop(run_candidate_rebuild=True, upload_to_azure=True):
    print("Master Scheduler started.")
    print(f"Party refresh interval: {PARTY_REFRESH_SECONDS} seconds")
    print(f"Candidate rebuild interval: {CANDIDATE_REBUILD_SECONDS} seconds")
    print("Candidate full scraping is intentionally manual/batch, not automatic every 5 minutes.")
    print("Azure upload enabled." if upload_to_azure else "Azure upload disabled.")
    print_file_status()

    last_party_run = 0
    last_candidate_rebuild = 0

    while True:
        current_time = time.time()
        changed = False

        if current_time - last_party_run >= PARTY_REFRESH_SECONDS:
            party_success = run_party_ingestion()
            last_party_run = current_time
            changed = changed or party_success
            print_file_status()

        if run_candidate_rebuild and current_time - last_candidate_rebuild >= CANDIDATE_REBUILD_SECONDS:
            candidate_success = rebuild_candidate_dataset()
            last_candidate_rebuild = current_time
            changed = changed or candidate_success
            print_file_status()

        if upload_to_azure and changed:
            upload_processed_outputs_to_azure()

        print(f"\n[{timestamp()}] Sleeping for 30 seconds...")
        time.sleep(30)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Master scheduler for Election Intelligence Platform."
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="Run party ingestion once and candidate rebuild once, upload outputs, then exit.",
    )

    parser.add_argument(
        "--party-only",
        action="store_true",
        help="Only run party-level ingestion.",
    )

    parser.add_argument(
        "--candidate-rebuild-only",
        action="store_true",
        help="Only rebuild final candidate dataset from partial raw data.",
    )

    parser.add_argument(
        "--candidate-scrape-visible",
        action="store_true",
        help="Run candidate scraper in visible browser mode manually.",
    )

    parser.add_argument(
        "--upload-only",
        action="store_true",
        help="Only upload existing processed files to Azure Blob Storage.",
    )

    parser.add_argument(
        "--no-azure-upload",
        action="store_true",
        help="Disable Azure upload after scheduler refresh.",
    )

    parser.add_argument(
        "--no-candidate-rebuild-loop",
        action="store_true",
        help="Disable periodic candidate rebuild inside continuous scheduler loop.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    load_environment()
    args = parse_args()

    upload_to_azure = not args.no_azure_upload

    if args.upload_only:
        upload_processed_outputs_to_azure()
        sys.exit(0)

    if args.party_only:
        success = run_party_ingestion()
        print_file_status()

        if upload_to_azure and success:
            upload_processed_outputs_to_azure()

        sys.exit(0)

    if args.candidate_rebuild_only:
        success = rebuild_candidate_dataset()
        print_file_status()

        if upload_to_azure and success:
            upload_processed_outputs_to_azure()

        sys.exit(0)

    if args.candidate_scrape_visible:
        success = run_candidate_manual_visible()
        print_file_status()

        if upload_to_azure and success:
            upload_processed_outputs_to_azure()

        sys.exit(0)

    if args.once:
        party_success = run_party_ingestion()
        candidate_success = rebuild_candidate_dataset()
        print_file_status()

        if upload_to_azure and (party_success or candidate_success):
            upload_processed_outputs_to_azure()

        sys.exit(0)

    run_loop(
        run_candidate_rebuild=not args.no_candidate_rebuild_loop,
        upload_to_azure=upload_to_azure,
    )