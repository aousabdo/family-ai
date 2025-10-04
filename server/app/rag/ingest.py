"""Utilities to ingest knowledge base documents into the selected vector store."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Iterable
from uuid import uuid4

import boto3
from fastapi import UploadFile

from app.core.openai_client import OpenAIClient
from app.core.settings import Settings
from app.db import crud
from app.rag.schemas import DocumentChunk, DocumentMetadata, IngestResult
from app.rag.vectorstore_chroma import ChromaVectorStore
from app.rag.vectorstore_pgvector import PgVectorStore


def chunk_text(text: str, *, max_words: int = 220, overlap: int = 40) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    step = max_words - overlap
    for start in range(0, len(words), step):
        slice_words = words[start : start + max_words]
        chunk = " ".join(slice_words).strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def build_vector_store(settings: Settings, session_factory):
    if settings.is_pgvector:
        return PgVectorStore(session_factory=session_factory, settings=settings)
    return ChromaVectorStore(settings=settings)


async def ingest_text(
    *,
    text: str,
    file_name: str,
    metadata_overrides: dict[str, str] | None,
    session_factory,
    settings: Settings,
    openai_client: OpenAIClient,
) -> IngestResult:
    document_id = str(uuid4())
    overrides = metadata_overrides or {}
    meta = DocumentMetadata(
        document_id=document_id,
        file_name=file_name,
        topic=overrides.get("topic", "general"),
        age_range=overrides.get("age_range", "all"),
        tone=overrides.get("tone", "supportive"),
        country=overrides.get("country", "jo"),
        language=overrides.get("language", "ar"),
    )
    chunks_raw = chunk_text(text)
    if not chunks_raw:
        return IngestResult(document_id=document_id, stored_chunks=0, metadata=meta, extras={})
    embeddings = await openai_client.embed_texts(chunks_raw)
    chunks = [
        DocumentChunk(
            chunk_id=f"{document_id}:{idx}",
            content=chunk_text_value,
            embedding=embedding,
            metadata=DocumentMetadata(
                **meta.model_dump(
                    exclude={"created_at"},
                    mode="json",
                )
            ),
        )
        for idx, (chunk_text_value, embedding) in enumerate(zip(chunks_raw, embeddings, strict=True))
    ]
    store = build_vector_store(settings=settings, session_factory=session_factory)
    stored = store.upsert(chunks)

    session = session_factory()
    try:
        crud.upsert_document_registry(
            session,
            document_id=document_id,
            file_name=file_name,
            metadata=meta.model_dump(mode="json"),
            chunk_count=stored,
            s3_uploaded=bool(settings.s3_bucket_corpus),
        )
        session.commit()
    finally:
        session.close()

    return IngestResult(document_id=document_id, stored_chunks=stored, metadata=meta, extras={})


async def ingest_upload(
    *, file: UploadFile, overrides: dict[str, str] | None, session_factory, settings: Settings, openai_client: OpenAIClient
) -> IngestResult:
    file_bytes = await file.read()
    text = file_bytes.decode("utf-8", errors="ignore")
    ingest_result = await ingest_text(
        text=text,
        file_name=file.filename or "uploaded.md",
        metadata_overrides=overrides,
        session_factory=session_factory,
        settings=settings,
        openai_client=openai_client,
    )
    _maybe_upload_to_s3(settings=settings, content=file_bytes, file_name=file.filename or ingest_result.metadata.file_name)
    return ingest_result


def _maybe_upload_to_s3(*, settings: Settings, content: bytes, file_name: str) -> None:
    if not settings.s3_bucket_corpus or not content:
        return
    client = boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id or None,
        aws_secret_access_key=settings.aws_secret_access_key or None,
    )
    client.put_object(Bucket=settings.s3_bucket_corpus, Key=file_name, Body=content, ContentType="text/markdown")
