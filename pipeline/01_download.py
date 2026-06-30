#!/usr/bin/env python3
"""Download all APSED Excel releases listed in data/releases.csv to data/xlsx/."""
import csv
import urllib.request
from pathlib import Path

XLSX_DIR = Path("data/xlsx")
RELEASES_CSV = Path("data/releases.csv")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; apsed-public/1.0)"}


def dest_path(snapshot_date: str) -> Path:
    return XLSX_DIR / f"apsed_{snapshot_date}.xlsx"


def main() -> None:
    XLSX_DIR.mkdir(parents=True, exist_ok=True)

    with open(RELEASES_CSV, newline="") as f:
        releases = list(csv.DictReader(f))

    print(f"Releases in manifest: {len(releases)}")

    for row in releases:
        label = row["release_label"]
        date = row["snapshot_date"]
        url = row["url"]
        dest = dest_path(date)

        if dest.exists():
            print(f"  [skip]     {label} ({date})  {dest.stat().st_size:>10,} bytes")
            continue

        print(f"  [download] {label} ({date}) ...", end=" ", flush=True)
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            dest.write_bytes(data)
            print(f"{len(data):>10,} bytes")
        except Exception as exc:
            print(f"ERROR: {exc}")


if __name__ == "__main__":
    main()
