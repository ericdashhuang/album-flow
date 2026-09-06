from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        url = get_settings().database_url
        connect_args = {}
        # In-memory SQLite (used by the test suite) needs a shared connection
        # pool, or each new connection would see an empty, separate database.
        if url.startswith("sqlite") and ":memory:" in url:
            from sqlalchemy.pool import StaticPool

            connect_args = {"check_same_thread": False}
            _engine = create_engine(url, connect_args=connect_args, poolclass=StaticPool)
        else:
            _engine = create_engine(url, echo=False)
    return _engine


def init_db() -> None:
    SQLModel.metadata.create_all(get_engine())


def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session
