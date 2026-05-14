from __future__ import annotations

from ..models.sentiment import SentimentReport
from .base import BaseExtractor


class SentimentExtractor(BaseExtractor[SentimentReport]):
    stage_name = "sentiment"
    response_model = SentimentReport

    def system_prompt(self) -> str:
        return (
            "You are a meeting sentiment analyzer. Produce a meeting-level overview AND a "
            "per-speaker breakdown of sentiment and engagement.\n\n"
            "Rules:\n"
            "1. `overall_tone` is one of: positive, neutral, negative, mixed. Use 'mixed' "
            "when both positive and negative moments are clearly present.\n"
            "2. `energy` is one of: high, medium, low. High = enthusiastic, fast-paced, many "
            "interjections. Low = slow, terse, disengaged. Medium = anything in between.\n"
            "3. `conflict_detected` is true ONLY if there is clear disagreement, pushback, or "
            "tension in the transcript. Polite differences of opinion are not conflict.\n"
            "4. `per_speaker` must include EVERY distinct speaker who has at least one "
            "utterance. Use speaker names exactly as they appear in the transcript.\n"
            "5. For each speaker, set `sentiment` (positive/neutral/negative/mixed) and "
            "`engagement` (high/medium/low) based on their actual contributions: number of "
            "utterances, depth of input, expressed enthusiasm or disinterest.\n"
            "6. Base every judgment on the transcript text. Do not invent emotional context "
            "that is not supported by what was actually said.\n"
        )