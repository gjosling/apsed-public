#!/usr/bin/env python3
"""
Parse APS-wide job family totals from all APSED releases.

Each release contains a job-family-by-gender table (Table 28 or 29 depending
on the release) with APS-total headcount per family. This script locates it by
scanning for a sheet whose header area mentions job family and gender keywords,
then extracts family labels from column A and the total-N column.

Outputs data/apsed_totals_jf.csv:
  snapshot_date, taxonomy_regime, job_family, headcount

Usage:
    uv run python pipeline/03_parse_totals.py
    uv run python pipeline/03_parse_totals.py 2020-06-30
"""
import csv
import datetime
import sys
import traceback
from pathlib import Path

import openpyxl
import pyarrow as pa
import pyarrow.parquet as pq

from utils import XLSX_DIR, REGIME_MAP, FOOTER_PREFIXES, snapshot_date_from_path

OUTPUT = Path("data/apsed_totals_jf.csv")

# REGIME_MAP is imported from utils.py.

OUTPUT_COLS = ["snapshot_date", "taxonomy_regime", "job_family", "headcount"]

_SCHEMA = pa.schema([
    ("snapshot_date",   pa.date32()),
    ("taxonomy_regime", pa.string()),
    ("job_family",      pa.string()),
    ("headcount",       pa.int32()),
])

# Unclassified-employee column label varies across releases; normalise all to "No data".
_FAMILY_NORMALISE: dict[str, str] = {
    "No Data": "No data",
    "Zero Data": "No data",
}

# Fragments present in genuine family names, used to identify data rows.
_FAMILY_FRAGMENTS = (
    "accounting", "administration", "business", "communications",
    "compliance", "data", "development", "engineering", "health",
    "human resource", "ict", "information", "intelligence", "legal",
    "monitoring", "organisation", "policy", "portfolio", "project",
    "research", "science", "senior", "service delivery", "strategic",
    "trades", "no data", "zero data",
)

_STOP_LABELS = frozenset({"total", "all", "source", "family", "job family"})
# FOOTER_PREFIXES is imported from utils.py.


def _looks_like_family(s: str) -> bool:
    sl = s.lower()
    return any(frag in sl for frag in _FAMILY_FRAGMENTS)


def _is_stop_row(s: str) -> bool:
    sl = s.lower().strip()
    return sl in _STOP_LABELS or any(sl.startswith(p) for p in FOOTER_PREFIXES)

# ── Sheet detection ───────────────────────────────────────────────────────────

def find_totals_sheet(wb: openpyxl.Workbook):
    """Return the job-family-by-gender worksheet, or None.

    Accepts sheets whose header area mentions job family AND gender keywords,
    and whose column A contains family names (not agency names). Rejects the
    agency×JF table, which has family names as column headers instead.
    """
    for sname in wb.sheetnames:
        ws = wb[sname]
        header_texts: list[str] = []
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i >= 6:
                break
            for v in row:
                if v is not None:
                    header_texts.append(str(v).lower())

        combined = " ".join(header_texts)

        if not (("job" in combined or "family" in combined) and
                ("male" in combined or "gender" in combined)):
            continue

        # Reject the agency×JF table: it has 6+ JF names as column headers in rows 3–5.
        if "agency" in combined:
            col_jf_hits = 0
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if i < 2 or i > 5:
                    continue
                for j, v in enumerate(row):
                    if j == 0 or v is None:
                        continue
                    if any(frag in str(v).lower() for frag in _FAMILY_FRAGMENTS):
                        col_jf_hits += 1
            if col_jf_hits >= 6:
                continue

        # Confirm: column A in data rows should contain family names.
        family_hits = 0
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i < 3:
                continue
            if i > 30:
                break
            v = row[0]
            if v is not None and _looks_like_family(str(v)):
                family_hits += 1
        if family_hits >= 5:
            return ws

    return None

# ── Total-column detection ────────────────────────────────────────────────────

