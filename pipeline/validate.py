#!/usr/bin/env python3
"""
Validate both pipeline outputs against each other and the crosswalk.

Checks:
  C1 — APS-wide headcount per release (apsed_totals_jf.csv): family counts and
       release-over-release totals, useful for spotting unexpected jumps.
  C2 — Agency-table sums vs APS-wide totals: summing all agency×JF rows should be
       slightly below the totals figure (suppressed cells account for the gap).
  C3 — Agency roster changes across the four agency-table releases: flags portfolio
       departments and sub-agencies absent from any release.
  C4 — Crosswalk coverage: any (regime, family_label) pair in either output that
       has no matching row in crosswalk.csv is flagged as missing.
  C5 — "No data" normalisation: confirms all unclassified-employee source variants
       (No Data, Zero Data, etc.) have been normalised to a single label.

A clean run prints no lines containing "MISSING" and shows ✓ for C2 and C4.
"""
import csv
from collections import defaultdict
from pathlib import Path

AGENCY_JF = Path("data/apsed_agency_jf.csv")
TOTALS_JF = Path("data/apsed_totals_jf.csv")
CROSSWALK = Path("data/crosswalk.csv")


def load_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


agency_rows = load_csv(AGENCY_JF)
total_rows  = load_csv(TOTALS_JF)
xwalk_rows  = load_csv(CROSSWALK)

# ── C1: APS-wide headcount per release ───────────────────────────────────────

print("\n=== C1: APS-wide headcount per release (apsed_totals_jf.csv) ===")

totals_by_date: dict[str, int] = defaultdict(int)
families_by_date: dict[str, set] = defaultdict(set)
for r in total_rows:
    totals_by_date[r["snapshot_date"]] += int(r["headcount"])
    families_by_date[r["snapshot_date"]].add(r["job_family"])

print(f"\n  {'Snapshot':<15} {'Regime':<8} {'Families':>9} {'APS total':>12} {'Change':>10}")
print(f"  {'-'*15} {'-'*8} {'-'*9} {'-'*12} {'-'*10}")
prev = None
for date in sorted(totals_by_date):
    regime = next(r["taxonomy_regime"] for r in total_rows if r["snapshot_date"] == date)
    n = totals_by_date[date]
    n_fam = len(families_by_date[date])
    chg = f"{n - prev:+,}" if prev is not None else "—"
    print(f"  {date:<15} {regime:<8} {n_fam:>9} {n:>12,} {chg:>10}")
    prev = n

# ── C2: Agency-table sums vs APS-wide totals ─────────────────────────────────

print("\n=== C2: Agency-table sums vs APS-wide totals (4 overlap releases) ===")

# Portfolio dept rows are direct-employee-only (not sub-agency aggregates);
# summing all rows (portfolio depts + sub-agencies) gives the correct APS total.
atotal_by_date: dict[str, int] = defaultdict(int)
for r in agency_rows:
    if r["headcount"]:
        atotal_by_date[r["snapshot_date"]] += int(r["headcount"])

print(f"\n  {'Snapshot':<15} {'Totals-table':>14} {'Agency-table (all rows)':>24} {'Diff':>8}")
print(f"  {'-'*15} {'-'*14} {'-'*24} {'-'*8}")
for date in sorted(atotal_by_date):
    t_total = totals_by_date.get(date, 0)
    a_total = atotal_by_date[date]
    diff    = a_total - t_total
    note    = f" ← {abs(diff):,} suppressed" if diff != 0 else " ✓"
    print(f"  {date:<15} {t_total:>14,} {a_total:>24,} {diff:>+8,}{note}")

# ── C3: Agency roster changes ─────────────────────────────────────────────────

print("\n=== C3: Agency roster changes across the 4 agency-table releases ===")

dates_in_agency = sorted({r["snapshot_date"] for r in agency_rows})
top_by_date: dict[str, set] = defaultdict(set)
sub_by_date: dict[str, set] = defaultdict(set)
for r in agency_rows:
    if r["is_sub_agency"] == "False":
        top_by_date[r["snapshot_date"]].add(r["agency"])
    else:
        sub_by_date[r["snapshot_date"]].add(r["agency"])

print(f"\n  Portfolio dept counts: { {d: len(top_by_date[d]) for d in dates_in_agency} }")
print(f"  Sub-agency counts:     { {d: len(sub_by_date[d]) for d in dates_in_agency} }")

