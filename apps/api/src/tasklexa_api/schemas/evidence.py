import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mission_id: uuid.UUID
    task_id: uuid.UUID | None
    agent_execution_id: uuid.UUID | None
    source: str
    source_type: str
    content: str
    confidence: float | None
    demo: bool
    created_at: datetime