def find_total_col(ws) -> tuple[int, int]:
    """Return (data_start_row_0based, total_col_index).

    The gender table has a sub-header row with the pattern "N % N % N",
    where the last N column is the APS total. Falls back to looking for
    'total' as a column header label.
    """
    data_start = -1
    total_col = -1

    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i > 10:
            break
        vals = [str(v).strip() if v is not None else "" for v in row]
        non_empty = [(j, v) for j, v in enumerate(vals) if v]
        if not non_empty:
            continue

        # "N % N % N" sub-header pattern: last N column is the total.
        has_n = any(v == "N" for _, v in non_empty)
        has_pct = any(v == "%" or "%" in v for _, v in non_empty)
        if has_n and has_pct:
            n_indices = [j for j, v in non_empty if v == "N"]
            if n_indices:
                total_col = n_indices[-1]
                data_start = i + 1
                break

        # Fallback: 'total' keyword in a non-first column.
        for j, v in non_empty:
            if "total" in v.lower() and j > 1:
                total_col = j
                data_start = i + 1

    return data_start, total_col

# ── Sheet parsing ─────────────────────────────────────────────────────────────

def parse_totals_sheet(ws, snapshot_date: str, regime: str) -> list[dict]:
    data_start, total_col = find_total_col(ws)

    if data_start < 0 or total_col < 0:
        raise ValueError(f"Could not locate total column (data_start={data_start}, total_col={total_col})")

    records: list[dict] = []
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i < data_start:
            continue

        raw = row[0]
        if raw is None:
            continue
        family = str(raw).strip()
        if not family or _is_stop_row(family) or not _looks_like_family(family):
            continue

        total_val = row[total_col] if total_col < len(row) else None
        if total_val is None:
            continue
        try:
            n = int(float(str(total_val).replace(",", "")))
        except ValueError:
            continue

        records.append({
            "snapshot_date": snapshot_date,
            "taxonomy_regime": regime,
            "job_family": _FAMILY_NORMALISE.get(family, family),
            "headcount": n,
        })

    return records

# ── Main ──────────────────────────────────────────────────────────────────────

def main(target_date: str | None = None) -> None:
    files = sorted(XLSX_DIR.glob("apsed_*.xlsx"))
    all_records: list[dict] = []
    processed: list[str] = []

    for path in files:
        date = snapshot_date_from_path(path)
        if not date:
            continue
        if target_date and date != target_date:
            continue
        regime = REGIME_MAP.get(date)
        if not regime:
            print(f"  [warn] No regime mapping for {date}, skipping")
            continue

        print(f"  [{date}] Opening ...", end=" ", flush=True)
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = find_totals_sheet(wb)

        if ws is None:
            wb.close()
            print("totals sheet not found — skipped")
            continue

        try:
            records = parse_totals_sheet(ws, date, regime)
        except Exception as exc:
            wb.close()
            print(f"ERROR: {exc}")
            traceback.print_exc()
            continue

        wb.close()

        aps_total = sum(r["headcount"] for r in records)
        print(f"{len(records)} families, APS total = {aps_total:,}")
        all_records.extend(records)
        processed.append(date)

    if not all_records:
        print("No rows parsed — nothing written.")
        return

    with open(OUTPUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLS)
        writer.writeheader()
        writer.writerows(all_records)

    parquet_path = OUTPUT.with_suffix(".parquet")
    arrays = []
    for col in OUTPUT_COLS:
        field_type = _SCHEMA.field(col).type
        values = [r[col] for r in all_records]
        if field_type == pa.date32():
            values = [datetime.date.fromisoformat(v) for v in values]
        arrays.append(pa.array(values, type=field_type))
    pq.write_table(pa.table(dict(zip(OUTPUT_COLS, arrays)), schema=_SCHEMA), parquet_path)

    print(f"\nWrote {len(all_records):,} rows → {OUTPUT}")
    print(f"                     → {parquet_path}")
    print(f"Dates: {processed}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    main(target)
