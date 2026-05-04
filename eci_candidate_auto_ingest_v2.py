import argparse
import os
import re
from datetime import datetime
from io import StringIO

import pandas as pd
from playwright.sync_api import sync_playwright


BASE_URL = "https://results.eci.gov.in/ResultAcGenMay2026"
HOME_URL = BASE_URL

RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"

PARTIAL_RAW_OUTPUT = os.path.join(RAW_DIR, "candidate_results_partial_raw.csv")
FINAL_RAW_OUTPUT = os.path.join(RAW_DIR, "candidate_results_raw.csv")
FINAL_PROCESSED_OUTPUT = os.path.join(PROCESSED_DIR, "latest_candidate_results.csv")
SCRAPE_LOG_OUTPUT = os.path.join(RAW_DIR, "candidate_scrape_log.csv")
FAILED_LOG_OUTPUT = os.path.join(RAW_DIR, "candidate_failed_log.csv")
DISCOVERED_OUTPUT = os.path.join(RAW_DIR, "candidate_constituencies_discovered.csv")

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)


def clean_text(value):
    if pd.isna(value):
        return ""
    value = str(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def parse_constituency_text(text):
    text = clean_text(text)
    match = re.search(r"(.+?)\s*-\s*(\d+)$", text)

    if match:
        return clean_text(match.group(1)), int(match.group(2))

    return text, None


def now_string():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_existing_csv(path):
    if not os.path.exists(path):
        return pd.DataFrame()

    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def save_csv(df, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)


def append_rows_to_csv(new_df, path):
    if new_df.empty:
        return

    existing_df = load_existing_csv(path)

    if existing_df.empty:
        combined_df = new_df.copy()
    else:
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)

    combined_df = combined_df.drop_duplicates(
        subset=["constituency", "candidate", "party", "eci_code"],
        keep="last",
    )

    save_csv(combined_df, path)


def append_log_row(row, path):
    existing_df = load_existing_csv(path)
    new_df = pd.DataFrame([row])

    if existing_df.empty:
        combined_df = new_df
    else:
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)

    save_csv(combined_df, path)


def get_completed_eci_codes():
    log_df = load_existing_csv(SCRAPE_LOG_OUTPUT)

    if log_df.empty or "status" not in log_df.columns or "eci_code" not in log_df.columns:
        return set()

    success_df = log_df[log_df["status"].astype(str).str.lower() == "success"].copy()
    return set(success_df["eci_code"].astype(str).tolist())


def discover_constituencies(page):
    page.goto(HOME_URL, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(4000)

    title = page.title()
    print(f"Home page title: {title}")

    if "Access Denied" in title:
        raise RuntimeError("Access denied on ECI home page. Run with visible browser mode: --visible")

    options = page.locator("select option")
    count = options.count()

    print(f"Dropdown options found: {count}")

    constituencies = []

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
                "discovered_at": now_string(),
            }
        )

    discovered_df = pd.DataFrame(constituencies)
    save_csv(discovered_df, DISCOVERED_OUTPUT)

    print(f"Constituencies discovered: {len(discovered_df)}")
    print(f"Discovery file saved: {DISCOVERED_OUTPUT}")

    return constituencies


def parse_candidate_table(html, constituency, constituency_no, eci_code, url):
    try:
        tables = pd.read_html(StringIO(html))
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

    for required_col in ["candidate", "party", "votes", "status", "margin"]:
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
    best_table["scraped_at"] = now_string()

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

    return best_table.drop_duplicates()


