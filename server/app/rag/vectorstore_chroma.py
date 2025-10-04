"""ChromaDB-backed lightweight vector store for local development."""
from __future__ import annotations

from typing import Sequence

import numpy as np

if not hasattr(np, "float_"):
    np.float_ = np.float64  # type: ignore[attr-defined]
if not hasattr(np, "uint"):
    np.uint = np.uint64  # type: ignore[attr-defined]

import chromadb
from chromadb.config import Settings as ChromaConfig

from app.core.settings import Settings
from app.rag.schemas import DocumentChunk, DocumentMetadata

_COLLECTION_NAME = "family_ai_docs"


class ChromaVectorStore:
    def __init__(self, settings: Settings) -> None:
        client_settings = ChromaConfig(anonymized_telemetry=False, persist_directory=settings.chroma_persist_dir)
        self._client = chromadb.PersistentClient(settings=client_settings)
        self._collection = self._client.get_or_create_collection(name=_COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
        self._supports_persist = hasattr(self._client, "persist")

    def upsert(self, chunks: Sequence[DocumentChunk]) -> int:
        if not chunks:
            return 0
        self._collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            documents=[chunk.content for chunk in chunks],
            embeddings=[chunk.embedding for chunk in chunks],
            metadatas=[
                {
                    **chunk.metadata.model_dump(mode="json"),
                    "created_at": chunk.metadata.created_at.isoformat(),
                }
                for chunk in chunks
            ],
        )
        if self._supports_persist:
            self._client.persist()
        return len(chunks)

    def similarity_search(self, query_embedding: Sequence[float], top_k: int) -> list[DocumentChunk]:
        if not query_embedding:
            return []
        results = self._collection.query(
            query_embeddings=[list(query_embedding)],
            n_results=top_k,
            include=["documents", "metadatas", "embeddings"],
        )
        documents = (results.get("documents") or [[]])[0]
        ids = (results.get("ids") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]
        embeddings = (results.get("embeddings") or [[]])[0]
        chunks: list[DocumentChunk] = []
        for chunk_id, content, metadata_dict, embedding in zip(ids, documents, metadatas, embeddings, strict=False):
            metadata = DocumentMetadata(**(metadata_dict or {}))
            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    content=content,
                    embedding=list(embedding or []),
                    metadata=metadata,
                )
            )
        return chunks

    def delete(self, chunk_ids: Sequence[str]) -> None:
        if not chunk_ids:
            return
        self._collection.delete(ids=list(chunk_ids))
        if self._supports_persist:
            self._client.persist()
