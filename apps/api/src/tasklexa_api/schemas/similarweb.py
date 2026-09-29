from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class AnalyzeWebsiteRequest(BaseModel):
    domain: str


class CompareCompetitorsRequest(BaseModel):
    domain: str
    competitor_domains: list[str] = Field(default_factory=list)


class SearchMarketSignalsRequest(BaseModel):
    query: str


class ToolAvailability(BaseModel):
    available: bool
    reason: str


class ToolResult(BaseModel):
    tool: str
    status: Literal["LIVE", "MOCK", "FAILED"]
    demo: bool
    data: dict
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
