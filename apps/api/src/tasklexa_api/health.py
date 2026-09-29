import asyncio
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from tasklexa_api.config import Settings


IntegrationStatus = Literal["LIVE", "MOCK", "NOT_CONFIGURED", "FAILED"]


class IntegrationHealth(BaseModel):
    provider: str
    purpose: str
    status: IntegrationStatus
    details: str
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class HealthResponse(BaseModel):
    service: str
    status: Literal["LIVE"]
    environment: str
    phase: str
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class IntegrationsHealthResponse(BaseModel):
    service: str
    integrations: list[IntegrationHealth]
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


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
        tcp_health("Neo4j", "Mission relationship graph", settings.neo4j_host, settings.neo4j_bolt_port),
    )

    external_checks = [
        configured_but_unverified(
            "Band",
            "Agent collaboration fabric",
            bool(settings.band_api_key or settings.band_agent_key),
        ),
        configured_but_unverified(
            "OpenRouter",
            "Model gateway",
            bool(settings.openrouter_api_key),
        ),
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

