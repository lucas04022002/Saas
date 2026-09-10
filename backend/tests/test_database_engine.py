import pytest

from app.core.database import engine_kwargs


class TestDatabaseEngineConfiguration:
    """Test that engine configuration adapts to the database driver."""

    def test_postgresql_uses_prepare_threshold(self):
        """PostgreSQL should use prepare_threshold=None."""
        kwargs = engine_kwargs("postgresql+psycopg://user:pass@localhost/db")
        assert kwargs["connect_args"] == {"prepare_threshold": None}

    def test_sqlite_uses_check_same_thread(self):
        """SQLite should use check_same_thread=False."""
        kwargs = engine_kwargs("sqlite:///./dev.db")
        assert kwargs["connect_args"] == {"check_same_thread": False}

    def test_always_includes_pool_pre_ping(self):
        """Both drivers should keep pool_pre_ping=True."""
        pg_kwargs = engine_kwargs("postgresql+psycopg://user:pass@localhost/db")
        sqlite_kwargs = engine_kwargs("sqlite:///./dev.db")
        assert pg_kwargs["pool_pre_ping"] is True
        assert sqlite_kwargs["pool_pre_ping"] is True

    def test_always_includes_future(self):
        """Both drivers should keep future=True."""
        pg_kwargs = engine_kwargs("postgresql+psycopg://user:pass@localhost/db")
        sqlite_kwargs = engine_kwargs("sqlite:///./dev.db")
        assert pg_kwargs["future"] is True
        assert sqlite_kwargs["future"] is True
