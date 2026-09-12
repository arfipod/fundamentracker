from __future__ import annotations

import os
import time

from repositories.base import (
    DEFAULT_POSTGRES_STARTUP_TIMEOUT_SECONDS,
    SUPPORTED_DATABASE_BACKENDS,
    DatabaseHealthError,
    FundamenTrackerRepository,
    normalize_database_backend,
)
from repositories.postgres import PostgresRepository
from repositories.sqlite import SQLiteRepository
from repositories.supabase_rest import SupabaseRestRepository


def get_database_backend() -> str:
    return normalize_database_backend(os.getenv("DATABASE_BACKEND"))


def is_postgres_backend() -> bool:
    return get_database_backend() == "postgres"


def create_repository(backend: str | None = None) -> FundamenTrackerRepository:
    selected_backend = normalize_database_backend(
        os.getenv("DATABASE_BACKEND") if backend is None else backend
    )

    if selected_backend == "postgres":
        return PostgresRepository()
    if selected_backend == "sqlite":
        return SQLiteRepository()
    if selected_backend == "supabase_rest":
        return SupabaseRestRepository()

    raise DatabaseHealthError(
        reason="unsupported_backend",
        detail="DATABASE_BACKEND must be one of 'supabase_rest', 'postgres', or 'sqlite'.",
        backend=selected_backend,
    )


def get_repository() -> FundamenTrackerRepository:
    return create_repository()


def is_database_configured() -> bool:
    backend = get_database_backend()
    if backend not in SUPPORTED_DATABASE_BACKENDS:
        return False
    return create_repository(backend).is_configured()


def check_database_connectivity() -> dict[str, str]:
    return create_repository().check_connectivity()


def wait_for_database_ready(
    timeout_seconds: int = DEFAULT_POSTGRES_STARTUP_TIMEOUT_SECONDS,
    interval_seconds: float = 2.0,
) -> dict[str, str]:
    if not is_postgres_backend():
        return check_database_connectivity()

    deadline = time.monotonic() + timeout_seconds
    last_error: DatabaseHealthError | None = None

    while time.monotonic() < deadline:
        try:
            return check_database_connectivity()
        except DatabaseHealthError as error:
            last_error = error
            time.sleep(interval_seconds)

    detail = "PostgreSQL did not become ready before startup timed out."
    reason = "timeout"
    if last_error is not None:
        detail = f"{detail} Last error: {last_error.detail}"
        reason = last_error.reason

    raise DatabaseHealthError(reason=reason, detail=detail, backend="postgres")
