from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Tone(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"


class EnergyLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Engagement(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SpeakerSentiment(BaseModel):
    speaker: str = Field(min_length=1, max_length=100)
    sentiment: Tone
    engagement: Engagement


class SentimentReport(BaseModel):
    overall_tone: Tone
    energy: EnergyLevel
    conflict_detected: bool = False
    per_speaker: list[SpeakerSentiment] = Field(default_factory=list)
