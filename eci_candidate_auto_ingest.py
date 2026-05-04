import os
import re
import time
from datetime import datetime

import pandas as pd
from playwright.sync_api import sync_playwright


BASE_URL = "https://results.eci.gov.in/ResultAcGenMay2026"
HOME_URL = BASE_URL

RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"

RAW_OUTPUT = os.path.join(RAW_DIR, "candidate_results_raw.csv")
PROCESSED_OUTPUT = os.path.join(PROCESSED_DIR, "latest_candidate_results.csv")

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)


def clean_text(value):
    if pd.isna(value):
        return ""
    value = str(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def parse_constituency_text(text):
    """
    Example:
    ALANDUR - 28
    """
    text = clean_text(text)

    match = re.search(r"(.+?)\s*-\s*(\d+)$", text)

    if match:
        return clean_text(match.group(1)), int(match.group(2))

    return text, None


def discover_constituencies(page):
    """
    Extracts constituency dropdown options directly from rendered page.
    ECI values look like S2228, S22182, etc.
    """

    page.wait_for_load_state("networkidle", timeout=60000)
    page.wait_for_timeout(4000)

    options = page.locator("select option")
    count = options.count()

    constituencies = []

    print(f"Dropdown options found on page: {count}")

    for i in range(count):
        text = clean_text(options.nth(i).inner_text())
        value = clean_text(options.nth(i).get_attribute("value"))

        if not text or not value:
            continue

        if "select constituency" in text.lower():
            continue

        if not value.startswith("S22"):
            continue

        constituency_name, constituency_no = parse_constituency_text(text)

        constituencies.append(
            {
                "constituency": constituency_name,
                "constituency_no": constituency_no,
                "eci_code": value,
                "candidate_url": f"{BASE_URL}/Constituencywise{value}.htm",
            }
        )

    return constituencies


def parse_candidate_table(html, constituency, constituency_no, eci_code, url):
    try:
        tables = pd.read_html(html)
    except Exception:
        return pd.DataFrame()

    if not tables:
        return pd.DataFrame()

    best_table = None

    for table in tables:
        table = table.copy()
        table.columns = [clean_text(c) for c in table.columns]
        joined_cols = " ".join([c.lower() for c in table.columns])

        if (
            "candidate" in joined_cols
            or "party" in joined_cols
            or "evm votes" in joined_cols
            or "postal votes" in joined_cols
            or "total votes" in joined_cols
            or "status" in joined_cols
        ):
            best_table = table
            break

    if best_table is None:
        best_table = tables[0].copy()
        best_table.columns = [clean_text(c) for c in best_table.columns]

    rename_map = {}

    for col in best_table.columns:
        c = clean_text(col).lower()

        if "candidate" in c:
            rename_map[col] = "candidate"
        elif c == "party" or "party" in c:
            rename_map[col] = "party"
        elif "total votes" in c:
            rename_map[col] = "votes"
        elif c == "total" or "total" in c:
            rename_map[col] = "votes"
        elif "status" in c:
            rename_map[col] = "status"
        elif "margin" in c:
            rename_map[col] = "margin"

    best_table = best_table.rename(columns=rename_map)

    for required_col in ["candidate", "party", "votes", "status"]:
        if required_col not in best_table.columns:
            best_table[required_col] = ""

    best_table["candidate"] = best_table["candidate"].apply(clean_text)
    best_table["party"] = best_table["party"].apply(clean_text)
    best_table["status"] = best_table["status"].apply(clean_text)

    best_table["votes"] = (
        best_table["votes"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.extract(r"(\d+)", expand=False)
        .fillna("0")
        .astype(int)
    )

    if "margin" not in best_table.columns:
        best_table["margin"] = 0
    else:
        best_table["margin"] = (
            best_table["margin"]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.extract(r"(\d+)", expand=False)
            .fillna("0")
            .astype(int)
        )

    best_table["constituency"] = constituency
    best_table["constituency_no"] = constituency_no
    best_table["eci_code"] = eci_code
    best_table["source_url"] = url
    best_table["scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    final_cols = [
        "constituency",
        "constituency_no",
        "candidate",
        "party",
        "votes",
        "status",
        "margin",
        "eci_code",
        "source_url",
        "scraped_at",
    ]

    best_table = best_table[final_cols]

    best_table = best_table[
        best_table["candidate"].ne("")
        | best_table["party"].ne("")
        | best_table["votes"].gt(0)
    ]

    best_table = best_table.drop_duplicates()

    return best_table


def run_once(max_constituencies=None, headless=True):
    all_rows = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1440, "height": 1000},
        )

        page = context.new_page()

        print(f"Opening home page: {HOME_URL}")
        page.goto(HOME_URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(4000)

        print("Page title:", page.title())

        constituencies = discover_constituencies(page)

        print(f"Constituencies discovered: {len(constituencies)}")

        if not constituencies:
            debug_html_path = os.path.join(RAW_DIR, "candidate_discovery_debug.html")
            with open(debug_html_path, "w", encoding="utf-8") as f:
                f.write(page.content())

            browser.close()

            raise RuntimeError(
                f"No constituency dropdown options discovered. Debug HTML saved at: {debug_html_path}"
            )

        if max_constituencies:
            constituencies = constituencies[:max_constituencies]

        for i, item in enumerate(constituencies, start=1):
            constituency = item["constituency"]
            constituency_no = item["constituency_no"]
            eci_code = item["eci_code"]
            url = item["candidate_url"]

            print(f"\n[{i}/{len(constituencies)}] Opening {constituency} ({eci_code})")
            print(url)

            candidate_page = context.new_page()

            try:
                candidate_page.goto(url, wait_until="networkidle", timeout=60000)
                candidate_page.wait_for_timeout(3500)

                title = candidate_page.title()
                html = candidate_page.content()

                print("Title:", title)

                if "Access Denied" in title or "Access Denied" in html:
                    print(f"Access denied: {constituency}")
                    candidate_page.close()
                    continue

                df = parse_candidate_table(
                    html=html,
                    constituency=constituency,
                    constituency_no=constituency_no,
                    eci_code=eci_code,
                    url=url,
                )

                if df.empty:
                    print(f"No candidate table found: {constituency}")
                else:
                    print(f"Rows scraped: {len(df)}")
                    all_rows.append(df)

            except Exception as e:
                print(f"Failed: {constituency} | {e}")

            finally:
                candidate_page.close()

        browser.close()

    if not all_rows:
        raise RuntimeError(
            "No candidate-level data scraped. Candidate page URL pattern may still need adjustment."
        )

    final_df = pd.concat(all_rows, ignore_index=True)

    final_df = final_df.drop_duplicates(
        subset=["constituency", "candidate", "party"],
        keep="last",
    )

    # Remove non-candidate summary rows like "Total"
    final_df["candidate"] = final_df["candidate"].astype(str).str.strip()
    final_df["party"] = final_df["party"].astype(str).str.strip()

    final_df = final_df[
        ~final_df["candidate"].str.lower().isin(["total", "nan", ""])
    ].copy()

    final_df = final_df[
        ~final_df["party"].str.lower().isin(["nan", ""])
    ].copy()

    # Ensure votes are numeric
    final_df["votes"] = (
        pd.to_numeric(final_df["votes"], errors="coerce")
        .fillna(0)
        .astype(int)
    )

    # Rank candidates inside each constituency by votes
    final_df["vote_rank"] = (
        final_df.groupby("constituency")["votes"]
        .rank(method="first", ascending=False)
        .astype(int)
    )

    # Calculate runner-up votes and margin for the top candidate
    second_votes = (
        final_df[final_df["vote_rank"] == 2][["constituency", "votes"]]
        .rename(columns={"votes": "runner_up_votes"})
    )

    final_df = final_df.merge(second_votes, on="constituency", how="left")
    final_df["runner_up_votes"] = final_df["runner_up_votes"].fillna(0).astype(int)

    final_df["vote_margin"] = final_df["votes"] - final_df["runner_up_votes"]
    final_df.loc[final_df["vote_rank"] != 1, "vote_margin"] = 0

    # Derive status because parsed ECI table does not expose status
    final_df["derived_status"] = final_df["vote_rank"].apply(
        lambda x: "Leading / Top Candidate"
        if x == 1
        else ("Runner-up" if x == 2 else "Trailing")
    )

    final_df["is_leading"] = final_df["vote_rank"] == 1

    # Do not call this final winner unless ECI status exists
    final_df["is_winner_like"] = final_df["vote_rank"] == 1

    # Reorder columns
    final_df = final_df[
        [
            "constituency",
            "constituency_no",
            "candidate",
            "party",
            "votes",
            "vote_rank",
            "derived_status",
            "vote_margin",
            "runner_up_votes",
            "eci_code",
            "source_url",
            "scraped_at",
        ]
    ]

    final_df.to_csv(RAW_OUTPUT, index=False)
    final_df.to_csv(PROCESSED_OUTPUT, index=False)

    print("\nSaved outputs:")
    print(f"Raw candidate file: {RAW_OUTPUT}")
    print(f"Processed candidate file: {PROCESSED_OUTPUT}")
    print(f"Rows written: {len(final_df)}")

    return final_df


if __name__ == "__main__":
    run_once(max_constituencies=None, headless=False)