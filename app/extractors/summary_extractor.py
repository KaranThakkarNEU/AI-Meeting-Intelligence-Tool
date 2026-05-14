from __future__ import annotations

from ..llm import CallStats
from ..models.action_items import ActionItemList
from ..models.summary import MeetingSummary
from ..models.topics import TopicList
from ..models.transcript import Transcript
from .base import BaseExtractor


class SummaryExtractor(BaseExtractor[MeetingSummary]):
    """
    Runs AFTER topic + action item extraction so it can use those results as
    additional context for a more coherent summary.
    """

    stage_name = "summary"
    response_model = MeetingSummary

    def system_prompt(self) -> str:
        return (
            "You are a meeting summarizer. Produce a concise, executive-level summary of the "
            "meeting that a busy reader will see first.\n\n"
            "Rules:\n"
            "1. `title` (3–150 chars) should be a specific, descriptive meeting name "
            "(e.g. 'Q3 Roadmap Sync — Engineering', not 'Meeting').\n"
            "2. `executive_summary` (20–2000 chars, prefer 3–5 sentences) should cover what "
            "the meeting was about, what was decided or progressed, and any notable dynamics.\n"
            "3. `duration_minutes` is your best estimate based on transcript length and pace "
            "(roughly 130–160 words per minute of speech). Leave null if highly uncertain.\n"
            "4. `participant_count` is the number of distinct speakers in the transcript.\n"
            "5. `key_takeaways` is a list of 1–5 short, punchy bullet points (each under 200 "
            "chars). These should be the most important outcomes a reader would skim for.\n"
            "6. Use the provided extracted topics and action items as CONTEXT when summarizing, "
            "but do not just restate them verbatim — synthesize.\n"
            "7. Never invent facts not present in the transcript.\n"
        )

    def user_prompt_with_context(  # type: ignore[override]
        self,
        transcript: Transcript,
        topics: TopicList | None,
        action_items: ActionItemList | None,
    ) -> str:
        ctx_parts: list[str] = []
        if topics and topics.items:
            ctx_parts.append("Already-extracted topics:")
            for t in topics.items:
                ctx_parts.append(f"  - {t.title}: {t.summary}")
        if action_items and action_items.items:
            ctx_parts.append("Already-extracted action items:")
            for it in action_items.items:
                a = f" [{it.assignee}]" if it.assignee else ""
                ctx_parts.append(f"  -{a} {it.description}")
        ctx = "\n".join(ctx_parts) if ctx_parts else "(no prior extractions available)"
        return (
            f"Context from prior pipeline stages:\n{ctx}\n\n"
            "Process the ENTIRE transcript. Do not stop early.\n\n"
            f"Transcript:\n{transcript.to_prompt_text()}"
        )

    async def extract_with_context(
        self,
        transcript: Transcript,
        topics: TopicList | None,
        action_items: ActionItemList | None,
    ) -> tuple[MeetingSummary, CallStats]:
        return await self.llm.call_structured(
            system_prompt=self.system_prompt(),
            user_prompt=self.user_prompt_with_context(transcript, topics, action_items),
            response_model=self.response_model,
        )