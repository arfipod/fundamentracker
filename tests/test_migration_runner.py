from pathlib import Path

import pytest

from db.migration_runner import (
    MigrationError,
    assert_applied_checksum_matches,
    discover_migrations,
)


def write_migration(path: Path, sql: str) -> None:
    path.write_text(sql, encoding="utf-8")


def test_discover_migrations_returns_sql_files_in_order(tmp_path):
    write_migration(tmp_path / "002_second.sql", "SELECT 2;")
    write_migration(tmp_path / "001_first.sql", "SELECT 1;")
    (tmp_path / "README.md").write_text("not a migration", encoding="utf-8")

    migrations = discover_migrations(tmp_path)

    assert [migration.version for migration in migrations] == [
        "001_first.sql",
        "002_second.sql",
    ]
    assert all(len(migration.checksum) == 64 for migration in migrations)


def test_discover_migrations_requires_directory(tmp_path):
    missing_dir = tmp_path / "missing"

    with pytest.raises(MigrationError, match="does not exist"):
        discover_migrations(missing_dir)


def test_applied_migration_checksum_must_match(tmp_path):
    migration_path = tmp_path / "001_example.sql"
    write_migration(migration_path, "SELECT 1;")
    migration = discover_migrations(tmp_path)[0]

    with pytest.raises(MigrationError, match="checksum differs"):
        assert_applied_checksum_matches(migration, "different-checksum")
