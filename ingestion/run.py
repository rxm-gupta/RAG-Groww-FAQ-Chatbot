"""One-command ingestion entrypoint.

Usage:
    python -m ingestion.run                 # ingest everything in the manifest
    python -m ingestion.run --file foo.pdf  # (re-)ingest a single file
    python -m ingestion.run --limit 3       # smoke test on first N files
"""
from __future__ import annotations

import argparse

from .ingest import run_ingestion


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest official documents into Supabase pgvector")
    parser.add_argument("--file", dest="only_file", help="ingest a single file by name")
    parser.add_argument("--limit", type=int, help="ingest only the first N manifest rows")
    args = parser.parse_args()
    summary = run_ingestion(limit=args.limit, only_file=args.only_file)
    print(summary)


if __name__ == "__main__":
    main()