def clean_and_build_final_candidate_dataset(raw_df):
    if raw_df.empty:
        return pd.DataFrame()

    final_df = raw_df.copy()

    required_cols = [
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

    for col in required_cols:
        if col not in final_df.columns:
            final_df[col] = ""

    final_df["candidate"] = final_df["candidate"].astype(str).str.strip()
    final_df["party"] = final_df["party"].astype(str).str.strip()

    final_df = final_df[
        ~final_df["candidate"].str.lower().isin(["total", "nan", ""])
    ].copy()

    final_df = final_df[
        ~final_df["party"].str.lower().isin(["nan", ""])
    ].copy()

    final_df["votes"] = (
        pd.to_numeric(final_df["votes"], errors="coerce")
        .fillna(0)
        .astype(int)
    )

    final_df["constituency_no"] = (
        pd.to_numeric(final_df["constituency_no"], errors="coerce")
        .fillna(0)
        .astype(int)
    )

    final_df = final_df.drop_duplicates(
        subset=["constituency", "candidate", "party"],
        keep="last",
    )

    final_df["vote_rank"] = (
        final_df.groupby("constituency")["votes"]
        .rank(method="first", ascending=False)
        .astype(int)
    )

    second_votes = (
        final_df[final_df["vote_rank"] == 2][["constituency", "votes"]]
        .rename(columns={"votes": "runner_up_votes"})
    )

    final_df = final_df.merge(second_votes, on="constituency", how="left")
    final_df["runner_up_votes"] = final_df["runner_up_votes"].fillna(0).astype(int)

    final_df["vote_margin"] = final_df["votes"] - final_df["runner_up_votes"]
    final_df.loc[final_df["vote_rank"] != 1, "vote_margin"] = 0

    final_df["derived_status"] = final_df["vote_rank"].apply(
        lambda rank: (
            "Leading / Top Candidate"
            if rank == 1
            else ("Runner-up" if rank == 2 else "Trailing")
        )
    )

    final_df["is_leading"] = final_df["vote_rank"] == 1
    final_df["is_winner_like"] = final_df["vote_rank"] == 1

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

    final_df = final_df.sort_values(
        ["constituency_no", "vote_rank", "votes"],
        ascending=[True, True, False],
    )

    return final_df


def rebuild_final_files_from_partial():
    raw_df = load_existing_csv(PARTIAL_RAW_OUTPUT)

    if raw_df.empty:
        return pd.DataFrame()

    final_df = clean_and_build_final_candidate_dataset(raw_df)

    save_csv(raw_df, FINAL_RAW_OUTPUT)
    save_csv(final_df, FINAL_PROCESSED_OUTPUT)

    return final_df


def reset_files():
    files_to_remove = [
        PARTIAL_RAW_OUTPUT,
        FINAL_RAW_OUTPUT,
        FINAL_PROCESSED_OUTPUT,
        SCRAPE_LOG_OUTPUT,
        FAILED_LOG_OUTPUT,
        DISCOVERED_OUTPUT,
    ]

    for path in files_to_remove:
        if os.path.exists(path):
            os.remove(path)

    print("Fresh run selected. Old candidate scrape files removed.")


def scrape_constituency(context, item, delay_ms):
    constituency = item["constituency"]
    constituency_no = item["constituency_no"]
    eci_code = item["eci_code"]
    url = item["candidate_url"]

    candidate_page = context.new_page()

    try:
        candidate_page.goto(url, wait_until="networkidle", timeout=60000)
        candidate_page.wait_for_timeout(delay_ms)

        title = candidate_page.title()
        html = candidate_page.content()

        if "Access Denied" in title or "Access Denied" in html:
            raise RuntimeError("Access denied")

        df = parse_candidate_table(
            html=html,
            constituency=constituency,
            constituency_no=constituency_no,
            eci_code=eci_code,
            url=url,
        )

        if df.empty:
            raise RuntimeError("No candidate table found")

        return df, None

    except Exception as e:
        return pd.DataFrame(), str(e)

    finally:
        candidate_page.close()


def run_once(
    max_constituencies=None,
    visible=True,
    fresh=False,
    delay_ms=3500,
    rebuild_only=False,
):
    if fresh:
        reset_files()

    if rebuild_only:
        final_df = rebuild_final_files_from_partial()
        print("\nRebuild completed.")
        print(f"Processed file: {FINAL_PROCESSED_OUTPUT}")
        print(f"Rows written: {len(final_df)}")
        return final_df

    all_completed_codes = get_completed_eci_codes()

    print("Candidate Scraper v2 started.")
    print(f"Visible browser mode: {visible}")
    print(f"Resume mode: {'enabled' if not fresh else 'fresh run'}")
    print(f"Already completed constituencies: {len(all_completed_codes)}")
    print(f"Delay per constituency page: {delay_ms} ms")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not visible,
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

        constituencies = discover_constituencies(page)

        if not constituencies:
            browser.close()
            raise RuntimeError("No constituency dropdown options discovered.")

        if max_constituencies is not None:
            constituencies = constituencies[:max_constituencies]

        total_to_process = len(constituencies)

        success_count = 0
        skipped_count = 0
        failed_count = 0

        for index, item in enumerate(constituencies, start=1):
            constituency = item["constituency"]
            eci_code = item["eci_code"]

            if eci_code in all_completed_codes:
                skipped_count += 1
                print(f"\n[{index}/{total_to_process}] Skipping completed: {constituency} ({eci_code})")
                continue

            print(f"\n[{index}/{total_to_process}] Scraping: {constituency} ({eci_code})")
            print(item["candidate_url"])

            df, error = scrape_constituency(context, item, delay_ms)

            if error:
                failed_count += 1
                print(f"Failed: {constituency} | {error}")

                append_log_row(
                    {
                        "constituency": constituency,
                        "constituency_no": item["constituency_no"],
                        "eci_code": eci_code,
                        "url": item["candidate_url"],
                        "status": "failed",
                        "row_count": 0,
                        "error": error,
                        "logged_at": now_string(),
                    },
                    SCRAPE_LOG_OUTPUT,
                )

                append_log_row(
                    {
                        "constituency": constituency,
                        "constituency_no": item["constituency_no"],
                        "eci_code": eci_code,
                        "url": item["candidate_url"],
                        "error": error,
                        "failed_at": now_string(),
                    },
                    FAILED_LOG_OUTPUT,
                )

                continue

            append_rows_to_csv(df, PARTIAL_RAW_OUTPUT)

            append_log_row(
                {
                    "constituency": constituency,
                    "constituency_no": item["constituency_no"],
                    "eci_code": eci_code,
                    "url": item["candidate_url"],
                    "status": "success",
                    "row_count": len(df),
                    "error": "",
                    "logged_at": now_string(),
                },
                SCRAPE_LOG_OUTPUT,
            )

            all_completed_codes.add(eci_code)
            success_count += 1

            print(f"Rows scraped: {len(df)}")
            print("Saved progress immediately.")

            final_df = rebuild_final_files_from_partial()

            print(
                f"Processed file refreshed: {FINAL_PROCESSED_OUTPUT} | "
                f"Rows: {len(final_df)} | "
                f"Constituencies: {final_df['constituency'].nunique() if not final_df.empty else 0}"
            )

        browser.close()

    final_df = rebuild_final_files_from_partial()

    print("\nCandidate Scraper v2 completed.")
    print(f"Success this run: {success_count}")
    print(f"Skipped completed: {skipped_count}")
    print(f"Failed this run: {failed_count}")
    print(f"Partial raw file: {PARTIAL_RAW_OUTPUT}")
    print(f"Final raw file: {FINAL_RAW_OUTPUT}")
    print(f"Processed file: {FINAL_PROCESSED_OUTPUT}")
    print(f"Rows written: {len(final_df)}")

    if not final_df.empty:
        print(f"Constituencies: {final_df['constituency'].nunique()}")
        print(f"Parties: {final_df['party'].nunique()}")

    return final_df


def parse_args():
    parser = argparse.ArgumentParser(
        description="ECI candidate-level scraper v2 with resume support."
    )

    parser.add_argument(
        "--max",
        type=int,
        default=None,
        help="Maximum number of constituencies to process from the discovered list.",
    )

    parser.add_argument(
        "--visible",
        action="store_true",
        help="Run Chromium in visible mode. Recommended because ECI blocks headless often.",
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chromium in headless mode. Not recommended for ECI.",
    )

    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Delete previous candidate scrape files and start fresh.",
    )

    parser.add_argument(
        "--delay-ms",
        type=int,
        default=3500,
        help="Delay after opening each constituency page.",
    )

    parser.add_argument(
        "--rebuild-only",
        action="store_true",
        help="Only rebuild final processed file from partial raw file.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    visible_mode = True

    if args.headless:
        visible_mode = False

    if args.visible:
        visible_mode = True

    run_once(
        max_constituencies=args.max,
        visible=visible_mode,
        fresh=args.fresh,
        delay_ms=args.delay_ms,
        rebuild_only=args.rebuild_only,
    )