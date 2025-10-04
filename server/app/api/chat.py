"""Chat endpoint with retrieval augmented generation."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.core.openai_client import OpenAIClient
from app.core.prompts import build_system_prompt, format_context
from app.core.safety import SafetyChecker
from app.core.settings import Settings, get_settings
from app.db import crud
from app.db.session import SessionLocal, session_scope
from app.rag.retriever import Retriever, build_retriever

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=2)
    persona: str = Field(default="neutral", description="neutral|yazan")
    language: str = Field(default="msa", description="msa|jordanian")
    household_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    needs_human: bool
    safety_reasons: list[str]
    context: list[str]
    persona: str


async def get_openai_client(settings: Settings = Depends(get_settings)) -> OpenAIClient:
    return OpenAIClient(settings)


async def get_retriever(
    client: Annotated[OpenAIClient, Depends(get_openai_client)],
    settings: Settings = Depends(get_settings),
) -> Retriever:
    async def embed_query(query: str) -> list[float]:
        vectors = await client.embed_texts([query])
        return vectors[0]

    return build_retriever(settings=settings, session_factory=SessionLocal, embedder=embed_query)


def _trim_words(text: str, limit: int) -> str:
    words = text.split()
    if len(words) <= limit:
        return text
    return " ".join(words[:limit]) + "…"


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    payload: ChatRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    retriever: Retriever = Depends(get_retriever),
    openai_client: OpenAIClient = Depends(get_openai_client),
) -> ChatResponse:
    safety: SafetyChecker = getattr(request.app.state, "safety_checker")
    safety_result = safety.check_user_input(payload.message)
    if not safety_result.safe:
        return ChatResponse(
            reply="أقترح التحدث مباشرة مع مختص موثوق لمتابعة هذا الموضوع الحساس.",
            needs_human=True,
            safety_reasons=safety_result.reasons,
            context=[],
            persona=payload.persona,
        )

    retrieval = await retriever.retrieve(payload.message, top_k=settings.max_context_docs)
    context_prompt = format_context(retrieval.context_bullets)
    system_prompt = build_system_prompt(persona=payload.persona, language=payload.language, settings=settings)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": context_prompt},
        {"role": "user", "content": payload.message},
    ]

    reply_text = await openai_client.chat(messages)
    reply_text = _trim_words(reply_text, settings.max_response_words)

    output_safety = safety.check_assistant_output(reply_text)
    needs_human = bool(output_safety.needs_human or safety_result.needs_human)
    reasons = list({*safety_result.reasons, *output_safety.reasons})

    with session_scope() as session:
        crud.record_chat_log(
            session,
            household_id=payload.household_id,
            persona=payload.persona,
            language=payload.language,
            user_message=payload.message,
            assistant_message=reply_text,
            needs_human=needs_human,
            safety_reasons=reasons,
            context_snippets=retrieval.context_bullets,
        )

    return ChatResponse(
        reply=reply_text,
        needs_human=needs_human,
        safety_reasons=reasons,
        context=retrieval.context_bullets,
        persona=payload.persona,
    )
