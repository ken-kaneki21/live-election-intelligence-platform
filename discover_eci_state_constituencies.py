import os
import re
from datetime import datetime
from urllib.parse import urljoin

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


BASE_URL = "https://results.eci.gov.in/ResultAcGenMay2026"
OUTPUT_DIR = "data/raw"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "eci_state_constituency_discovery.csv")
HTML_DEBUG_FILE = os.path.join(OUTPUT_DIR, "eci_discovery_debug.html")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def clean_text(value):
    if value is None:
        return ""
    value = str(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def extract_state_code(value):
    """
    Examples:
    S2228   -> S22
    S031    -> S03
    U071    -> U07
    """
    value = clean_text(value)

    match = re.match(r"([SU]\d{2})", value)
    if match:
        return match.group(1)

    return ""


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


def discover_from_dropdown(html):
    soup = BeautifulSoup(html, "html.parser")

    rows = []

    for option in soup.find_all("option"):
        option_text = clean_text(option.get_text())
        option_value = clean_text(option.get("value"))

        if not option_text or not option_value:
            continue

        if "select constituency" in option_text.lower():
            continue

        if not re.match(r"^[SU]\d+", option_value):
            continue

        state_code = extract_state_code(option_value)
        constituency_name, constituency_no = parse_constituency_text(option_text)

        constituency_url = urljoin(
            BASE_URL + "/",
            f"Constituencywise{option_value}.htm",
        )

        rows.append(
            {
                "state_code": state_code,
                "eci_code": option_value,
                "constituency": constituency_name,
                "constituency_no": constituency_no,
                "constituency_url": constituency_url,
                "discovered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    return pd.DataFrame(rows)


def discover_links_from_html(html):
    soup = BeautifulSoup(html, "html.parser")

    rows = []

    for link in soup.find_all("a"):
        href = clean_text(link.get("href"))
        text = clean_text(link.get_text())

        if not href:
            continue

        if "Constituencywise" not in href:
            continue

        match = re.search(r"Constituencywise([SU]\d+)\.htm", href)

        if not match:
            continue

        eci_code = match.group(1)
        state_code = extract_state_code(eci_code)
        constituency_name, constituency_no = parse_constituency_text(text)

        constituency_url = urljoin(BASE_URL + "/", href)

        rows.append(
            {
                "state_code": state_code,
                "eci_code": eci_code,
                "constituency": constituency_name,
                "constituency_no": constituency_no,
                "constituency_url": constituency_url,
                "discovered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    return pd.DataFrame(rows)


def run_discovery(visible=True):
    print("ECI State Constituency Discovery")
    print(f"Opening: {BASE_URL}")
    print(f"Visible browser: {visible}")

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
        page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(4000)

        title = page.title()
        html = page.content()

        with open(HTML_DEBUG_FILE, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"Page title: {title}")
        print(f"Debug HTML saved: {HTML_DEBUG_FILE}")

        if "Access Denied" in title or "Access Denied" in html:
            browser.close()
            raise RuntimeError("Access Denied. Try again later or use visible mode.")

        dropdown_df = discover_from_dropdown(html)
        link_df = discover_links_from_html(html)

        browser.close()

    print(f"Dropdown rows discovered: {len(dropdown_df)}")
    print(f"Link rows discovered: {len(link_df)}")

    if not dropdown_df.empty and not link_df.empty:
        final_df = pd.concat([dropdown_df, link_df], ignore_index=True)
    elif not dropdown_df.empty:
        final_df = dropdown_df
    elif not link_df.empty:
        final_df = link_df
    else:
        raise RuntimeError("No constituency data discovered from dropdown or links.")

    final_df = final_df.drop_duplicates(
        subset=["state_code", "eci_code", "constituency_url"],
        keep="last",
    )

    final_df = final_df.sort_values(
        ["state_code", "constituency_no", "eci_code"],
        na_position="last",
    )

    final_df.to_csv(OUTPUT_FILE, index=False)

    print("\nDiscovery completed.")
    print(f"Output file: {OUTPUT_FILE}")
    print(f"Total constituencies discovered: {len(final_df)}")

    print("\nState code summary:")
    summary = (
        final_df.groupby("state_code", as_index=False)
        .agg(
            constituencies=("eci_code", "count"),
            first_code=("eci_code", "first"),
            sample_url=("constituency_url", "first"),
        )
        .sort_values("state_code")
    )

    print(summary.to_string(index=False))

    print("\nSample rows:")
    print(
        final_df[
            [
                "state_code",
                "eci_code",
                "constituency",
                "constituency_no",
                "constituency_url",
            ]
        ]
        .head(30)
        .to_string(index=False)
    )

    return final_df


if __name__ == "__main__":
    run_discovery(visible=True)