import uuid
from typing import Literal

from pydantic import BaseModel, Field

from tasklexa_api.domain.enums import MissionStatus


class TaskReadinessReport(BaseModel):
    ready_task_ids: list[uuid.UUID] = Field(default_factory=list)
    blocked_task_ids: list[uuid.UUID] = Field(default_factory=list)
    in_progress_task_ids: list[uuid.UUID] = Field(default_factory=list)
    done_task_ids: list[uuid.UUID] = Field(default_factory=list)
    failed_task_ids: list[uuid.UUID] = Field(default_factory=list)
    cyclic_task_ids: list[uuid.UUID] = Field(default_factory=list)


class TaskDispatchResult(BaseModel):
    task_id: uuid.UUID
    status: Literal["DISPATCHED", "NO_AGENT_AVAILABLE"]
    agent_id: uuid.UUID | None = None
    detail: str | None = None


class DispatchReport(BaseModel):
    mission_id: uuid.UUID
    readiness: TaskReadinessReport
    dispatched: list[TaskDispatchResult] = Field(default_factory=list)
    mission_transitioned_to: MissionStatus | None = None


class FailTaskRequest(BaseModel):
    reason: str


class FailTaskResult(BaseModel):
    task_id: uuid.UUID
    cascaded_failure_ids: list[uuid.UUID] = Field(default_factory=list)


class CompleteTaskRequest(BaseModel):
    actual_output: str | None = None
    confidence: float | None = None
