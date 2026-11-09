"""Database engine and per-request sessions.

One engine (a connection pool) per process; each request borrows a session
from it and returns it when the request ends. Routers ask for a session
with `Depends(get_session)` instead of creating connections themselves.
"""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    # pool_pre_ping re-checks a pooled connection before use, so a database
    # that restarted (or a Neon compute that slept) doesn't cause errors.
    return create_engine(get_settings().database_url, pool_pre_ping=True)


def get_session() -> Iterator[Session]:
    session_factory = sessionmaker(bind=get_engine())
    with session_factory() as session:
        yield session
