from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, Type, TypeVar

from pydantic import BaseModel

from ..llm import CallStats, LLMClient
from ..models.transcript import Transcript

T = TypeVar("T", bound=BaseModel)


class BaseExtractor(ABC, Generic[T]):
    """Shared scaffolding for every Claude-powered extractor."""

    stage_name: str = "base"
    response_model: Type[T]

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    @abstractmethod
    def system_prompt(self) -> str:
        ...

    def user_prompt(self, transcript: Transcript) -> str:
        return (
            "Process the ENTIRE transcript below. Do not stop early or skip sections.\n\n"
            "Transcript (each line is prefixed with its utterance index in brackets):\n"
            f"{transcript.to_prompt_text()}"
        )

    async def extract(self, transcript: Transcript) -> tuple[T, CallStats]:
        return await self.llm.call_structured(
            system_prompt=self.system_prompt(),
            user_prompt=self.user_prompt(transcript),
            response_model=self.response_model,
        )