"""
Multi-format transcript preprocessor.

Auto-detects plain text / SRT / JSON, strips filler markers, normalizes speaker
names via an optional alias map, and produces a clean Transcript Pydantic model.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Optional

from .models.transcript import Transcript, Utterance

# Markers like [inaudible], [crosstalk], (laughter), <noise> — drop them.
_FILLER_RE = re.compile(r"[\[\(<](?:inaudible|crosstalk|noise|laughter|applause|music|silence|pause)[^\]\)>]*[\]\)>]", re.IGNORECASE)
# Drop entire <script>/<style> blocks including their content (XSS safety).
_SCRIPT_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
# HTML/script tags — security: strip from raw input.
_HTML_RE = re.compile(r"<[^>]+>")
# Stray whitespace before punctuation left after filler removal: " ." -> "."
_STRAY_SPACE_PUNCT_RE = re.compile(r"\s+([,.;:!?])")
# Collapse runs of whitespace.
_WS_RE = re.compile(r"\s+")
# SRT timestamp line: "00:00:01,000 --> 00:00:04,000"
_SRT_TS_RE = re.compile(r"\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,.]\d{3}")
# "Speaker: text" prefix (capture conservative speaker name).
_SPEAKER_LINE_RE = re.compile(r"^\s*([A-Za-z][\w .'\-]{0,50}?):\s*(.+)$")


def _clean_text(s: str) -> str:
    s = _SCRIPT_STYLE_RE.sub("", s)
    s = _HTML_RE.sub("", s)
    s = _FILLER_RE.sub("", s)
    s = _STRAY_SPACE_PUNCT_RE.sub(r"\1", s)
    s = _WS_RE.sub(" ", s).strip()
    return s


def _detect_format(raw: str) -> str:
    s = raw.lstrip()
    if s.startswith("[") or s.startswith("{"):
        try:
            json.loads(s)
            return "json"
        except json.JSONDecodeError:
            pass
    if _SRT_TS_RE.search(raw):
        return "srt"
    return "text"


def _parse_text(raw: str) -> list[Utterance]:
    utterances: list[Utterance] = []
    last_speaker: Optional[str] = None
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        m = _SPEAKER_LINE_RE.match(line)
        if m:
            speaker = m.group(1).strip()
            text = _clean_text(m.group(2))
            if text:
                utterances.append(Utterance(speaker=speaker, text=text))
                last_speaker = speaker
        else:
            # Continuation line — append to previous utterance if any, else use Unknown.
            text = _clean_text(line)
            if not text:
                continue
            if utterances and last_speaker:
                prev = utterances[-1]
                utterances[-1] = Utterance(
                    speaker=prev.speaker,
                    text=f"{prev.text} {text}",
                    timestamp=prev.timestamp,
                )
            else:
                utterances.append(Utterance(speaker="Unknown", text=text))
    return utterances


def _parse_srt(raw: str) -> list[Utterance]:
    # SRT blocks separated by blank lines: index / timestamp / text lines.
    blocks = re.split(r"\n\s*\n", raw.strip())
    utterances: list[Utterance] = []
    for block in blocks:
        lines = [ln for ln in (l.strip() for l in block.splitlines()) if ln]
        if not lines:
            continue
        # Drop the index line if it's a bare integer.
        if lines and lines[0].isdigit():
            lines = lines[1:]
        timestamp: Optional[str] = None
        if lines and _SRT_TS_RE.search(lines[0]):
            timestamp = lines[0]
            lines = lines[1:]
        if not lines:
            continue
        text_block = " ".join(lines)
        m = _SPEAKER_LINE_RE.match(text_block)
        if m:
            speaker = m.group(1).strip()
            text = _clean_text(m.group(2))
        else:
            speaker = "Unknown"
            text = _clean_text(text_block)
        if text:
            utterances.append(Utterance(speaker=speaker, text=text, timestamp=timestamp))
    return utterances


def _parse_json(raw: str) -> tuple[list[Utterance], Optional[datetime]]:
    data = json.loads(raw)
    meeting_date: Optional[datetime] = None
    items: list[dict] = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        if isinstance(data.get("utterances"), list):
            items = data["utterances"]
        elif isinstance(data.get("transcript"), list):
            items = data["transcript"]
        if data.get("meeting_date"):
            try:
                meeting_date = datetime.fromisoformat(str(data["meeting_date"]).replace("Z", "+00:00"))
            except ValueError:
                meeting_date = None
    utterances: list[Utterance] = []
    for entry in items:
        if not isinstance(entry, dict):
            continue
        speaker = str(entry.get("speaker") or entry.get("name") or "Unknown").strip() or "Unknown"
        text = _clean_text(str(entry.get("text") or entry.get("content") or ""))
        if not text:
            continue
        ts = entry.get("timestamp") or entry.get("time") or entry.get("start")
        utterances.append(Utterance(speaker=speaker, text=text, timestamp=str(ts) if ts else None))
    return utterances, meeting_date


def _apply_aliases(utterances: list[Utterance], aliases: dict[str, str]) -> list[Utterance]:
    if not aliases:
        return utterances
    norm = {k.lower(): v for k, v in aliases.items()}
    out: list[Utterance] = []
    for u in utterances:
        canonical = norm.get(u.speaker.lower(), u.speaker)
        out.append(Utterance(speaker=canonical, text=u.text, timestamp=u.timestamp))
    return out


def preprocess(
    raw: str,
    *,
    meeting_date: Optional[datetime] = None,
    speaker_aliases: Optional[dict[str, str]] = None,
) -> Transcript:
    """
    Normalize a raw transcript (plain text / SRT / JSON) into a Transcript model.

    Raises ValueError on empty or unparsable input.
    """
    if not raw or not raw.strip():
        raise ValueError("transcript is empty")

    fmt = _detect_format(raw)
    json_date: Optional[datetime] = None
    if fmt == "json":
        utterances, json_date = _parse_json(raw)
    elif fmt == "srt":
        utterances = _parse_srt(raw)
    else:
        utterances = _parse_text(raw)

    if not utterances:
        raise ValueError(f"no utterances parsed from input (detected format: {fmt})")

    utterances = _apply_aliases(utterances, speaker_aliases or {})

    return Transcript(
        utterances=utterances,
        meeting_date=meeting_date or json_date,
        raw_text=raw,
    )