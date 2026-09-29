import asyncio
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from tasklexa_api.config import get_settings

# Keyed by running event loop rather than a plain @lru_cache: an AsyncEngine's
# connection pool is bound to the loop that created it, and a long-lived process
# that runs several independent asyncio.run() calls (as the test suite does, one
# per test method) would otherwise hand out a pooled connection tied to an already
# -closed loop. A real deployment has exactly one event loop for its whole life,
# so this still yields exactly one cached engine there.
_engines_by_loop: dict[int, AsyncEngine] = {}


def get_engine() -> AsyncEngine:
    loop = asyncio.get_event_loop()
    key = id(loop)
    engine = _engines_by_loop.get(key)
    if engine is None:
        engine = create_async_engine(get_settings().async_database_url(), pool_pre_ping=True)
        _engines_by_loop[key] = engine
    return engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        yield session
