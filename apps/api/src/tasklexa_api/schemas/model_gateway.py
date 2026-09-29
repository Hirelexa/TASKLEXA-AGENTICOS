from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    id: str
    name: str | None = None
    context_length: int | None = None
    pricing: dict | None = None


class ModelCatalog(BaseModel):
    models: list[ModelInfo]
    fetched_at: datetime


class ModelSelectionRequest(BaseModel):
    required_capabilities: list[str] = Field(default_factory=list)
    preferred_models: list[str] = Field(default_factory=list)


class SelectedModel(BaseModel):
    model_id: str
    fallback_models: list[str] = Field(default_factory=list)
    rationale: str


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ModelRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    fallback_models: list[str] = Field(default_factory=list)
    temperature: float | None = None
    max_tokens: int | None = None


class TokenUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ModelResponse(BaseModel):
    model: str
    content: str
    finish_reason: str | None
    usage: TokenUsage | None


class StructuredModelRequest(ModelRequest):
    response_schema_name: str


class ValidatedModelResponse(BaseModel):
    model: str
    data: dict
    usage: TokenUsage | None


class CostEstimate(BaseModel):
    model: str
    estimated_cost_usd: float | None
    note: str
