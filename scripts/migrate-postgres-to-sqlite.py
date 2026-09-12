#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
API_DIR = REPO_ROOT / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from db.postgres_to_sqlite import migrate_postgres_to_sqlite


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy a consistent read-only PostgreSQL snapshot into a SQLite database."
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="PostgreSQL source URL (defaults to DATABASE_URL).",
    )
    parser.add_argument(
        "--sqlite-path",
        default=os.getenv("SQLITE_PATH"),
        help="Destination SQLite path (defaults to SQLITE_PATH).",
    )
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Replace an existing destination after preserving it as a timestamped backup.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Rows fetched from PostgreSQL per batch (default: 500).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.database_url:
        print("error: --database-url or DATABASE_URL is required", file=sys.stderr)
        return 2
    if not args.sqlite_path:
        print("error: --sqlite-path or SQLITE_PATH is required", file=sys.stderr)
        return 2

    try:
        counts = migrate_postgres_to_sqlite(
            args.database_url,
            args.sqlite_path,
            replace_existing=args.replace_existing,
            batch_size=args.batch_size,
        )
    except Exception as exc:
        print(f"migration failed: {exc}", file=sys.stderr)
        return 1

    print(f"SQLite migration completed: {Path(args.sqlite_path).expanduser()}")
    for table, count in counts.items():
        print(f"  {table}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
