import uuid
from typing import Literal

from pydantic import BaseModel, Field


class GraphMutationResult(BaseModel):
    status: Literal["APPLIED", "FAILED"]
    summary: str
    error: str | None = None


class GraphNode(BaseModel):
    id: str
    labels: list[str]
    properties: dict


class GraphRelationship(BaseModel):
    type: str
    start_id: str
    end_id: str


class MissionGraph(BaseModel):
    mission_id: uuid.UUID
    nodes: list[GraphNode] = Field(default_factory=list)
    relationships: list[GraphRelationship] = Field(default_factory=list)


class GraphAgentRef(BaseModel):
    id: uuid.UUID
    name: str
    capabilities: list[str] = Field(default_factory=list)


class GraphEvidenceRef(BaseModel):
    id: uuid.UUID
    source: str
    source_type: str
    confidence: float | None = None


class ToolUsageInput(BaseModel):
    tool_id: uuid.UUID
    tool_name: str
    action: str


class OutcomeInput(BaseModel):
    id: uuid.UUID
    decision_id: uuid.UUID | None = None
    summary: str
    status: str


class ProjectionReport(BaseModel):
    mission_id: uuid.UUID
    applied: int
    failed: int
    results: list[GraphMutationResult] = Field(default_factory=list)
