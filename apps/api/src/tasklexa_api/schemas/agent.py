import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from tasklexa_api.domain.enums import AgentDefinitionStatus, AgentExecutionStatus, RiskLevel


class AgentDefinitionCreate(BaseModel):
    name: str
    description: str
    capabilities: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    preferred_model_policy: dict | None = None
    permissions: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    provider: str


class AgentDefinitionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str
    capabilities: list[str] | None
    allowed_tools: list[str] | None
    preferred_model_policy: dict | None
    permissions: list[str] | None
    risk_level: RiskLevel
    provider: str
    status: AgentDefinitionStatus


class AgentExecutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mission_id: uuid.UUID
    agent_definition_id: uuid.UUID
    task_id: uuid.UUID | None
    status: AgentExecutionStatus
    model_used: str | None
    started_at: datetime | None
    completed_at: datetime | None
    token_usage: dict | None
    estimated_cost: float | None
    output: str | None
    confidence: float | None


class AgentTeamPlan(BaseModel):
    mission_id: uuid.UUID
    required_capabilities: list[str] = Field(default_factory=list)
    selected_agents: list[uuid.UUID] = Field(default_factory=list)
    selected_tools: list[uuid.UUID] = Field(default_factory=list)
    unresolved_capabilities: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)
