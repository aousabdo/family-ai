"""Vector store selection and retrieval orchestration."""
from __future__ import annotations

from typing import Awaitable, Callable

from app.core.settings import Settings
from app.rag.schemas import RetrievalResult
from app.rag.vectorstore_chroma import ChromaVectorStore
from app.rag.vectorstore_pgvector import PgVectorStore

EmbedderFn = Callable[[str], Awaitable[list[float]]]


class Retriever:
    def __init__(self, *, vector_store, embedder: EmbedderFn, settings: Settings) -> None:
        self._vector_store = vector_store
        self._embedder = embedder
        self._settings = settings

    async def retrieve(self, query: str, *, top_k: int | None = None) -> RetrievalResult:
        if not query.strip():
            return RetrievalResult(chunks=[], context_bullets=[])
        embedding = await self._embedder(query)
        top_k = top_k or self._settings.max_context_docs
        chunks = self._vector_store.similarity_search(embedding, top_k=top_k)
        bullets = [chunk.content.strip()[:280] for chunk in chunks]
        return RetrievalResult(chunks=chunks, context_bullets=bullets)


def build_retriever(*, settings: Settings, session_factory, embedder: EmbedderFn) -> Retriever:
    if settings.is_pgvector:
        store = PgVectorStore(session_factory=session_factory, settings=settings)
    else:
        store = ChromaVectorStore(settings=settings)
    return Retriever(vector_store=store, embedder=embedder, settings=settings)
