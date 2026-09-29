import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from tasklexa_api.domain.enums import ExecutionEventStatus, ExecutionEventType


class ExecutionEventCreate(BaseModel):
    mission_id: uuid.UUID
    task_id: uuid.UUID | None = None
    agent_execution_id: uuid.UUID | None = None
    correlation_id: uuid.UUID
    event_type: ExecutionEventType
    provider: str | None = None
    status: ExecutionEventStatus
    error_category: str | None = None
    payload: dict | None = None


class ExecutionEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mission_id: uuid.UUID
    task_id: uuid.UUID | None
    agent_execution_id: uuid.UUID | None
    correlation_id: uuid.UUID
    event_type: ExecutionEventType
    provider: str | None
    status: ExecutionEventStatus
    error_category: str | None
    payload: dict | None
    created_at: datetime
