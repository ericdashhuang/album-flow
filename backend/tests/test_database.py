from app.database import _normalize_database_url


def test_normalizes_bare_postgresql_scheme_to_psycopg_dialect():
    url = "postgresql://user:pass@host:5432/dbname"
    assert _normalize_database_url(url) == "postgresql+psycopg://user:pass@host:5432/dbname"


def test_normalizes_legacy_postgres_scheme_to_psycopg_dialect():
    url = "postgres://user:pass@host:5432/dbname"
    assert _normalize_database_url(url) == "postgresql+psycopg://user:pass@host:5432/dbname"


def test_leaves_explicit_psycopg_dialect_unchanged():
    url = "postgresql+psycopg://user:pass@host:5432/dbname"
    assert _normalize_database_url(url) == url


def test_leaves_sqlite_url_unchanged():
    url = "sqlite:///:memory:"
    assert _normalize_database_url(url) == url
