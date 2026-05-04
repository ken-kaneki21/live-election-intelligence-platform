import os
from io import BytesIO, StringIO

import pandas as pd
from dotenv import load_dotenv

load_dotenv()


LOCAL_PARTY_RESULTS = "data/processed/latest_results.csv"
LOCAL_CANDIDATE_RESULTS = "data/processed/latest_candidate_results.csv"
LOCAL_CANDIDATE_COVERAGE = "data/processed/candidate_coverage_report.csv"

DEFAULT_PARTY_BLOB = "processed/latest_results.csv"
DEFAULT_CANDIDATE_BLOB = "processed/latest_candidate_results.csv"
DEFAULT_COVERAGE_BLOB = "processed/candidate_coverage_report.csv"


REQUIRED_PARTY_COLUMNS = [
    "state",
    "constituency",
    "candidate",
    "party",
    "votes",
    "status",
    "margin",
    "last_updated",
]

REQUIRED_CANDIDATE_COLUMNS = [
    "state",
    "state_code",
    "constituency",
    "constituency_no",
    "candidate",
    "party",
    "votes",
    "status",
    "margin",
    "scraped_at",
]

REQUIRED_COVERAGE_COLUMNS = [
    "state_code",
    "state_name",
    "discovered_constituencies",
    "candidate_rows",
    "candidate_constituencies",
    "candidate_pipeline_status",
]


def _azure_enabled() -> bool:
    return bool(
        os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        and os.getenv("AZURE_STORAGE_CONTAINER_NAME")
    )


def _read_csv_from_azure(blob_name: str) -> pd.DataFrame:
    try:
        from azure.storage.blob import BlobServiceClient
    except Exception as exc:
        raise RuntimeError(
            "azure-storage-blob is not installed. Run: pip install azure-storage-blob"
        ) from exc

    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME")

    if not connection_string or not container_name:
        raise RuntimeError("Azure storage environment variables are missing.")

    service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = service_client.get_blob_client(container=container_name, blob=blob_name)
    payload = blob_client.download_blob().readall()

    return pd.read_csv(BytesIO(payload))


def _read_csv_with_fallback(local_path: str, blob_name: str) -> pd.DataFrame:
    if _azure_enabled():
        try:
            return _read_csv_from_azure(blob_name)
        except Exception:
            # Local fallback keeps the dashboard usable on Streamlit Cloud/local machines
            # when Azure credentials are absent, expired, or the blob is temporarily unavailable.
            pass

    if os.path.exists(local_path):
        return pd.read_csv(local_path)

    return pd.DataFrame()


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    df.columns = [str(col).strip().lower() for col in df.columns]
    return df


def _ensure_columns(df: pd.DataFrame, required_columns: list[str]) -> pd.DataFrame:
    df = _normalise_columns(df)

    for col in required_columns:
        if col not in df.columns:
            if col in [
                "votes",
                "margin",
                "won",
                "leading",
                "total",
                "constituency_no",
                "candidate_rows",
                "candidate_constituencies",
                "discovered_constituencies",
            ]:
                df[col] = 0
            elif col == "state":
                df[col] = "Tamil Nadu"
            elif col == "state_code":
                df[col] = "S22"
            elif col == "status":
                df[col] = "Unknown"
            else:
                df[col] = ""

    return df


def _coerce_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    return df


def _coerce_text(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    for col in columns:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

    return df


def load_party_results() -> pd.DataFrame:
    blob_name = os.getenv("AZURE_PARTY_RESULTS_BLOB", DEFAULT_PARTY_BLOB)
    df = _read_csv_with_fallback(LOCAL_PARTY_RESULTS, blob_name)
    df = _ensure_columns(df, REQUIRED_PARTY_COLUMNS)
    df = _coerce_numeric(df, ["votes", "margin", "won", "leading", "total"])
    df = _coerce_text(df, ["state", "constituency", "candidate", "party", "status", "last_updated"])
    return df


def load_candidate_results() -> pd.DataFrame:
    blob_name = os.getenv("AZURE_CANDIDATE_RESULTS_BLOB", DEFAULT_CANDIDATE_BLOB)
    df = _read_csv_with_fallback(LOCAL_CANDIDATE_RESULTS, blob_name)
    df = _ensure_columns(df, REQUIRED_CANDIDATE_COLUMNS)
    df = _coerce_numeric(df, ["votes", "margin", "constituency_no", "vote_rank", "vote_margin", "runner_up_votes"])
    df = _coerce_text(df, ["state", "state_code", "constituency", "candidate", "party", "status", "scraped_at"])
    return df


def load_candidate_coverage_report() -> pd.DataFrame:
    blob_name = os.getenv("AZURE_CANDIDATE_COVERAGE_BLOB", DEFAULT_COVERAGE_BLOB)
    df = _read_csv_with_fallback(LOCAL_CANDIDATE_COVERAGE, blob_name)
    df = _ensure_columns(df, REQUIRED_COVERAGE_COLUMNS)
    df = _coerce_numeric(df, ["discovered_constituencies", "candidate_rows", "candidate_constituencies"])
    df = _coerce_text(df, ["state_code", "state_name", "candidate_pipeline_status"])
    return df
