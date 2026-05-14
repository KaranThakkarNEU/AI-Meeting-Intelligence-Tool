from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class MeetingSummary(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    executive_summary: str = Field(min_length=20, max_length=2000)
    duration_minutes: Optional[int] = Field(default=None, ge=0, le=1440)
    participant_count: int = Field(ge=1)
    key_takeaways: list[str] = Field(min_length=1, max_length=5)
