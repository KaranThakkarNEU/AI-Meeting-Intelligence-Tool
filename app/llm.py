from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Type, TypeVar

from anthropic import AsyncAnthropic, APIError
from pydantic import BaseModel, ValidationError

from .config import get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_JSON_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE | re.MULTILINE)


@dataclass
class CallStats:
    """Token + latency stats for a single call_structured invocation (including retries)."""

    input_tokens: int = 0
    output_tokens: int = 0
    attempts: int = 0
    first_try_success: bool = False
    latency_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


def _strip_to_json(text: str) -> str:
    """Strip markdown fences and any preamble/postamble around a JSON object."""
    cleaned = _JSON_FENCE_RE.sub("", text).strip()
    # Find the outermost JSON object or array
    start_obj = cleaned.find("{")
    start_arr = cleaned.find("[")
    starts = [s for s in (start_obj, start_arr) if s != -1]
    if not starts:
        return cleaned
    start = min(starts)
    end_obj = cleaned.rfind("}")
    end_arr = cleaned.rfind("]")
    end = max(end_obj, end_arr)
    if end <= start:
        return cleaned
    return cleaned[start : end + 1]


class LLMClient:
    """Async wrapper around the Anthropic SDK with a Pydantic self-correction retry loop."""

    def __init__(self, client: AsyncAnthropic | None = None) -> None:
        settings = get_settings()
        self._settings = settings
        self._client = client or AsyncAnthropic(api_key=settings.anthropic_api_key)

    @property
    def model(self) -> str:
        return self._settings.claude_model

    async def call_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        max_tokens: int | None = None,
    ) -> tuple[T, CallStats]:
        """
        Send a prompt to Claude and return a validated Pydantic instance.

        On validation failure, the Pydantic error is appended to a retry prompt up to
        settings.max_retries times. Raises the final ValidationError if all attempts fail.
        """
        stats = CallStats()
        start = time.perf_counter()
        schema_json = json.dumps(response_model.model_json_schema(), indent=2)
        system_with_schema = (
            f"{system_prompt}\n\n"
            f"You MUST return ONLY valid JSON conforming to this exact JSON schema:\n"
            f"{schema_json}\n\n"
            f"Return ONLY the JSON object. No preamble. No markdown fences. No explanation."
        )

        current_user_prompt = user_prompt
        last_raw_response: str = ""
        last_error: Exception | None = None

        for attempt in range(1, self._settings.max_retries + 1):
            stats.attempts = attempt
            try:
                response = await asyncio.wait_for(
                    self._client.messages.create(
                        model=self._settings.claude_model,
                        max_tokens=max_tokens or self._settings.max_tokens,
                        temperature=0,
                        system=system_with_schema,
                        messages=[{"role": "user", "content": current_user_prompt}],
                    ),
                    timeout=self._settings.llm_timeout_seconds,
                )
            except (asyncio.TimeoutError, APIError) as e:
                last_error = e
                stats.errors.append(f"attempt {attempt}: API error: {e}")
                logger.warning("LLM API error on attempt %d: %s", attempt, e)
                await asyncio.sleep(min(2 ** (attempt - 1), 8))
                continue

            stats.input_tokens += response.usage.input_tokens
            stats.output_tokens += response.usage.output_tokens
            raw = response.content[0].text if response.content else ""
            last_raw_response = raw

            cleaned = _strip_to_json(raw)
            try:
                data = json.loads(cleaned)
            except json.JSONDecodeError as e:
                last_error = e
                stats.errors.append(f"attempt {attempt}: JSON parse error: {e.msg}")
                logger.warning("JSON parse failed on attempt %d: %s", attempt, e)
                current_user_prompt = (
                    f"Your previous response was not valid JSON. Error: {e.msg}\n\n"
                    f"Your previous response was:\n{raw}\n\n"
                    f"Return ONLY the corrected JSON object. No preamble. No markdown."
                )
                continue

            try:
                instance = response_model.model_validate(data)
                if attempt == 1:
                    stats.first_try_success = True
                stats.latency_seconds = time.perf_counter() - start
                return instance, stats
            except ValidationError as e:
                last_error = e
                stats.errors.append(f"attempt {attempt}: validation error")
                logger.warning("Pydantic validation failed on attempt %d: %s", attempt, e)
                current_user_prompt = (
                    f"Your previous response failed validation with this error:\n{e}\n\n"
                    f"Your previous response was:\n{raw}\n\n"
                    f"Fix the JSON to resolve every error above. "
                    f"Return ONLY the corrected JSON object. No preamble. No markdown."
                )

        stats.latency_seconds = time.perf_counter() - start
        logger.error(
            "call_structured exhausted %d retries. Last raw response: %s",
            self._settings.max_retries,
            last_raw_response[:500],
        )
        raise last_error or RuntimeError("LLM call failed with no captured error")
