"""Chat endpoint with retrieval augmented generation."""
from __future__ import annotations

from typing import Annotated, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.core.openai_client import OpenAIClient
from app.core.prompts import build_system_prompt, format_context
from app.core.safety import SafetyChecker
from app.core.settings import Settings, get_settings
from app.db import crud
from app.db.session import SessionLocal, session_scope
from app.core.security import decode_jwt_optional
from app.rag.retriever import Retriever, build_retriever

router = APIRouter()
HISTORY_MAX_MESSAGES = 16


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=2)
    persona: str = Field(default="neutral", description="neutral|yazan")
    language: str = Field(default="msa", description="msa|jordanian")
    household_id: str | None = None
    thread_id: Optional[str] = None
    browser_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    needs_human: bool
    safety_reasons: list[str]
    context: list[str]
    persona: str
    thread_id: str


class ChatThreadSummary(BaseModel):
    thread_id: str
    title: Optional[str]
    persona: Optional[str]
    lang: Optional[str]
    last_message_at: Optional[str]


class HistoryOut(BaseModel):
    thread_id: str
    turns: List[Dict[str, str]]


class ChatNewRequest(BaseModel):
    persona: Optional[str] = "neutral"
    language: Optional[str] = "msa"


class ChatNewResponse(BaseModel):
    thread_id: str


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


@router.post("/chat/new", response_model=ChatNewResponse)
async def create_chat_thread(
    payload: ChatNewRequest,
    authorization: Optional[str] = Header(default=None),
    x_browser_id: Optional[str] = Header(default=None, alias="x-browser-id"),
):
    claims = decode_jwt_optional(authorization)
    household_id = claims.get("household_id") if claims else None

    with session_scope() as session:
        thread = crud.create_thread(
            session,
            persona=payload.persona,
            lang=payload.language,
            browser_id=x_browser_id,
            household_id=household_id,
        )
        session.flush()
        new_thread_id = thread.id

    return ChatNewResponse(thread_id=new_thread_id)


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    payload: ChatRequest,
    request: Request,
    authorization: Optional[str] = Header(default=None),
    x_browser_id: Optional[str] = Header(default=None, alias="x-browser-id"),
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
            thread_id=payload.thread_id or "",
        )

    claims = decode_jwt_optional(authorization)
    household_id = claims.get("household_id") if claims else None
    browser_id = x_browser_id or payload.browser_id

    with session_scope() as session:
        thread = crud.get_thread(session, payload.thread_id or "") if payload.thread_id else None

        if thread:
            if thread.household_id:
                if household_id and thread.household_id != household_id:
                    raise HTTPException(status_code=403, detail="thread belongs to another household")
                if not household_id:
                    raise HTTPException(status_code=403, detail="login required for this conversation")
            if not household_id and thread.browser_id and browser_id and thread.browser_id != browser_id:
                raise HTTPException(status_code=403, detail="thread belongs to a different session")
            if household_id and not thread.household_id:
                thread.household_id = household_id
            if browser_id and not thread.browser_id:
                thread.browser_id = browser_id
            if payload.persona:
                thread.persona = payload.persona
            if payload.language:
                thread.lang = payload.language
        else:
            thread = crud.create_thread(
                session,
                persona=payload.persona,
                lang=payload.language,
                browser_id=browser_id,
                household_id=household_id,
            )

        session.flush()
        thread_id = thread.id
        persona = thread.persona or payload.persona or "neutral"
        language = thread.lang or payload.language or "msa"
        history = crud.fetch_history(session, thread_id, max_messages=HISTORY_MAX_MESSAGES)

    retrieval = await retriever.retrieve(payload.message, top_k=settings.max_context_docs)
    context_prompt = format_context(retrieval.context_bullets)
    system_prompt = build_system_prompt(persona=persona, language=language, settings=settings)

    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if context_prompt:
        messages.append({"role": "system", "content": context_prompt})
    messages.extend(history)
    messages.append({"role": "user", "content": payload.message})

    reply_text = await openai_client.chat(messages)
    reply_text = _trim_words(reply_text, settings.max_response_words)

    output_safety = safety.check_assistant_output(reply_text)
    needs_human = bool(output_safety.needs_human or safety_result.needs_human)
    reasons = list({*safety_result.reasons, *output_safety.reasons})

    with session_scope() as session:
        crud.log_turn(session, thread_id, "user", payload.message)
        crud.log_turn(session, thread_id, "assistant", reply_text)
        thread = crud.get_thread(session, thread_id)
        if thread:
            if household_id:
                thread.household_id = household_id
            if browser_id and not thread.browser_id:
                thread.browser_id = browser_id
            if payload.persona:
                thread.persona = payload.persona
            if payload.language:
                thread.lang = payload.language
            crud.update_thread_title(session, thread, payload.message)
        crud.record_chat_log(
            session,
            household_id=household_id or payload.household_id,
            persona=persona,
            language=language,
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
        persona=persona,
        thread_id=thread_id,
    )


@router.get("/chat/threads")
async def list_threads(
    x_browser_id: Optional[str] = Header(default=None, alias="x-browser-id"),
    authorization: Optional[str] = Header(default=None),
):
    claims = decode_jwt_optional(authorization)
    with session_scope() as session:
        if claims and claims.get("household_id"):
            items = crud.list_threads_for_household(session, claims["household_id"])
        elif x_browser_id:
            items = crud.list_threads_for_browser(session, x_browser_id, limit=50)
        else:
            return {"threads": []}

        threads_payload = [
            {
                "thread_id": thread.id,
                "title": thread.title or f"Conversation {thread.id[:6]}",
                "persona": thread.persona or "neutral",
                "lang": thread.lang or "msa",
                "last_message_at": thread.last_message_at.isoformat() if thread.last_message_at else "",
            }
            for thread in items
        ]

    return {"threads": threads_payload}


class ClaimThreadsIn(BaseModel):
    browser_id: str


@router.post("/chat/claim")
async def claim_threads(
    payload: ClaimThreadsIn,
    authorization: Optional[str] = Header(default=None),
):
    claims = decode_jwt_optional(authorization)
    household_id = claims.get("household_id") if claims else None
    if not household_id:
        raise HTTPException(status_code=401, detail="auth required")
    with session_scope() as session:
        moved = crud.move_threads_from_browser_to_household(session, payload.browser_id, household_id)
    return {"moved": moved}


@router.get("/chat/history", response_model=HistoryOut)
async def get_history(
    thread_id: str = Query(...),
    limit: int = Query(100, ge=1, le=500),
    authorization: Optional[str] = Header(default=None),
    x_browser_id: Optional[str] = Header(default=None, alias="x-browser-id"),
):
    claims = decode_jwt_optional(authorization)
    with session_scope() as session:
        thread = crud.get_thread(session, thread_id)
        if thread is None:
            return {"thread_id": thread_id, "turns": []}

        if thread.household_id:
            if not claims or thread.household_id != claims.get("household_id"):
                return {"thread_id": thread_id, "turns": []}
        elif thread.browser_id and x_browser_id and thread.browser_id != x_browser_id:
            return {"thread_id": thread_id, "turns": []}
        elif thread.browser_id and not x_browser_id and not claims:
            return {"thread_id": thread_id, "turns": []}

        turns = crud.fetch_history(session, thread_id, max_messages=limit)

    return {"thread_id": thread_id, "turns": turns}
