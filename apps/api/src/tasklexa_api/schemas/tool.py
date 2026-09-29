import uuid

from pydantic import BaseModel, ConfigDict

from tasklexa_api.domain.enums import RiskLevel, ToolStatus


class ToolDefinitionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str
    provider: str
    capabilities: list[str] | None
    authentication_type: str | None
    risk_level: RiskLevel
    requires_approval: bool
    status: ToolStatus
