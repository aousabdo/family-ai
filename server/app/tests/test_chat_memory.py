from __future__ import annotations

import os
import sys
from types import SimpleNamespace

import pytest
from starlette.requests import Request

# Minimal stub for jwt so tests can run without external dependency.
if "jwt" not in sys.modules:
    sys.modules["jwt"] = SimpleNamespace(
        encode=lambda *args, **kwargs: "test-token",
        decode=lambda *args, **kwargs: {},
        PyJWTError=Exception,
    )

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_memory.db")
os.environ.setdefault("VECTOR_BACKEND", "chroma")

from app.api import chat as chat_api
from app.core.safety import SafetyChecker
from app.core.settings import Settings
from app.db import crud
from app.db.session import init_db, session_scope
from app.rag.schemas import RetrievalResult


class StubRetriever:
    async def retrieve(self, message: str, top_k: int) -> RetrievalResult:
        return RetrievalResult(chunks=[], context_bullets=[])


class StubOpenAIClient:
    async def chat(self, messages: list[dict[str, str]]) -> str:
        last_user = [m for m in messages if m["role"] == "user"][::-1][0]["content"]
        return f"[hist={len(messages)}] {last_user}"


@pytest.mark.asyncio
async def test_memory_roundtrip() -> None:
    init_db()
    with session_scope() as session:
        thread = crud.create_thread(
            session,
            persona="neutral",
            lang="msa",
            browser_id="test-browser",
            household_id=None,
        )
        thread_id = thread.id
        crud.log_turn(session, thread_id, "user", "مرحبا")
        crud.log_turn(session, thread_id, "assistant", "أهلاً وسهلاً")

    payload = chat_api.ChatRequest(
        message="تذكّر ماذا قلت؟",
        persona="neutral",
        language="msa",
        household_id=None,
        thread_id=thread_id,
        browser_id="test-browser",
    )

    scope = {
        "type": "http",
        "app": SimpleNamespace(state=SimpleNamespace(safety_checker=SafetyChecker())),
        "headers": [],
        "method": "POST",
        "path": "/api/chat",
        "query_string": b"",
        "client": ("testclient", 12345),
        "server": ("testserver", 80),
    }
    request = Request(scope)

    response = await chat_api.chat_endpoint(
        payload,
        request=request,
        authorization=None,
        x_browser_id="test-browser",
        settings=Settings(),
        retriever=StubRetriever(),
        openai_client=StubOpenAIClient(),
    )

    assert "hist=" in response.reply
    assert "تذكّر" in response.reply
    hist_value = int(response.reply.split("]")[0].split("=")[-1])
    assert hist_value > 3  # system + context + new user + prior turns
