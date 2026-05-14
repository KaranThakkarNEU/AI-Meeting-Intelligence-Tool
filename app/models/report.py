from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from .action_items import ActionItemList
from .decisions import DecisionList
from .sentiment import SentimentReport
from .summary import MeetingSummary
from .topics import TopicList


class ValidationWarning(BaseModel):
    stage: str
    field: str
    message: str


class ValidationReport(BaseModel):
    warnings: list[ValidationWarning] = Field(default_factory=list)
    hallucination_rate: float = Field(ge=0.0, le=1.0)
    total_fields_checked: int = Field(ge=0)
    flagged_fields: int = Field(ge=0)


class StageError(BaseModel):
    stage: str
    error: str


class MeetingIntelligenceReport(BaseModel):
    summary: Optional[MeetingSummary] = None
    action_items: ActionItemList = Field(default_factory=ActionItemList)
    decisions: DecisionList = Field(default_factory=DecisionList)
    topics: Optional[TopicList] = None
    sentiment: Optional[SentimentReport] = None
    validation: ValidationReport
    pipeline_latency_seconds: float = Field(ge=0.0)
    model_used: str
    total_tokens_used: int = Field(ge=0)
    stage_errors: list[StageError] = Field(default_factory=list)
