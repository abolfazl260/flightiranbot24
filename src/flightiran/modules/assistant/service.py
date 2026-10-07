"""Retrieval-first assistant with safe provider fallback."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True)
class Citation:
    title: str
    source_url: str
    checked_on: date


@dataclass(frozen=True)
class AssistantAnswer:
    text: str
    citations: tuple[Citation, ...]
    confidence: str
    fallback: bool = False


class LLMProvider(Protocol):
    async def answer(self, prompt: str, context: str) -> str: ...


class AssistantService:
    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider

    async def answer(
        self, question: str, citations: list[Citation], context: str = ""
    ) -> AssistantAnswer:
        lowered = question.casefold()
        if any(
            term in lowered for term in ("ignore previous", "system prompt", "reveal instructions")
        ):
            return AssistantAnswer(
                "I can answer travel questions using verified sources.", (), "low", fallback=True
            )
        if self.provider is None:
            return AssistantAnswer(
                "No assistant provider is available. Please use the cited travel sources.",
                tuple(citations),
                "medium" if citations else "low",
                fallback=True,
            )
        try:
            text = await self.provider.answer(question, context)
        except Exception:
            return AssistantAnswer(
                "The assistant is unavailable; please use the cited sources.",
                tuple(citations),
                "low",
                True,
            )
        return AssistantAnswer(text, tuple(citations), "high" if citations else "medium")
