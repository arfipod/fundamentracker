from __future__ import annotations

import argparse
import hashlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MIGRATIONS_DIR = PROJECT_ROOT / "db" / "migrations"
LOCK_KEY = "fundamentracker_schema_migrations"

CREATE_SCHEMA_MIGRATIONS_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
  version TEXT PRIMARY KEY,
  checksum TEXT NOT NULL,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


class MigrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class Migration:
    version: str
    path: Path
    checksum: str


@dataclass(frozen=True)
class MigrationSummary:
    applied: int
    skipped: int
    total: int
    dry_run: bool = False


def load_dotenv_if_available(project_root: Path = PROJECT_ROOT) -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    load_dotenv(project_root / ".env", override=False)


def compute_checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as migration_file:
        for chunk in iter(lambda: migration_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_migrations(migrations_dir: Path = DEFAULT_MIGRATIONS_DIR) -> list[Migration]:
    if not migrations_dir.exists():
        raise MigrationError(f"migrations directory does not exist: {migrations_dir}")
    if not migrations_dir.is_dir():
        raise MigrationError(f"migrations path is not a directory: {migrations_dir}")

    migrations = []
    for path in sorted(migrations_dir.glob("*.sql")):
        if not path.is_file():
            continue
        migrations.append(
            Migration(
                version=path.name,
                path=path,
                checksum=compute_checksum(path),
            )
        )
    return migrations


def assert_applied_checksum_matches(migration: Migration, applied_checksum: str) -> None:
    if applied_checksum != migration.checksum:
        raise MigrationError(
            "applied migration checksum differs from the file on disk: "
            f"{migration.version}"
        )


def import_psycopg():
    try:
        import psycopg
    except ImportError as exc:
        raise MigrationError(
            "psycopg is required to run database migrations. "
            "Install project requirements or use scripts/migrate-db.sh with Docker."
        ) from exc
    return psycopg


def ensure_schema_migrations(conn) -> None:
    conn.execute(CREATE_SCHEMA_MIGRATIONS_SQL)


def schema_migrations_exists(conn) -> bool:
    exists = conn.execute(
        "SELECT to_regclass('public.schema_migrations') IS NOT NULL"
    ).fetchone()
    return bool(exists and exists[0])


def fetch_applied_migrations(conn) -> dict[str, str]:
    if not schema_migrations_exists(conn):
        return {}
    rows = conn.execute("SELECT version, checksum FROM schema_migrations").fetchall()
    return {version: checksum for version, checksum in rows}


def acquire_migration_lock(conn) -> None:
    conn.execute("SELECT pg_advisory_lock(hashtext(CAST(%s AS text)))", (LOCK_KEY,))


def release_migration_lock(conn) -> None:
    conn.execute("SELECT pg_advisory_unlock(hashtext(CAST(%s AS text)))", (LOCK_KEY,))


def apply_migration(conn, migration: Migration) -> None:
    sql = migration.path.read_text(encoding="utf-8")
    with conn.transaction():
        conn.execute(sql)
        conn.execute(
            """
            INSERT INTO schema_migrations (version, checksum)
            VALUES (%s, %s)
            """,
            (migration.version, migration.checksum),
        )


def run_migrations(
    *,
    database_url: str,
    migrations_dir: Path = DEFAULT_MIGRATIONS_DIR,
    dry_run: bool = False,
) -> MigrationSummary:
    migrations = discover_migrations(migrations_dir)
    psycopg = import_psycopg()

    applied_count = 0
    skipped_count = 0

    with psycopg.connect(database_url) as conn:
        conn.autocommit = True
        if not dry_run:
            ensure_schema_migrations(conn)
        acquire_migration_lock(conn)
        try:
            applied_migrations = fetch_applied_migrations(conn)
            for migration in migrations:
                applied_checksum = applied_migrations.get(migration.version)
                if applied_checksum is not None:
                    assert_applied_checksum_matches(migration, applied_checksum)
                    print(f"Skipping already applied migration: {migration.version}")
                    skipped_count += 1
                    continue

                if dry_run:
                    print(f"Would apply migration: {migration.version}")
                else:
                    print(f"Applying migration: {migration.version}")
                    apply_migration(conn, migration)
                applied_count += 1
        finally:
            release_migration_lock(conn)

    return MigrationSummary(
        applied=applied_count,
        skipped=skipped_count,
        total=len(migrations),
        dry_run=dry_run,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run FundamenTracker SQL migrations.")
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="PostgreSQL connection URL. Defaults to DATABASE_URL.",
    )
    parser.add_argument(
        "--migrations-dir",
        type=Path,
        default=DEFAULT_MIGRATIONS_DIR,
        help=f"Directory containing *.sql migrations. Defaults to {DEFAULT_MIGRATIONS_DIR}.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print pending migrations without applying them.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv_if_available()
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.database_url:
        print("ERROR: DATABASE_URL must be set to run migrations.", file=sys.stderr)
        return 2

    try:
        summary = run_migrations(
            database_url=args.database_url,
            migrations_dir=args.migrations_dir,
            dry_run=args.dry_run,
        )
    except Exception as exc:
        print(f"ERROR: migration failed: {exc}", file=sys.stderr)
        return 1

    action = "would apply" if summary.dry_run else "applied"
    print(
        "Migration summary: "
        f"{action} {summary.applied}, skipped {summary.skipped}, "
        f"total {summary.total}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
