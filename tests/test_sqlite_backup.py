import importlib.util
from pathlib import Path
import sqlite3

import pytest

spec = importlib.util.spec_from_file_location(
    "backup_sqlite", Path(__file__).resolve().parents[1] / "scripts" / "backup-sqlite.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_backup_copies_committed_wal_and_archives_without_deleting(tmp_path):
    source = tmp_path / "live.db"
    with sqlite3.connect(source) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE entries (value TEXT)")
        conn.execute("INSERT INTO entries VALUES ('first')")
        conn.commit()
        first = module.backup_database(source, tmp_path / "backups", 1)
        conn.execute("INSERT INTO entries VALUES ('second')")
        conn.commit()
        second = module.backup_database(source, tmp_path / "backups", 1)
        with sqlite3.connect(second) as snapshot:
            assert snapshot.execute("SELECT value FROM entries").fetchall() == [("first",), ("second",)]
            assert snapshot.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        archived = first.parent / "archive" / first.name
        assert archived.exists()
        with sqlite3.connect(archived) as snapshot:
            assert snapshot.execute("SELECT value FROM entries").fetchall() == [("first",)]
        assert second.stat().st_mode & 0o777 == 0o600


def test_missing_source_does_not_create_empty_database(tmp_path):
    source = tmp_path / "missing.db"
    with pytest.raises(FileNotFoundError):
        module.backup_database(source, tmp_path / "backups")
    assert not source.exists()
