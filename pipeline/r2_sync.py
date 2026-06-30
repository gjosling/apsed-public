#!/usr/bin/env python3
"""
r2_sync.py — Publish output files to Cloudflare R2 public bucket.

Usage:
    python pipeline/r2_sync.py [--dry-run]

Required environment variables:
    R2_ACCOUNT_ID              Cloudflare account ID (builds the endpoint URL)
    R2_PUBLIC_ACCESS_KEY_ID    Access key for the public bucket
    R2_PUBLIC_SECRET_ACCESS_KEY
    R2_PUBLIC_BUCKET           Public bucket name
"""

import argparse
import os
import sys
from pathlib import Path

import boto3
from boto3.s3.transfer import TransferConfig
from dotenv import load_dotenv

load_dotenv()

# (local_path, r2_key)
PUSH_PUBLIC = [
    ("data/apsed_agency_jf.csv",             "apsed/apsed_agency_jf.csv"),
    ("data/apsed_agency_jf.parquet",         "apsed/apsed_agency_jf.parquet"),
    ("data/apsed_agency_headcount.csv",      "apsed/apsed_agency_headcount.csv"),
    ("data/apsed_agency_headcount.parquet",  "apsed/apsed_agency_headcount.parquet"),
    ("data/apsed_totals_jf.csv",             "apsed/apsed_totals_jf.csv"),
    ("data/apsed_totals_jf.parquet",         "apsed/apsed_totals_jf.parquet"),
]

TRANSFER_CFG = TransferConfig(multipart_threshold=8 * 1024 * 1024)


def _check_env(*vars: str) -> None:
    missing = [v for v in vars if not os.environ.get(v)]
    if missing:
        for v in missing:
            print(f"Missing required environment variable: {v}", file=sys.stderr)
        sys.exit(1)


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_PUBLIC_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_PUBLIC_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def _remote_size(s3, bucket: str, key: str) -> int | None:
    try:
        return s3.head_object(Bucket=bucket, Key=key)["ContentLength"]
    except Exception:
        return None


def _push_one(s3, bucket: str, local: str, r2_key: str, dry_run: bool) -> str:
    p = Path(local)
    if not p.exists():
        return f"SKIP (not found locally): {local}"

    local_size = p.stat().st_size
    if _remote_size(s3, bucket, r2_key) == local_size:
        return f"skip (unchanged, {local_size / 1e6:.1f} MB): {r2_key}"

    mb = local_size / 1e6
    if dry_run:
        return f"would push ({mb:.1f} MB): {local} → {r2_key}"

    s3.upload_file(Filename=str(p), Bucket=bucket, Key=r2_key, Config=TRANSFER_CFG)
    return f"pushed ({mb:.1f} MB): {r2_key}"


def push(dry_run: bool = False) -> None:
    _check_env("R2_ACCOUNT_ID",
               "R2_PUBLIC_ACCESS_KEY_ID", "R2_PUBLIC_SECRET_ACCESS_KEY", "R2_PUBLIC_BUCKET")
    s3     = _s3_client()
    bucket = os.environ["R2_PUBLIC_BUCKET"]
    if dry_run:
        print("Mode: dry run\n")

    total_mb = 0.0
    for local, r2_key in PUSH_PUBLIC:
        msg = _push_one(s3, bucket, local, r2_key, dry_run)
        print(f"  {msg}")
        if msg.startswith("pushed"):
            total_mb += Path(local).stat().st_size / 1e6

    print()
    if dry_run:
        print("Dry run complete.")
    else:
        print(f"Push complete. {total_mb:.1f} MB uploaded this run.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Publish APSED output files to Cloudflare R2 public bucket."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="print what would be transferred without actually transferring",
    )
    args = parser.parse_args()
    push(dry_run=args.dry_run)
