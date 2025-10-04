"""Thin async wrapper around the OpenAI Python SDK."""
from __future__ import annotations

import asyncio
from typing import Iterable, Sequence

from fastapi import HTTPException, status
from openai import APIError, AuthenticationError, BadRequestError, NotFoundError, OpenAIError, OpenAI
from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

from app.core.settings import Settings


class OpenAIClient:
    """Provide shared access to chat and embedding endpoints."""

    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OpenAI API key is not configured",
            )
        self._settings = settings
        self._client = OpenAI(api_key=settings.openai_api_key)

    @retry(wait=wait_exponential(multiplier=1, min=1, max=20), stop=stop_after_attempt(4))
    def _embed_sync(self, texts: Sequence[str]) -> list[list[float]]:
        response = self._client.embeddings.create(model=self._settings.embedding_model, input=list(texts))
        return [item.embedding for item in response.data]

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        try:
            return await asyncio.to_thread(self._embed_sync, texts)
        except (BadRequestError, AuthenticationError, NotFoundError) as exc:
            raise HTTPException(status_code=400, detail=f"Embedding error: {exc}") from exc
        except APIError as exc:
            raise HTTPException(status_code=502, detail="Embedding request failed: API error") from exc
        except RetryError as exc:  # pragma: no cover - network failure path
            raise HTTPException(status_code=502, detail="Embedding request failed") from exc

    @retry(wait=wait_exponential(multiplier=1, min=1, max=20), stop=stop_after_attempt(4))
    def _chat_sync(self, messages: Iterable[dict[str, str]]) -> str:
        response = self._client.chat.completions.create(
            model=self._settings.chat_model,
            messages=list(messages),
            temperature=0.6,
        )
        return response.choices[0].message.content or ""

    async def chat(self, messages: Iterable[dict[str, str]]) -> str:
        try:
            return await asyncio.to_thread(self._chat_sync, messages)
        except (BadRequestError, AuthenticationError, NotFoundError) as exc:
            raise HTTPException(status_code=400, detail=f"Chat completion error: {exc}") from exc
        except APIError as exc:
            raise HTTPException(status_code=502, detail="Chat completion failed: API error") from exc
        except RetryError as exc:  # pragma: no cover - network failure path
            raise HTTPException(status_code=502, detail="Chat completion failed") from exc
