import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CollaborationContext(BaseModel):
    context_id: str
    mission_id: uuid.UUID
    title: str


class Participant(BaseModel):
    agent_handle: str
    role: str | None = None


class ParticipantResult(BaseModel):
    context_id: str
    added: list[str] = Field(default_factory=list)
    already_present: list[str] = Field(default_factory=list)


class MessageReference(BaseModel):
    message_id: str
    context_id: str
    task_id: uuid.UUID | None = None


class EventReference(BaseModel):
    event_id: str
    context_id: str
    event_type: str


class BandEvent(BaseModel):
    event_id: str
    event_type: str
    content: dict = Field(default_factory=dict)
    created_at: datetime | None = None


class SubscriptionHandle(BaseModel):
    context_id: str
    active: bool
