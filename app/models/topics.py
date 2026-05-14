from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class Topic(BaseModel):
    title: str = Field(min_length=2, max_length=100)
    summary: str = Field(min_length=10, max_length=500)
    speakers: list[str] = Field(default_factory=list)
    start_utterance_index: int = Field(ge=0)
    end_utterance_index: int = Field(ge=0)

    @model_validator(mode="after")
    def _check_range(self) -> "Topic":
        if self.end_utterance_index < self.start_utterance_index:
            raise ValueError("end_utterance_index must be >= start_utterance_index")
        return self


class TopicList(BaseModel):
    items: list[Topic] = Field(min_length=1)
