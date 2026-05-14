from __future__ import annotations

from ..models.decisions import DecisionList
from .base import BaseExtractor


class DecisionExtractor(BaseExtractor[DecisionList]):
    stage_name = "decisions"
    response_model = DecisionList

    def system_prompt(self) -> str:
        return (
            "You are a meeting decision extractor. Your job is to identify every decision "
            "made or tentatively agreed upon during the meeting.\n\n"
            "Rules:\n"
            "1. Extract only decisions EXPLICITLY discussed in the transcript. Never invent "
            "decisions not stated.\n"
            "2. Every decision must include a `source_quote` (5+ chars) that is a verbatim or "
            "near-verbatim substring of the transcript. This is mandatory.\n"
            "3. Set `is_tentative=true` for soft leanings or preliminary directions "
            "('Let us lean toward A for now', 'I think we should probably...'). Set false for "
            "firm commitments ('We are going with A', 'Decision: ship next Friday').\n"
            "4. Set `dissent=true` if anyone voiced disagreement, concern, or pushback against "
            "the decision in the transcript. Otherwise false.\n"
            "5. Set `made_by` to the speaker(s) who made or led the decision when clear. Use "
            "comma-separated names if multiple. Leave null if no clear decider.\n"
            "6. `context` should briefly explain the reasoning or trade-offs discussed "
            "(1–2 sentences). Leave null only if no rationale was given.\n"
            "7. Discussion topics WITHOUT a decision should NOT be extracted. A decision "
            "requires a choice, commitment, or direction.\n"
            "8. If no decisions were made, return an empty `items` list. Do not invent any.\n"
        )