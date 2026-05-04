import os
import time
from datetime import datetime
from io import StringIO

import pandas as pd
from playwright.sync_api import sync_playwright


BASE_URL = "https://results.eci.gov.in/ResultAcGenMay2026"

STATE_PAGES = {
    "Assam": "partywiseresult-S03.htm",
    "Kerala": "partywiseresult-S11.htm",
    "Tamil Nadu": "partywiseresult-S22.htm",
    "West Bengal": "partywiseresult-S25.htm",
    "Puducherry": "partywiseresult-U07.htm",
}

RAW_OUTPUT = "data/raw/eci_party_latest_raw.csv"
PROCESSED_OUTPUT = "data/processed/latest_results.csv"

os.makedirs("data/raw", exist_ok=True)
os.makedirs("data/processed", exist_ok=True)


def normalize_party_code(party_full: str) -> str:
    """
    Converts:
    Bharatiya Janata Party - BJP -> BJP
    Communist Party of India (Marxist) - CPI(M) -> CPI(M)
    """
    party_full = str(party_full).strip()

    if " - " in party_full:
        return party_full.split(" - ")[-1].strip()

    return party_full


def extract_party_table_from_html(html: str, state: str, source_url: str) -> pd.DataFrame:
    """
    Extracts party-wise result table from ECI HTML.
    Expected table columns:
    Party, Won, Leading, Total
    """
    try:
        tables = pd.read_html(StringIO(html))
    except Exception as e:
        raise ValueError(f"Could not parse HTML tables for {state}: {e}")

    print(f"{state}: tables found = {len(tables)}")

    selected_table = None

    for i, table in enumerate(tables):
        table.columns = [str(col).strip() for col in table.columns]
        lower_cols = [col.lower() for col in table.columns]

        print(f"{state}: table {i} columns = {table.columns.tolist()}")

        has_party = any("party" in col for col in lower_cols)
        has_won = any("won" in col for col in lower_cols)
        has_leading = any("leading" in col for col in lower_cols)
        has_total = any("total" in col for col in lower_cols)

        if has_party and has_won and has_leading and has_total:
            selected_table = table.copy()
            break

    if selected_table is None:
        raise ValueError(f"No valid party-wise table found for {state}")

    rename_map = {}

    for col in selected_table.columns:
        col_lower = col.lower()

        if "party" in col_lower:
            rename_map[col] = "party_full"
        elif "won" in col_lower:
            rename_map[col] = "won"
        elif "leading" in col_lower:
            rename_map[col] = "leading"
        elif "total" in col_lower:
            rename_map[col] = "total"

    df = selected_table.rename(columns=rename_map)

    required_cols = ["party_full", "won", "leading", "total"]
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        raise ValueError(
            f"{state}: missing columns {missing_cols}. Found columns: {df.columns.tolist()}"
        )

    df = df[required_cols].copy()

    df = df[~df["party_full"].astype(str).str.lower().str.strip().eq("total")]

    df["won"] = pd.to_numeric(df["won"], errors="coerce").fillna(0).astype(int)
    df["leading"] = pd.to_numeric(df["leading"], errors="coerce").fillna(0).astype(int)
    df["total"] = pd.to_numeric(df["total"], errors="coerce").fillna(0).astype(int)

    df = df[df["total"] > 0]

    df["state"] = state
    df["party_full"] = df["party_full"].astype(str).str.strip()
    df["party"] = df["party_full"].apply(normalize_party_code)
    df["source_url"] = source_url
    df["scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return df[
        [
            "state",
            "party",
            "party_full",
            "won",
            "leading",
            "total",
            "source_url",
            "scraped_at",
        ]
    ]


def scrape_state_page(page, state: str, page_file: str) -> pd.DataFrame:
    url = f"{BASE_URL}/{page_file}"
    print(f"\nOpening {state}: {url}")

    page.goto(url, wait_until="networkidle", timeout=60000)
    time.sleep(2)

    title = page.title()
    print(f"{state}: page title = {title}")

    html = page.content()

    debug_path = f"data/raw/debug_{state.replace(' ', '_').lower()}.html"

    with open(debug_path, "w", encoding="utf-8") as f:
        f.write(html)

    if "Access Denied" in html or "Access Denied" in title:
        raise RuntimeError(f"{state}: Access Denied page received")

    return extract_party_table_from_html(html, state, url)


def convert_party_summary_to_dashboard_rows(party_df: pd.DataFrame) -> pd.DataFrame:
    """
    Converts party-wise totals into the dashboard schema.

    Existing dashboard expects:
    state,constituency,candidate,party,votes,status,margin,last_updated

    For party-wise trend data:
    - constituency = state-level party trend row
    - candidate = party full name
    - votes = total seat trend count
    - margin = leading count for now
    """
    rows = []

    for _, row in party_df.iterrows():
        state = row["state"]
        party = row["party"]
        party_full = row["party_full"]
        won = int(row["won"])
        leading = int(row["leading"])
        total = int(row["total"])
        scraped_at = row["scraped_at"]

        if won > 0 and leading == 0:
            status = "Won"
        elif leading > 0:
            status = "Leading"
        else:
            status = "Reported"

        rows.append(
            {
                "state": state,
                "constituency": f"{state} Party Trend",
                "candidate": party_full,
                "party": party,
                "votes": total,
                "status": status,
                "margin": leading,
                "last_updated": scraped_at,
            }
        )

    return pd.DataFrame(rows)


def run_once() -> pd.DataFrame:
    all_state_dfs = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
            ],
        )

        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )

        page = context.new_page()

        for state, page_file in STATE_PAGES.items():
            try:
                state_df = scrape_state_page(page, state, page_file)
                all_state_dfs.append(state_df)
                print(f"{state}: success, rows = {len(state_df)}")

            except Exception as e:
                print(f"{state}: failed -> {e}")

            time.sleep(2)

        browser.close()

    if not all_state_dfs:
        raise RuntimeError("No state data scraped. All sources failed.")

    party_df = pd.concat(all_state_dfs, ignore_index=True)

    party_df.to_csv(RAW_OUTPUT, index=False)

    dashboard_df = convert_party_summary_to_dashboard_rows(party_df)
    dashboard_df.to_csv(PROCESSED_OUTPUT, index=False)

    print("\nSaved outputs:")
    print(f"Raw party file: {RAW_OUTPUT}")
    print(f"Dashboard file: {PROCESSED_OUTPUT}")
    print(f"Rows written to dashboard file: {len(dashboard_df)}")

    return dashboard_df


if __name__ == "__main__":
    run_once()