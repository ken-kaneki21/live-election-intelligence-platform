import time
from datetime import datetime

from eci_party_auto_ingest import run_once


REFRESH_SECONDS = 300  # 5 minutes


def main():
    print("Election ingestion scheduler started.")
    print(f"Refresh interval: {REFRESH_SECONDS} seconds")

    while True:
        print("\n--------------------------------")
        print(f"Starting ingestion at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            run_once()
            print("Ingestion completed successfully.")

        except Exception as e:
            print(f"Ingestion failed: {e}")

        print(f"Sleeping for {REFRESH_SECONDS} seconds...")
        time.sleep(REFRESH_SECONDS)


if __name__ == "__main__":
    main()