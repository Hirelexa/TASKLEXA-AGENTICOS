import asyncio

from tasklexa_api.config import Settings
from tasklexa_api.integrations.neo4j.dependency import get_graph_service
from tasklexa_api.integrations.openrouter.gateway import ModelGateway
from tasklexa_api.schemas.health import (
    HealthResponse,
    IntegrationHealth,
    IntegrationsHealthResponse,
    IntegrationStatus,
)

__all__ = [
    "HealthResponse",
    "IntegrationHealth",
    "IntegrationsHealthResponse",
    "IntegrationStatus",
    "collect_integration_health",
    "configured_but_unverified",
    "tcp_health",
]


async def tcp_health(provider: str, purpose: str, host: str, port: int) -> IntegrationHealth:
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=1.5)
        writer.close()
        await writer.wait_closed()
        return IntegrationHealth(
            provider=provider,
            purpose=purpose,
            status="LIVE",
            details=f"TCP connection succeeded at {host}:{port}",
        )
    except Exception as exc:
        return IntegrationHealth(
            provider=provider,
            purpose=purpose,
            status="FAILED",
            details=f"TCP connection failed at {host}:{port}: {exc.__class__.__name__}",
        )


def configured_but_unverified(provider: str, purpose: str, credential_present: bool) -> IntegrationHealth:
    if credential_present:
        return IntegrationHealth(
            provider=provider,
            purpose=purpose,
            status="NOT_CONFIGURED",
            details="Credential is present, but Phase 1 does not perform live provider verification.",
        )

    return IntegrationHealth(
        provider=provider,
        purpose=purpose,
        status="NOT_CONFIGURED",
        details="Credential is missing; no live provider calls will be attempted.",
    )


async def collect_integration_health(settings: Settings) -> list[IntegrationHealth]:
    local_checks = await asyncio.gather(
        tcp_health("PostgreSQL", "Transactional application state", settings.postgres_host, settings.postgres_port),
        tcp_health("Redis", "Transient execution state and cache", settings.redis_host, settings.redis_port),
        get_graph_service().health(),
    )

    gateway = ModelGateway(api_key=settings.openrouter_api_key)
    try:
        openrouter_health = await gateway.health()
    finally:
        await gateway.aclose()

    external_checks = [
        configured_but_unverified(
            "Band",
            "Agent collaboration fabric",
            bool(settings.band_api_key or settings.band_agent_key),
        ),
        openrouter_health,
        IntegrationHealth(
            provider="Similarweb",
            purpose="Discoverable digital intelligence tool",
            status="MOCK" if settings.demo_mode else "NOT_CONFIGURED",
            details=(
                "DEMO_MODE is enabled; any Similarweb demo response must be labeled DEMO DATA."
                if settings.demo_mode
                else "Credential is missing; Similarweb remains unavailable."
            ),
        ),
        configured_but_unverified(
            "Vultr Kubernetes Engine",
            "Future deployment target",
            bool(settings.vultr_api_key),
        ),
    ]

    return [*local_checks, *external_checks]
