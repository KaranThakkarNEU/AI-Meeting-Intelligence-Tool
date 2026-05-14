from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Utterance(BaseModel):
    speaker: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1)
    timestamp: Optional[str] = None


class Transcript(BaseModel):
    utterances: list[Utterance] = Field(min_length=1)
    meeting_date: Optional[datetime] = None
    raw_text: Optional[str] = None

    @property
    def speakers(self) -> list[str]:
        seen: dict[str, None] = {}
        for u in self.utterances:
            seen.setdefault(u.speaker, None)
        return list(seen.keys())

    def to_prompt_text(self) -> str:
        return "\n".join(f"[{i}] {u.speaker}: {u.text}" for i, u in enumerate(self.utterances))