import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from tasklexa_api.domain.enums import MissionStatus, RiskLevel, TaskPriority, TaskStatus


class MissionCreate(BaseModel):
    title: str
    objective: str
    description: str | None = None
    constraints: list[str] | None = None
    success_criteria: list[str] | None = None
    created_by: str


class MissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    objective: str
    description: str | None
    status: MissionStatus
    constraints: list[str] | None
    success_criteria: list[str] | None
    created_by: str
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class TaskCreate(BaseModel):
    mission_id: uuid.UUID
    title: str
    description: str | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    required_capabilities: list[str] | None = None
    dependencies: list[uuid.UUID] | None = None
    assigned_agent: uuid.UUID | None = None
    tool_requirements: list[str] | None = None
    expected_output: str | None = None


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mission_id: uuid.UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    required_capabilities: list[str] | None
    dependencies: list[uuid.UUID] | None
    assigned_agent: uuid.UUID | None
    tool_requirements: list[str] | None
    expected_output: str | None
    actual_output: str | None
    confidence: float | None
    created_at: datetime
    completed_at: datetime | None


class PlannedTask(BaseModel):
    title: str
    description: str | None = None
    required_capabilities: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    expected_output: str | None = None


class MissionPlan(BaseModel):
    objective: str
    constraints: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    required_capabilities: list[str] = Field(default_factory=list)
    tasks: list[PlannedTask]
    dependencies: dict[str, list[str]] = Field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.LOW
    approval_points: list[str] = Field(default_factory=list)
