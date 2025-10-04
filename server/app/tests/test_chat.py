from __future__ import annotations

import asyncio

import pytest

from app.core.safety import SafetyChecker
from app.core.settings import Settings
from app.rag.retriever import Retriever
from app.rag.schemas import DocumentChunk, DocumentMetadata, RetrievalResult


class FakeVectorStore:
    def __init__(self, chunks: list[DocumentChunk]) -> None:
        self._chunks = chunks

    def similarity_search(self, query_embedding, top_k: int):
        return self._chunks[:top_k]


async def fake_embedder(_: str) -> list[float]:
    return [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_retriever_returns_context():
    meta = DocumentMetadata(document_id="doc1", file_name="file.md", topic="sleep", age_range="3-5", tone="warm", country="jo")
    chunk = DocumentChunk(chunk_id="doc1:0", content="اضبط روتين النوم قبل ساعة من موعد النوم.", embedding=[0.1, 0.2, 0.3], metadata=meta)
    retriever = Retriever(vector_store=FakeVectorStore([chunk]), embedder=fake_embedder, settings=Settings())
    result: RetrievalResult = await retriever.retrieve("كيف أساعد طفلي على النوم؟", top_k=1)
    assert result.chunks[0].metadata.topic == "sleep"
    assert "روتين" in result.context_bullets[0]


def test_safety_flags_high_risk():
    safety = SafetyChecker()
    result = safety.check_user_input("أفكر في انتحار")
    assert not result.safe
    assert result.needs_human
    assert any("انتحار" in reason for reason in result.reasons)
