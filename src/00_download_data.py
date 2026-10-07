"""01-telco-churn — 00_download_data.py — download the real public dataset."""
from pathlib import Path
import sys

import requests

# Verified-live source for IBM's Telco Customer Churn dataset (checked 2026-10).
# NOTE: the commonly-referenced URL on the old `telco-customer-churn-on-ibm-cloud`
# repo now returns 404; `telco-customer-churn-on-icp4d` hosts the same file.
URL = ("https://raw.githubusercontent.com/IBM/telco-customer-churn-on-icp4d/"
       "master/data/Telco-Customer-Churn.csv")

PROJECT = Path(__file__).resolve().parent.parent


def main() -> None:
    dest = PROJECT / "data" / "raw" / "Telco-Customer-Churn.csv"
    dest.parent.mkdir(parents=True, exist_ok=True)

    print(f"Downloading -> {dest}")
    resp = requests.get(URL, timeout=60)
    resp.raise_for_status()

    text = resp.text
    rows = len(text.strip().splitlines()) - 1  # minus header
    if rows <= 0:
        print("FATAL: download returned no data rows", file=sys.stderr)
        sys.exit(1)

    dest.write_text(text, encoding="utf-8")
    print(f"OK: {rows} data rows saved to {dest}")


if __name__ == "__main__":
    main()
