"""
FastAPI app: REST + WebSocket endpoints for the meeting-intelligence pipeline.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import (
    Body,
    FastAPI,
    File,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .config import get_settings
from .llm import LLMClient
from .models.report import MeetingIntelligenceReport
from .pipeline import Pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Meeting Intelligence Tool",
    description=(
        "Multi-stage pipeline that turns meeting transcripts into structured "
        "action items, decisions, topics, sentiment, and a summary — with "
        "Pydantic-validated, source-quoted output and a hallucination metric."
    ),
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_settings = get_settings()
_llm = LLMClient()
_pipeline = Pipeline(_llm)

# === Rate limiter (in-memory, per IP, sliding 60-second window, 10 req limit) ===
RATE_LIMIT = 10
RATE_WINDOW_SECONDS = 60
_rate_buckets: dict[str, deque[float]] = defaultdict(deque)


def _check_rate_limit(client_ip: str) -> None:
    now = time.monotonic()
    bucket = _rate_buckets[client_ip]
    cutoff = now - RATE_WINDOW_SECONDS
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "rate_limited", "detail": f"{RATE_LIMIT} requests per minute"},
        )
    bucket.append(now)


# === Persistent lifetime quota per IP. Survives server restarts. ===
USAGE_FILE = Path(__file__).resolve().parent / "data" / "usage.json"
_usage_lock = asyncio.Lock()


def _read_usage() -> dict[str, int]:
    if not USAGE_FILE.exists():
        return {}
    try:
        return json.loads(USAGE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _write_usage(data: dict[str, int]) -> None:
    USAGE_FILE.parent.mkdir(exist_ok=True)
    USAGE_FILE.write_text(json.dumps(data, indent=2))


async def _check_and_consume_quota(client_ip: str) -> None:
    """Increment the IP's lifetime usage. Raises 429 if quota exceeded."""
    if _settings.per_ip_limit <= 0:
        return
    async with _usage_lock:
        data = _read_usage()
        used = int(data.get(client_ip, 0))
        if used >= _settings.per_ip_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "quota_exceeded",
                    "detail": (
                        f"You've used your free demo run. "
                        f"Contact the admin to request more access."
                    ),
                    "admin_email": _settings.admin_email,
                    "limit": _settings.per_ip_limit,
                },
            )
        data[client_ip] = used + 1
        _write_usage(data)


class AnalyzeRequest(BaseModel):
    transcript: str = Field(min_length=10, max_length=50_000)
    meeting_date: Optional[datetime] = None
    speaker_aliases: Optional[dict[str, str]] = None


def _http_err(code: int, error: str, detail: str) -> JSONResponse:
    return JSONResponse(status_code=code, content={"error": error, "detail": detail})


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return _http_err(500, "internal_error", str(exc))


@app.get("/health")
async def health() -> dict[str, Any]:
    """Returns 200 if the server is up. Performs a cheap Claude API ping."""
    try:
        # Lightweight reachability check — 1-token response, no schema.
        await _llm._client.messages.create(  # noqa: SLF001
            model=_settings.claude_model,
            max_tokens=5,
            messages=[{"role": "user", "content": "ping"}],
        )
        claude_reachable = True
    except Exception as e:  # noqa: BLE001
        logger.warning("Claude API ping failed: %s", e)
        claude_reachable = False
    return {
        "status": "ok",
        "model": _settings.claude_model,
        "claude_reachable": claude_reachable,
    }


@app.get("/schema")
async def schema() -> dict[str, Any]:
    """Returns the JSON schema of MeetingIntelligenceReport."""
    return MeetingIntelligenceReport.model_json_schema()


# Sample transcripts (sourced from benchmark/transcripts) for the frontend's demo list.
_SAMPLES_DIR = Path(__file__).resolve().parent.parent / "benchmark" / "transcripts"


def _load_samples_index() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not _SAMPLES_DIR.is_dir():
        return items
    for p in sorted(_SAMPLES_DIR.glob("*.json")):
        try:
            data = json.loads(p.read_text())
            transcript = data.get("transcript", "")
            first_line = transcript.split("\n", 1)[0] if transcript else ""
            items.append({
                "id": data.get("id", p.stem),
                "category": data.get("category", "unknown"),
                "meeting_date": data.get("meeting_date"),
                "preview": first_line[:140],
                "char_count": len(transcript),
                "line_count": transcript.count("\n") + 1 if transcript else 0,
            })
        except (json.JSONDecodeError, OSError):
            continue
    return items


@app.get("/samples")
async def samples() -> dict[str, Any]:
    """Lightweight index of sample transcripts (no full content)."""
    return {"items": _load_samples_index()}


@app.get("/samples/{sample_id}")
async def sample_detail(sample_id: str) -> dict[str, Any]:
    """Full content of one sample transcript by id."""
    # Sanitize: only allow alphanumerics, hyphen, underscore (defends against path traversal).
    if not sample_id.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(400, detail={"error": "bad_sample_id", "detail": "invalid id"})
    p = _SAMPLES_DIR / f"{sample_id}.json"
    if not p.is_file():
        raise HTTPException(404, detail={"error": "not_found", "detail": f"sample {sample_id} not found"})
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError) as e:
        raise HTTPException(500, detail={"error": "read_failed", "detail": str(e)})


