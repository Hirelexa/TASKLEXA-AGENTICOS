import asyncio

from tasklexa_api.config import get_settings
from tasklexa_api.integrations.neo4j.graph_service import GraphService

# Keyed by running event loop for the same reason as db/session.py's engine cache
# (see ADR-014): the neo4j driver's connection pool is bound to the loop that
# created it, and a process that runs multiple independent asyncio.run() calls
# (the test suite) would otherwise reuse a pool tied to an already-closed loop.
_services_by_loop: dict[int, GraphService] = {}


def get_graph_service() -> GraphService:
    loop = asyncio.get_event_loop()
    key = id(loop)
    service = _services_by_loop.get(key)
    if service is None:
        settings = get_settings()
        service = GraphService(uri=settings.neo4j_uri, user=settings.neo4j_user, password=settings.neo4j_password)
        _services_by_loop[key] = service
    return service
