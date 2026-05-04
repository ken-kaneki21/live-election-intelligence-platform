import os
from bs4 import BeautifulSoup
import pandas as pd


RAW_DIR = "data/raw"


def get_latest_html_file():
    html_files = [
        os.path.join(RAW_DIR, f)
        for f in os.listdir(RAW_DIR)
        if f.endswith(".html")
    ]

    if not html_files:
        raise FileNotFoundError("No HTML files found in data/raw")

    latest_file = max(html_files, key=os.path.getmtime)
    return latest_file


def inspect_html(file_path):
    print(f"Inspecting: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "lxml")

    print("\nPAGE TITLE:")
    print(soup.title.text.strip() if soup.title else "No title found")

    print("\nALL LINKS FOUND:")
    links = []

    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        href = a["href"]
        links.append((text, href))

    for i, (text, href) in enumerate(links[:100], start=1):
        print(f"{i}. TEXT: {text} | HREF: {href}")

    print(f"\nTotal links found: {len(links)}")

    print("\nCHECKING TABLES:")
    try:
        tables = pd.read_html(html)
        print(f"Tables found: {len(tables)}")

        os.makedirs("data/processed", exist_ok=True)

        for i, table in enumerate(tables):
            print(f"\nTable {i}:")
            print(table.head())
            output_path = f"data/processed/extracted_table_{i}.csv"
            table.to_csv(output_path, index=False)
            print(f"Saved: {output_path}")

    except ValueError:
        print("No HTML tables found.")


if __name__ == "__main__":
    latest_html = get_latest_html_file()
    inspect_html(latest_html)