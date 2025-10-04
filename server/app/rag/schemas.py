"""Shared data structures for RAG operations."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    document_id: str
    file_name: str
    topic: str = Field(default="general")
    age_range: str = Field(default="all")
    tone: str = Field(default="neutral")
    country: str = Field(default="jo")
    language: str = Field(default="ar")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentChunk(BaseModel):
    chunk_id: str
    content: str
    embedding: list[float]
    metadata: DocumentMetadata


class RetrievalResult(BaseModel):
    chunks: list[DocumentChunk]
    context_bullets: list[str]


class IngestResult(BaseModel):
    document_id: str
    stored_chunks: int
    metadata: DocumentMetadata
    extras: dict[str, Any] = Field(default_factory=dict)
