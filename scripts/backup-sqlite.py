#!/usr/bin/env python3
"""Create and verify a WAL-safe snapshot; archive older snapshots without deletion."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import tempfile


def backup_database(source: Path, directory: Path, keep_recent: int = 14) -> Path:
    if keep_recent < 1:
        raise ValueError("keep_recent must be positive")
    source = source.resolve(strict=True)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    destination = directory / f"fundamentracker-{stamp}.db"
    fd, temporary_name = tempfile.mkstemp(prefix=".snapshot-", dir=directory)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as original:
            with sqlite3.connect(temporary) as snapshot:
                original.backup(snapshot, pages=256, sleep=0.05)
                if snapshot.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                    raise RuntimeError("Backup integrity check failed")
                if snapshot.execute("PRAGMA foreign_key_check").fetchall():
                    raise RuntimeError("Backup contains foreign-key violations")
                snapshot.execute("PRAGMA journal_mode=DELETE")
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    except Exception:
        # Keep unsuccessful snapshots for diagnosis; never delete existing backups.
        raise

    older = sorted(directory.glob("fundamentracker-*.db"), reverse=True)[keep_recent:]
    if older:
        archive = directory / "archive"
        archive.mkdir(mode=0o700, exist_ok=True)
        for path in older:
            target = archive / path.name
            if target.exists():
                raise FileExistsError(target)
            path.rename(target)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=os.getenv("SQLITE_PATH"))
    parser.add_argument("--directory", type=Path,
                        default=os.getenv("SQLITE_BACKUP_DIR", "/srv/fundamentracker/backups"))
    parser.add_argument("--keep-recent", type=int,
                        default=int(os.getenv("SQLITE_BACKUP_KEEP_RECENT", "14")))
    args = parser.parse_args()
    if not args.source:
        parser.error("--source or SQLITE_PATH is required")
    os.umask(0o077)
    path = backup_database(args.source, args.directory, args.keep_recent)
    print(f"Verified SQLite backup: {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
