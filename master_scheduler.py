import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


PARTY_REFRESH_SECONDS = 300          # 5 minutes
CANDIDATE_REBUILD_SECONDS = 1800     # 30 minutes

PROJECT_ROOT = Path(__file__).resolve().parent

PARTY_SCRIPT = PROJECT_ROOT / "eci_party_auto_ingest.py"
CANDIDATE_SCRIPT = PROJECT_ROOT / "eci_candidate_auto_ingest_v2.py"

PARTY_OUTPUT = PROJECT_ROOT / "data" / "processed" / "latest_results.csv"
CANDIDATE_OUTPUT = PROJECT_ROOT / "data" / "processed" / "latest_candidate_results.csv"


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


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


def print_file_status():
    print("\nCurrent output files:")

    if PARTY_OUTPUT.exists():
        print(f"Party output exists: {PARTY_OUTPUT}")
        print(f"Party output modified: {datetime.fromtimestamp(PARTY_OUTPUT.stat().st_mtime)}")
    else:
        print(f"Party output missing: {PARTY_OUTPUT}")

    if CANDIDATE_OUTPUT.exists():
        print(f"Candidate output exists: {CANDIDATE_OUTPUT}")
        print(f"Candidate output modified: {datetime.fromtimestamp(CANDIDATE_OUTPUT.stat().st_mtime)}")
    else:
        print(f"Candidate output missing: {CANDIDATE_OUTPUT}")


def run_loop(run_candidate_rebuild=True):
    print("Master Scheduler started.")
    print(f"Party refresh interval: {PARTY_REFRESH_SECONDS} seconds")
    print(f"Candidate rebuild interval: {CANDIDATE_REBUILD_SECONDS} seconds")
    print("Candidate full scraping is intentionally manual/batch, not automatic every 5 minutes.")
    print_file_status()

    last_party_run = 0
    last_candidate_rebuild = 0

    while True:
        current_time = time.time()

        if current_time - last_party_run >= PARTY_REFRESH_SECONDS:
            run_party_ingestion()
            last_party_run = current_time
            print_file_status()

        if run_candidate_rebuild and current_time - last_candidate_rebuild >= CANDIDATE_REBUILD_SECONDS:
            rebuild_candidate_dataset()
            last_candidate_rebuild = current_time
            print_file_status()

        print(f"\n[{timestamp()}] Sleeping for 30 seconds...")
        time.sleep(30)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Master scheduler for Election Intelligence Platform."
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="Run party ingestion once and candidate rebuild once, then exit.",
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
        "--no-candidate-rebuild-loop",
        action="store_true",
        help="Disable periodic candidate rebuild inside continuous scheduler loop.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.party_only:
        run_party_ingestion()
        print_file_status()
        sys.exit(0)

    if args.candidate_rebuild_only:
        rebuild_candidate_dataset()
        print_file_status()
        sys.exit(0)

    if args.candidate_scrape_visible:
        run_candidate_manual_visible()
        print_file_status()
        sys.exit(0)

    if args.once:
        run_party_ingestion()
        rebuild_candidate_dataset()
        print_file_status()
        sys.exit(0)

    run_loop(run_candidate_rebuild=not args.no_candidate_rebuild_loop)