from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

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
