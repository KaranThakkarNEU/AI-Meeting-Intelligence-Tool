from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


_GENERIC_DESCRIPTIONS = {"tbd", "todo", "to be determined", "n/a", "na", "none", "pending"}


class ActionItem(BaseModel):
    description: str = Field(min_length=5, max_length=500)
    assignee: Optional[str] = Field(default=None, max_length=100)
    due_date: Optional[date] = None
    priority: Priority = Priority.MEDIUM
    confidence: float = Field(ge=0.0, le=1.0)
    source_quote: str = Field(min_length=5, max_length=500)

    @field_validator("description")
    @classmethod
    def reject_generic(cls, v: str) -> str:
        if v.strip().lower() in _GENERIC_DESCRIPTIONS:
            raise ValueError(
                f"description must be specific, not a generic placeholder like '{v}'"
            )
        return v.strip()


class ActionItemList(BaseModel):
    items: list[ActionItem] = Field(default_factory=list)
    extraction_notes: Optional[str] = Field(default=None, max_length=500)