from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable
from uuid import UUID, uuid4

from repositories.sqlite import SQLiteRepository


@dataclass(frozen=True)
class TableSpec:
    name: str
    columns: tuple[str, ...]


TABLES: tuple[TableSpec, ...] = (
    TableSpec(
        "tickers",
        (
            "symbol", "name", "status", "priority", "notes", "thesis",
            "target_action", "updated_at", "created_at",
        ),
    ),
    TableSpec("tags", ("id", "name", "color", "created_at")),
    TableSpec("ticker_tags", ("ticker_symbol", "tag_id")),
    TableSpec(
        "alerts",
        (
            "id", "ticker_symbol", "metric", "operator", "target_value",
            "is_active", "is_triggered", "reference_value", "alert_type",
            "current_value", "current_source", "current_as_of_date",
            "current_fetched_at", "current_expires_at", "current_stale",
            "current_confidence", "deleted_at", "restored_at", "created_at",
        ),
    ),
    TableSpec(
        "alert_history",
        (
            "id", "alert_id", "triggered_at", "trigger_value", "target_value",
            "ticker_symbol", "company_name", "metric", "operator", "alert_type",
            "reference_value", "current_value", "source", "as_of_date",
            "fetched_at", "message",
        ),
    ),
    TableSpec(
        "signals",
        (
            "id", "ticker_symbol", "company_name", "signal_type", "severity",
            "title", "message", "metric", "current_value", "previous_value",
            "target_value", "source", "as_of_date", "fetched_at", "created_at",
            "acknowledged_at", "dismissed_at", "raw_payload",
        ),
    ),
    TableSpec("scan_settings", ("id", "interval_seconds", "last_scan_time")),
    TableSpec(
        "data_providers",
        (
            "id", "name", "provider_type", "is_enabled", "priority", "config",
            "created_at", "updated_at",
        ),
    ),
    TableSpec(
        "metric_snapshots",
        (
            "id", "symbol", "metric", "value", "unit", "currency", "source",
            "as_of_date", "fetched_at", "expires_at", "confidence", "raw_payload",
        ),
    ),
    TableSpec(
        "provider_health",
        ("provider", "status", "last_ok_at", "last_error_at", "last_error"),
    ),
)

JSON_COLUMNS = {("signals", "raw_payload"), ("data_providers", "config"), ("metric_snapshots", "raw_payload")}
BOOLEAN_COLUMNS = {
    ("alerts", "is_active"),
    ("alerts", "is_triggered"),
    ("alerts", "current_stale"),
    ("data_providers", "is_enabled"),
}


def adapt_value(table: str, column: str, value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool) or (table, column) in BOOLEAN_COLUMNS:
        return int(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if (table, column) in JSON_COLUMNS:
        if isinstance(value, str):
            return value
        return json.dumps(value, default=str, separators=(",", ":"))
    return value


def normalize_row(spec: TableSpec, row: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(adapt_value(spec.name, column, row.get(column)) for column in spec.columns)


def _insert_statement(spec: TableSpec) -> str:
    columns = ", ".join(spec.columns)
    placeholders = ", ".join("?" for _ in spec.columns)
    verb = "INSERT OR REPLACE" if spec.name == "scan_settings" else "INSERT"
    return f"{verb} INTO {spec.name} ({columns}) VALUES ({placeholders})"


def initialize_target(database_path: Path) -> None:
    repository = SQLiteRepository(database_path=str(database_path))
    repository.check_connectivity()


def copy_table_rows(
    target: sqlite3.Connection,
    spec: TableSpec,
    rows: Iterable[dict[str, Any]],
) -> int:
    statement = _insert_statement(spec)
    count = 0
    for row in rows:
        target.execute(statement, normalize_row(spec, row))
        count += 1
    return count


def target_count(target: sqlite3.Connection, table: str) -> int:
    return int(target.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _postgres_driver():
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError("psycopg is required to migrate from PostgreSQL") from exc
    return psycopg, dict_row


def _source_count(source, table: str) -> int:
    with source.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) AS count FROM {table}")
        row = cursor.fetchone()
        if isinstance(row, dict):
            return int(row["count"])
        return int(row[0])


def _stream_source_rows(source, dict_row, spec: TableSpec, batch_size: int):
    column_list = ", ".join(spec.columns)
    cursor_name = f"ft_migrate_{spec.name}_{uuid4().hex[:8]}"
    with source.cursor(name=cursor_name, row_factory=dict_row) as cursor:
        cursor.itersize = batch_size
        cursor.execute(f"SELECT {column_list} FROM {spec.name}")
        while True:
            batch = cursor.fetchmany(batch_size)
            if not batch:
                break
            for row in batch:
                yield dict(row)


def migrate_postgres_to_sqlite(
    database_url: str,
    sqlite_path: str | Path,
    *,
    replace_existing: bool = False,
    batch_size: int = 500,
) -> dict[str, int]:
    if not database_url:
        raise ValueError("database_url is required")
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")

    target_path = Path(sqlite_path).expanduser().resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.exists() and not replace_existing:
        raise FileExistsError(
            f"Refusing to overwrite existing SQLite database: {target_path}"
        )

    temporary_path = target_path.with_name(
        f".{target_path.name}.migrating-{uuid4().hex}"
    )
    backup_path: Path | None = None
    psycopg, dict_row = _postgres_driver()

    try:
        initialize_target(temporary_path)
        with psycopg.connect(database_url, row_factory=dict_row) as source:
            source.execute("BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            source_counts = {spec.name: _source_count(source, spec.name) for spec in TABLES}

            with sqlite3.connect(temporary_path) as target:
                target.execute("PRAGMA foreign_keys = ON")
                target.execute("PRAGMA busy_timeout = 5000")
                target.execute("BEGIN IMMEDIATE")
                copied: dict[str, int] = {}
                try:
                    for spec in TABLES:
                        copied[spec.name] = copy_table_rows(
                            target,
                            spec,
                            _stream_source_rows(source, dict_row, spec, batch_size),
                        )
                    target.commit()
                except Exception:
                    target.rollback()
                    raise

                target_counts = {spec.name: target_count(target, spec.name) for spec in TABLES}
                mismatches = {
                    table: (source_counts[table], target_counts[table])
                    for table in source_counts
                    if source_counts[table] != target_counts[table]
                }
                if mismatches:
                    details = ", ".join(
                        f"{table}: source={source}, target={target_count_value}"
                        for table, (source, target_count_value) in mismatches.items()
                    )
                    raise RuntimeError(f"SQLite migration count verification failed: {details}")

                # SQLiteRepository initializes the temporary target in WAL mode.
                # Flush all committed pages into the main database before the
                # atomic rename; the temporary -wal/-shm sidecars are removed
                # only after this connection closes.
                target.execute("PRAGMA wal_checkpoint(TRUNCATE)")

            source.rollback()

        if target_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_path = target_path.with_name(f"{target_path.name}.backup-{timestamp}")
            os.replace(target_path, backup_path)

        os.replace(temporary_path, target_path)
        return source_counts
    except Exception:
        if backup_path is not None and backup_path.exists() and not target_path.exists():
            os.replace(backup_path, target_path)
        raise
    finally:
        for candidate in (
            temporary_path,
            Path(str(temporary_path) + "-wal"),
            Path(str(temporary_path) + "-shm"),
        ):
            try:
                candidate.unlink()
            except FileNotFoundError:
                pass
