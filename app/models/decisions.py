from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class Decision(BaseModel):
    decision: str = Field(min_length=5, max_length=500)
    made_by: Optional[str] = Field(default=None, max_length=100)
    context: Optional[str] = Field(default=None, max_length=1000)
    is_tentative: bool = False
    dissent: bool = False
    source_quote: str = Field(min_length=5, max_length=500)


class DecisionList(BaseModel):
    items: list[Decision] = Field(default_factory=list)
    extraction_notes: Optional[str] = Field(default=None, max_length=500)