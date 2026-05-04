import os
from datetime import datetime
from playwright.sync_api import sync_playwright


RAW_DIR = "data/raw"
os.makedirs(RAW_DIR, exist_ok=True)


def scrape_dynamic_page(url, source_name="eci_dynamic"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(RAW_DIR, f"{source_name}_{timestamp}.html")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        print(f"Opening: {url}")
        page.goto(url, wait_until="networkidle", timeout=60000)

        print("\nPage title:")
        print(page.title())

        print("\nLinks found on page:")
        links = page.locator("a").evaluate_all(
            """
            elements => elements.map(a => ({
                text: a.innerText,
                href: a.href
            }))
            """
        )

        for i, link in enumerate(links, start=1):
            print(f"{i}. TEXT: {link['text']} | HREF: {link['href']}")

        html = page.content()

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        browser.close()

    print(f"\nDynamic HTML saved at: {output_path}")


if __name__ == "__main__":
    scrape_dynamic_page("https://results.eci.gov.in/", "eci_dynamic_home")