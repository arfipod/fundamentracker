import pytest

from repositories import factory
from repositories.base import DatabaseHealthError
from repositories.postgres import PostgresRepository
from repositories.supabase_rest import SupabaseRestRepository


def test_repository_factory_defaults_to_supabase_rest(monkeypatch):
    monkeypatch.delenv("DATABASE_BACKEND", raising=False)

    repository = factory.create_repository()

    assert isinstance(repository, SupabaseRestRepository)
    assert factory.get_database_backend() == "supabase_rest"


def test_repository_factory_accepts_backend_aliases():
    assert isinstance(factory.create_repository("supabase"), SupabaseRestRepository)
    assert isinstance(factory.create_repository("PostgreSQL"), PostgresRepository)


def test_repository_factory_rejects_unknown_backend():
    with pytest.raises(DatabaseHealthError) as exc_info:
        factory.create_repository("sqlite")

    assert exc_info.value.reason == "unsupported_backend"
    assert exc_info.value.backend == "sqlite"


def test_repository_factory_reports_configured_supabase(monkeypatch):
    monkeypatch.setenv("DATABASE_BACKEND", "supabase_rest")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "example-key")

    assert factory.is_database_configured() is True


def test_repository_factory_reports_unconfigured_postgres(monkeypatch):
    monkeypatch.setenv("DATABASE_BACKEND", "postgres")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert factory.is_database_configured() is False
