"""
Pipeline orchestrator.

Wires preprocessor -> 4 parallel extractors -> summary -> validator and
assembles the top-level MeetingIntelligenceReport. Emits stage-completion
events via an optional async callback for WebSocket streaming.

Partial-failure semantics: if a single extractor exhausts retries the
pipeline still completes; the failed stage is recorded in stage_errors
and its slot in the final report is left empty/default.
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Awaitable, Callable, Optional

from pydantic import BaseModel

from .config import get_settings
from .extractors import (
    ActionItemExtractor,
    DecisionExtractor,
    SentimentExtractor,
    SummaryExtractor,
    TopicExtractor,
)
from .llm import CallStats, LLMClient
from .models.action_items import ActionItemList
from .models.decisions import DecisionList
from .models.report import (
    MeetingIntelligenceReport,
    StageError,
)
from .models.sentiment import SentimentReport
from .models.summary import MeetingSummary
from .models.topics import TopicList
from .models.transcript import Transcript
from .preprocessing import preprocess
from .validators import validate

logger = logging.getLogger(__name__)

# An async stage-event callback. Signature: (stage_name, status, data) -> Awaitable[None]
# status is one of: "complete", "error". data is a JSON-serializable dict.
StageEventCallback = Callable[[str, str, dict[str, Any]], Awaitable[None]]


def _model_to_event(obj: BaseModel | None) -> dict[str, Any]:
    if obj is None:
        return {}
    return obj.model_dump(mode="json")


async def _noop_emit(stage: str, status: str, data: dict[str, Any]) -> None:
    return None


class Pipeline:
    """Central coordinator for the full meeting-intelligence extraction pipeline."""

    def __init__(self, llm: Optional[LLMClient] = None) -> None:
        self.llm = llm or LLMClient()
        self.action = ActionItemExtractor(self.llm)
        self.decision = DecisionExtractor(self.llm)
        self.topic = TopicExtractor(self.llm)
        self.sentiment = SentimentExtractor(self.llm)
        self.summary = SummaryExtractor(self.llm)

    async def _run_extractor(
        self,
        name: str,
        coro: Awaitable[tuple[BaseModel, CallStats]],
    ) -> tuple[str, BaseModel | None, CallStats | None, str | None]:
        try:
            model, stats = await coro
            return name, model, stats, None
        except Exception as e:  # noqa: BLE001 — pipeline must survive any per-stage failure
            logger.exception("Extractor %s failed", name)
            return name, None, None, f"{type(e).__name__}: {e}"

    async def run(
        self,
        raw_transcript: str,
        *,
        meeting_date: Optional[datetime] = None,
        speaker_aliases: Optional[dict[str, str]] = None,
        emit: Optional[StageEventCallback] = None,
    ) -> MeetingIntelligenceReport:
        emit = emit or _noop_emit
        settings = get_settings()
        start = time.perf_counter()
        stage_errors: list[StageError] = []
        total_tokens = 0

        # === Stage 1: Preprocessing ===
        try:
            transcript: Transcript = preprocess(
                raw_transcript,
                meeting_date=meeting_date,
                speaker_aliases=speaker_aliases,
            )
            await emit("preprocessing", "complete", {
                "utterance_count": len(transcript.utterances),
                "speakers": transcript.speakers,
            })
        except ValueError as e:
            await emit("preprocessing", "error", {"message": str(e)})
            raise

        # === Stages 2-5: Parallel extraction ===
        results = await asyncio.gather(
            self._run_extractor("action_items", self.action.extract(transcript)),
            self._run_extractor("decisions", self.decision.extract(transcript)),
            self._run_extractor("topics", self.topic.extract(transcript)),
            self._run_extractor("sentiment", self.sentiment.extract(transcript)),
        )

        action_items: ActionItemList = ActionItemList()
        decisions: DecisionList = DecisionList()
        topics: Optional[TopicList] = None
        sentiment: Optional[SentimentReport] = None

        for name, model, stats, err in results:
            if err:
                stage_errors.append(StageError(stage=name, error=err))
                await emit(name, "error", {"message": err})
                continue
            if stats:
                total_tokens += stats.total_tokens
            if name == "action_items" and isinstance(model, ActionItemList):
                action_items = model
            elif name == "decisions" and isinstance(model, DecisionList):
                decisions = model
            elif name == "topics" and isinstance(model, TopicList):
                topics = model
            elif name == "sentiment" and isinstance(model, SentimentReport):
                sentiment = model
            await emit(name, "complete", _model_to_event(model))

        # === Stage 6: Summary (sequential, uses topics + actions as context) ===
        summary_model: Optional[MeetingSummary] = None
        try:
            summary_model, sstats = await self.summary.extract_with_context(
                transcript, topics, action_items,
            )
            total_tokens += sstats.total_tokens
            await emit("summary", "complete", _model_to_event(summary_model))
        except Exception as e:  # noqa: BLE001
            logger.exception("Summary extractor failed")
            err_msg = f"{type(e).__name__}: {e}"
            stage_errors.append(StageError(stage="summary", error=err_msg))
            await emit("summary", "error", {"message": err_msg})

        # === Stage 7: Post-extraction validation ===
        validation = validate(
            transcript,
            action_items=action_items,
            decisions=decisions,
            topics=topics,
            sentiment=sentiment,
            meeting_date=(meeting_date.date() if meeting_date else None),
        )
        await emit("validation", "complete", _model_to_event(validation))

        # === Stage 8: Assembly ===
        latency = time.perf_counter() - start
        report = MeetingIntelligenceReport(
            summary=summary_model,
            action_items=action_items,
            decisions=decisions,
            topics=topics,
            sentiment=sentiment,
            validation=validation,
            pipeline_latency_seconds=latency,
            model_used=settings.claude_model,
            total_tokens_used=total_tokens,
            stage_errors=stage_errors,
        )
        await emit("done", "complete", report.model_dump(mode="json"))
        return report