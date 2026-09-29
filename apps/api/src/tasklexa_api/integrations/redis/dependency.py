import asyncio

import redis.asyncio as redis

from tasklexa_api.config import get_settings

# Keyed by running event loop for the same reason as db/session.py's engine
# cache (ADR-014) and the Neo4j driver cache: a connection pool is bound to
# the loop that created it, and a process running multiple independent
# asyncio.run() calls (the test suite) would otherwise reuse a pool tied to
# an already-closed loop.
_clients_by_loop: dict[int, redis.Redis] = {}


def get_redis_client() -> redis.Redis:
    loop = asyncio.get_event_loop()
    key = id(loop)
    client = _clients_by_loop.get(key)
    if client is None:
        client = redis.from_url(get_settings().redis_url, decode_responses=True)
        _clients_by_loop[key] = client
    return client
