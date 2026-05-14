"""
Post-extraction semantic validator.

Cross-references extracted output against the source transcript:
- assignees and decision-makers must be known speakers
- source_quote fields must approximately appear in the transcript (fuzzy match)
- due dates must not be in the past relative to meeting_date

Produces a ValidationReport with a hallucination_rate metric.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from rapidfuzz import fuzz

from .models.action_items import ActionItemList
from .models.decisions import DecisionList
from .models.report import ValidationReport, ValidationWarning
from .models.sentiment import SentimentReport
from .models.topics import TopicList
from .models.transcript import Transcript

# Fuzzy-match threshold for source_quote substring lookup.
QUOTE_MATCH_THRESHOLD = 80


def _normalize_name(s: str) -> str:
    return s.strip().lower()


def _quote_in_transcript(quote: str, transcript_text: str) -> bool:
    quote = quote.strip()
    if not quote:
        return False
    # Cheap exact check first.
    if quote.lower() in transcript_text.lower():
        return True
    # Fuzzy partial: best matching window inside transcript.
    score = fuzz.partial_ratio(quote.lower(), transcript_text.lower())
    return score >= QUOTE_MATCH_THRESHOLD


def validate(
    transcript: Transcript,
    *,
    action_items: Optional[ActionItemList] = None,
    decisions: Optional[DecisionList] = None,
    topics: Optional[TopicList] = None,
    sentiment: Optional[SentimentReport] = None,
    meeting_date: Optional[date] = None,
) -> ValidationReport:
    warnings: list[ValidationWarning] = []
    fields_checked = 0
    flagged = 0

    speakers_norm = {_normalize_name(s) for s in transcript.speakers}
    transcript_text = "\n".join(u.text for u in transcript.utterances)
    last_idx = len(transcript.utterances) - 1
    meeting_d = meeting_date or (transcript.meeting_date.date() if transcript.meeting_date else None)

    # Action items
    if action_items:
        for i, item in enumerate(action_items.items):
            if item.assignee:
                fields_checked += 1
                if _normalize_name(item.assignee) not in speakers_norm:
                    flagged += 1
                    warnings.append(ValidationWarning(
                        stage="action_items", field=f"items[{i}].assignee",
                        message=f"assignee {item.assignee!r} is not a known speaker "
                                f"(speakers: {sorted(transcript.speakers)})",
                    ))
            fields_checked += 1
            if not _quote_in_transcript(item.source_quote, transcript_text):
                flagged += 1
                warnings.append(ValidationWarning(
                    stage="action_items", field=f"items[{i}].source_quote",
                    message=f"source_quote not found in transcript (fuzzy <{QUOTE_MATCH_THRESHOLD}%)",
                ))
            if item.due_date and meeting_d and item.due_date < meeting_d:
                fields_checked += 1
                flagged += 1
                warnings.append(ValidationWarning(
                    stage="action_items", field=f"items[{i}].due_date",
                    message=f"due_date {item.due_date} is before meeting_date {meeting_d}",
                ))

    # Decisions
    if decisions:
        for i, d in enumerate(decisions.items):
            if d.made_by:
                # made_by can be comma-separated; check each.
                for name in [n.strip() for n in d.made_by.split(",") if n.strip()]:
                    fields_checked += 1
                    if _normalize_name(name) not in speakers_norm:
                        flagged += 1
                        warnings.append(ValidationWarning(
                            stage="decisions", field=f"items[{i}].made_by",
                            message=f"made_by {name!r} is not a known speaker",
                        ))
            fields_checked += 1
            if not _quote_in_transcript(d.source_quote, transcript_text):
                flagged += 1
                warnings.append(ValidationWarning(
                    stage="decisions", field=f"items[{i}].source_quote",
                    message=f"source_quote not found in transcript",
                ))

    # Topics — check indices and speakers
    if topics:
        for i, t in enumerate(topics.items):
            fields_checked += 1
            if t.end_utterance_index > last_idx:
                flagged += 1
                warnings.append(ValidationWarning(
                    stage="topics", field=f"items[{i}].end_utterance_index",
                    message=f"end_utterance_index {t.end_utterance_index} exceeds last index {last_idx}",
                ))
            for sp in t.speakers:
                fields_checked += 1
                if _normalize_name(sp) not in speakers_norm:
                    flagged += 1
                    warnings.append(ValidationWarning(
                        stage="topics", field=f"items[{i}].speakers",
                        message=f"speaker {sp!r} not in transcript",
                    ))

    # Sentiment — per_speaker speakers must exist
    if sentiment:
        for i, ps in enumerate(sentiment.per_speaker):
            fields_checked += 1
            if _normalize_name(ps.speaker) not in speakers_norm:
                flagged += 1
                warnings.append(ValidationWarning(
                    stage="sentiment", field=f"per_speaker[{i}].speaker",
                    message=f"speaker {ps.speaker!r} not in transcript",
                ))

    rate = (flagged / fields_checked) if fields_checked > 0 else 0.0
    return ValidationReport(
        warnings=warnings,
        hallucination_rate=rate,
        total_fields_checked=fields_checked,
        flagged_fields=flagged,
    )