all_top = set().union(*top_by_date.values())
all_sub = set().union(*sub_by_date.values())

print("\n  Portfolio departments NOT present in all 4 releases:")
missing_top = []
for ag in sorted(all_top):
    dates_present = [d for d in dates_in_agency if ag in top_by_date[d]]
    if len(dates_present) < len(dates_in_agency):
        missing_top.append((ag, dates_present))
        print(f"    '{ag}': present in {dates_present}")
if not missing_top:
    print("    (all present in every release ✓)")

print("\n  Sub-agencies NOT present in all 4 releases (max 20 shown):")
missing_sub = []
for ag in sorted(all_sub):
    dates_present = [d for d in dates_in_agency if ag in sub_by_date[d]]
    if len(dates_present) < len(dates_in_agency):
        missing_sub.append((ag, dates_present))
print(f"    Total with roster changes: {len(missing_sub)}")
for ag, dates_present in missing_sub[:20]:
    print(f"    '{ag}': {dates_present}")

# ── C4: Family labels not covered by crosswalk ───────────────────────────────

print("\n=== C4: Family labels not covered by crosswalk.csv ===")

xwalk_labels = {(r["regime"], r["family_label"]) for r in xwalk_rows}

for label, rows, regime_col, fam_col in [
    ("apsed_agency_jf.csv",  agency_rows, "taxonomy_regime", "job_family"),
    ("apsed_totals_jf.csv",  total_rows,  "taxonomy_regime", "job_family"),
]:
    missing = {(r[regime_col], r[fam_col]) for r in rows
               if (r[regime_col], r[fam_col]) not in xwalk_labels}
    if missing:
        print(f"\n  {label}:")
        for k in sorted(missing):
            print(f"    MISSING  regime={k[0]!r}  family={k[1]!r}")
    else:
        print(f"\n  {label}: all labels covered ✓")

# ── C5: "No data" normalisation spot-check ───────────────────────────────────

print("\n=== C5: 'No data' normalisation ===")

for label, rows, col in [
    ("agency_jf",  agency_rows, "job_family"),
    ("totals_jf",  total_rows,  "job_family"),
]:
    variants = {r[col] for r in rows
                if "data" in r[col].lower() and "and" not in r[col].lower()}
    print(f"\n  {label}: {sorted(variants)}")

print("\n  Sample 'No data' rows from agency_jf (first per release):")
seen_dates: set[str] = set()
for r in agency_rows:
    if r["job_family"] == "No data" and r["snapshot_date"] not in seen_dates and r["is_sub_agency"] == "False":
        seen_dates.add(r["snapshot_date"])
        print(f"    {r['snapshot_date']}  regime={r['taxonomy_regime']}  "
              f"agency={r['agency'][:30]}  headcount={r['headcount'] or '(suppressed)'}")
        if len(seen_dates) >= 4:
            break

# ── C6: Agency headcount totals vs APS-wide totals ───────────────────────────

print("\n=== C6: Agency headcount totals vs APS-wide totals ===")

AGENCY_HC = Path("data/apsed_agency_headcount.csv")
if not AGENCY_HC.exists():
    print("\n  apsed_agency_headcount.csv not found — skipped")
else:
    hc_rows = load_csv(AGENCY_HC)
    hc_total_by_date: dict[str, int] = defaultdict(int)
    for r in hc_rows:
        if r["headcount_total"]:
            hc_total_by_date[r["snapshot_date"]] += int(r["headcount_total"])

    print(f"\n  {'Snapshot':<15} {'Agency-hc':>12} {'Totals-jf':>12} {'Diff':>8}  Note")
    print(f"  {'-'*15} {'-'*12} {'-'*12} {'-'*8}  {'-'*45}")
    all_match = True
    for date in sorted(hc_total_by_date):
        hc  = hc_total_by_date[date]
        tjf = totals_by_date.get(date, 0)
        diff = hc - tjf
        if date >= "2024-06-30":
            note = "✓" if diff == 0 else "MISMATCH"
            if diff != 0:
                all_match = False
        else:
            note = f"gap = {diff:+,} (unclassified employees not in totals-jf pre-Jun 2024)"
        print(f"  {date:<15} {hc:>12,} {tjf:>12,} {diff:>+8,}  {note}")
    if all_match:
        print("\n  Jun 2024+ exact matches ✓")
