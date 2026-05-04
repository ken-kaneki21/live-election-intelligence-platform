import os
import re
from datetime import datetime

import pandas as pd

from state_config import STATE_CONFIG, get_all_configured_states, get_state_name, get_state_slug


RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"

DISCOVERY_FILE = os.path.join(RAW_DIR, "eci_state_constituency_discovery.csv")
CANDIDATE_FILE = os.path.join(PROCESSED_DIR, "latest_candidate_results.csv")

COVERAGE_REPORT_FILE = os.path.join(PROCESSED_DIR, "candidate_coverage_report.csv")
MERGED_CANDIDATE_FILE = os.path.join(PROCESSED_DIR, "latest_candidate_results.csv")

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)


def now_string():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def clean_text(value):
    if pd.isna(value):
        return ""
    value = str(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def load_csv(path):
    if not os.path.exists(path):
        return pd.DataFrame()

    try:
        return pd.read_csv(path)
    except Exception as error:
        print(f"Failed to load {path}: {error}")
        return pd.DataFrame()


def save_csv(df, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)


def extract_state_code_from_eci_code(eci_code):
    eci_code = clean_text(eci_code)

    match = re.match(r"([SU]\d{2})", eci_code)

    if match:
        return match.group(1)

    return ""


def build_coverage_report(discovery_df, candidate_df):
    configured_states = pd.DataFrame(get_all_configured_states())

    if discovery_df.empty:
        discovered_summary = pd.DataFrame(
            columns=["state_code", "discovered_constituencies"]
        )
    else:
        discovered_summary = (
            discovery_df.groupby("state_code", as_index=False)
            .agg(discovered_constituencies=("eci_code", "nunique"))
        )

    if candidate_df.empty:
        candidate_summary = pd.DataFrame(
            columns=[
                "state_code",
                "candidate_rows",
                "candidate_constituencies",
                "candidate_parties",
            ]
        )
    else:
        candidate_summary = (
            candidate_df.groupby("state_code", as_index=False)
            .agg(
                candidate_rows=("candidate", "count"),
                candidate_constituencies=("constituency", "nunique"),
                candidate_parties=("party", "nunique"),
            )
        )

    report = configured_states.merge(
        discovered_summary,
        on="state_code",
        how="left",
    )

    report = report.merge(
        candidate_summary,
        on="state_code",
        how="left",
    )

    report["discovered_constituencies"] = (
        report["discovered_constituencies"].fillna(0).astype(int)
    )
    report["candidate_rows"] = report["candidate_rows"].fillna(0).astype(int)
    report["candidate_constituencies"] = (
        report["candidate_constituencies"].fillna(0).astype(int)
    )
    report["candidate_parties"] = report["candidate_parties"].fillna(0).astype(int)

    def determine_status(row):
        if row["candidate_rows"] > 0:
            return "candidate_data_available"

        if row["discovered_constituencies"] > 0:
            return "candidate_pages_discovered_no_data_loaded"

        return "candidate_pages_not_discovered"

    report["candidate_pipeline_status"] = report.apply(determine_status, axis=1)

    report["notes"] = report.apply(
        lambda row: (
            "Candidate-level constituency data is available and included in dashboard."
            if row["candidate_pipeline_status"] == "candidate_data_available"
            else (
                "Constituency pages were discovered, but no candidate data has been loaded yet."
                if row["candidate_pipeline_status"] == "candidate_pages_discovered_no_data_loaded"
                else "Candidate-level constituency pages are not exposed by the active ECI result path."
            )
        ),
        axis=1,
    )

    report["updated_at"] = now_string()

    return report


def add_state_metadata(candidate_df):
    if candidate_df.empty:
        return candidate_df

    df = candidate_df.copy()

    if "eci_code" not in df.columns:
        df["eci_code"] = ""

    df["state_code"] = df["eci_code"].apply(extract_state_code_from_eci_code)
    df["state"] = df["state_code"].apply(get_state_name)
    df["state_slug"] = df["state_code"].apply(get_state_slug)

    return df


def save_statewise_candidate_files(candidate_df):
    if candidate_df.empty:
        print("No candidate data available for state-wise output.")
        return []

    saved_files = []

    for state_code in sorted(candidate_df["state_code"].dropna().unique()):
        state_df = candidate_df[candidate_df["state_code"] == state_code].copy()

        if state_df.empty:
            continue

        state_slug = get_state_slug(state_code)
        output_file = os.path.join(PROCESSED_DIR, f"candidates_{state_slug}.csv")

        save_csv(state_df, output_file)

        saved_files.append(
            {
                "state_code": state_code,
                "state": get_state_name(state_code),
                "output_file": output_file,
                "rows": len(state_df),
                "constituencies": state_df["constituency"].nunique()
                if "constituency" in state_df.columns
                else 0,
                "parties": state_df["party"].nunique()
                if "party" in state_df.columns
                else 0,
            }
        )

    return saved_files


def run_master_ingest():
    print("Candidate Master Ingest started.")
    print("This script does not fake all-state candidate scraping.")
    print("It only processes states whose constituency pages are discovered and whose data is available.")

    discovery_df = load_csv(DISCOVERY_FILE)
    candidate_df = load_csv(CANDIDATE_FILE)

    print(f"\nDiscovery file: {DISCOVERY_FILE}")
    print(f"Discovery rows: {len(discovery_df)}")

    print(f"\nCandidate file: {CANDIDATE_FILE}")
    print(f"Candidate rows before metadata: {len(candidate_df)}")

    candidate_df = add_state_metadata(candidate_df)

    if not candidate_df.empty:
        save_csv(candidate_df, MERGED_CANDIDATE_FILE)

    saved_files = save_statewise_candidate_files(candidate_df)

    coverage_report = build_coverage_report(discovery_df, candidate_df)
    save_csv(coverage_report, COVERAGE_REPORT_FILE)

    print("\nState-wise candidate files saved:")

    if saved_files:
        for item in saved_files:
            print(
                f"{item['state']} ({item['state_code']}): "
                f"{item['rows']} rows, "
                f"{item['constituencies']} constituencies, "
                f"{item['parties']} parties -> {item['output_file']}"
            )
    else:
        print("No state-wise candidate files saved.")

    print("\nCoverage report saved:")
    print(COVERAGE_REPORT_FILE)

    print("\nCoverage summary:")
    print(
        coverage_report[
            [
                "state_code",
                "state_name",
                "discovered_constituencies",
                "candidate_rows",
                "candidate_constituencies",
                "candidate_pipeline_status",
            ]
        ].to_string(index=False)
    )

    print("\nFinal merged candidate file:")
    print(MERGED_CANDIDATE_FILE)

    print("\nCandidate Master Ingest completed.")

    return coverage_report


if __name__ == "__main__":
    run_master_ingest()