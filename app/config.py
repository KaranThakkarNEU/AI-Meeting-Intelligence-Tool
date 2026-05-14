from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    claude_model: str = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    llm_timeout_seconds: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
    pipeline_timeout_seconds: int = int(os.getenv("PIPELINE_TIMEOUT_SECONDS", "120"))
    max_transcript_chars: int = int(os.getenv("MAX_TRANSCRIPT_CHARS", "50000"))
    max_tokens: int = int(os.getenv("MAX_TOKENS", "4096"))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