async def _run_pipeline(req: AnalyzeRequest) -> MeetingIntelligenceReport:
    try:
        return await asyncio.wait_for(
            _pipeline.run(
                req.transcript,
                meeting_date=req.meeting_date,
                speaker_aliases=req.speaker_aliases,
            ),
            timeout=_settings.pipeline_timeout_seconds,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"error": "pipeline_timeout",
                    "detail": f"exceeded {_settings.pipeline_timeout_seconds}s"},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_input", "detail": str(e)},
        )


@app.post("/analyze")
async def analyze(
    request: Request,
    body: AnalyzeRequest = Body(...),
) -> MeetingIntelligenceReport:
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)
    await _check_and_consume_quota(client_ip)
    return await _run_pipeline(body)


@app.post("/analyze/upload")
async def analyze_upload(
    request: Request,
    file: UploadFile = File(...),
    meeting_date: Optional[str] = None,
    speaker_aliases: Optional[str] = None,
) -> MeetingIntelligenceReport:
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)
    await _check_and_consume_quota(client_ip)
    raw = (await file.read()).decode("utf-8", errors="replace")
    if not raw.strip():
        raise HTTPException(400, detail={"error": "empty_file", "detail": "upload was empty"})
    if len(raw) > _settings.max_transcript_chars:
        raise HTTPException(
            400,
            detail={"error": "too_large",
                    "detail": f"file exceeds {_settings.max_transcript_chars} chars"},
        )
    parsed_date: Optional[datetime] = None
    if meeting_date:
        try:
            parsed_date = datetime.fromisoformat(meeting_date)
        except ValueError:
            raise HTTPException(400, detail={"error": "bad_meeting_date",
                                             "detail": "expected ISO 8601 datetime"})
    parsed_aliases: Optional[dict[str, str]] = None
    if speaker_aliases:
        try:
            parsed_aliases = json.loads(speaker_aliases)
            if not isinstance(parsed_aliases, dict):
                raise ValueError("must be a JSON object")
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(400, detail={"error": "bad_speaker_aliases", "detail": str(e)})
    body = AnalyzeRequest(
        transcript=raw, meeting_date=parsed_date, speaker_aliases=parsed_aliases
    )
    return await _run_pipeline(body)


@app.websocket("/ws/analyze")
async def ws_analyze(websocket: WebSocket) -> None:
    """
    Streams pipeline stage events to the client. The client sends a single JSON
    message (same shape as AnalyzeRequest) as its first frame. The server emits
    one event per stage: {stage, status, data}, then a final {stage: "done"} event.
    """
    await websocket.accept()
    try:
        raw_msg = await websocket.receive_text()
        try:
            payload = json.loads(raw_msg)
            request_model = AnalyzeRequest.model_validate(payload)
        except Exception as e:  # noqa: BLE001
            await websocket.send_json({
                "stage": "input", "status": "error",
                "data": {"error": "invalid_request", "detail": str(e)},
            })
            await websocket.close(code=1003)
            return

        # Quota check — emit structured quota_exceeded event the frontend renders.
        client_ip = websocket.client.host if websocket.client else "unknown"
        try:
            await _check_and_consume_quota(client_ip)
        except HTTPException as e:
            detail = e.detail if isinstance(e.detail, dict) else {"detail": str(e.detail)}
            await websocket.send_json({
                "stage": "quota", "status": "error", "data": detail,
            })
            await websocket.close(code=1008)
            return

        async def emit(stage: str, status_: str, data: dict[str, Any]) -> None:
            try:
                await websocket.send_json({"stage": stage, "status": status_, "data": data})
            except Exception:  # noqa: BLE001
                # Client disconnected mid-stream; let the pipeline finish silently.
                pass

        try:
            await asyncio.wait_for(
                _pipeline.run(
                    request_model.transcript,
                    meeting_date=request_model.meeting_date,
                    speaker_aliases=request_model.speaker_aliases,
                    emit=emit,
                ),
                timeout=_settings.pipeline_timeout_seconds,
            )
        except asyncio.TimeoutError:
            await websocket.send_json({
                "stage": "pipeline", "status": "error",
                "data": {"error": "timeout",
                         "detail": f"exceeded {_settings.pipeline_timeout_seconds}s"},
            })
        except ValueError as e:
            await websocket.send_json({
                "stage": "preprocessing", "status": "error",
                "data": {"error": "invalid_input", "detail": str(e)},
            })
        except Exception as e:  # noqa: BLE001
            logger.exception("WebSocket pipeline error")
            await websocket.send_json({
                "stage": "pipeline", "status": "error",
                "data": {"error": "internal_error", "detail": str(e)},
            })

    except WebSocketDisconnect:
        return
    finally:
        try:
            await websocket.close()
        except Exception:  # noqa: BLE001
            pass