"""pgvector-backed similarity search implementation."""
from __future__ import annotations

from typing import Callable, Sequence

from pgvector.sqlalchemy import Vector
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.db import models
from app.rag.schemas import DocumentChunk, DocumentMetadata


class PgVectorStore:
    def __init__(self, session_factory: Callable[[], Session], settings: Settings) -> None:
        self._session_factory = session_factory
        self._settings = settings

    def upsert(self, chunks: Sequence[DocumentChunk]) -> int:
        try:
            with self._session_factory() as session:
                for chunk in chunks:
                    session.merge(
                        models.DocumentMeta(
                            chunk_id=chunk.chunk_id,
                            document_id=chunk.metadata.document_id,
                            file_name=chunk.metadata.file_name,
                            topic=chunk.metadata.topic,
                            age_range=chunk.metadata.age_range,
                            tone=chunk.metadata.tone,
                            country=chunk.metadata.country,
                            language=chunk.metadata.language,
                            content=chunk.content,
                            embedding=Vector(chunk.embedding),
                        )
                    )
                session.commit()
            return len(chunks)
        except SQLAlchemyError as exc:  # pragma: no cover - DB path
            raise RuntimeError("pgvector upsert failed") from exc

    def similarity_search(self, query_embedding: Sequence[float], top_k: int) -> list[DocumentChunk]:
        with self._session_factory() as session:
            stmt = (
                select(models.DocumentMeta)
                .order_by(models.DocumentMeta.embedding.cosine_distance(query_embedding))
                .limit(top_k)
            )
            rows = session.scalars(stmt).all()
        return [self._to_chunk(row) for row in rows]

    def delete(self, chunk_ids: Sequence[str]) -> None:
        if not chunk_ids:
            return
        with self._session_factory() as session:
            stmt = select(models.DocumentMeta).where(models.DocumentMeta.chunk_id.in_(list(chunk_ids)))
            rows = session.scalars(stmt).all()
            for row in rows:
                session.delete(row)
            session.commit()

    @staticmethod
    def _to_chunk(row: models.DocumentMeta) -> DocumentChunk:
        metadata = DocumentMetadata(
            document_id=row.document_id,
            file_name=row.file_name,
            topic=row.topic,
            age_range=row.age_range,
            tone=row.tone,
            country=row.country,
            language=row.language,
            created_at=row.created_at,
        )
        return DocumentChunk(
            chunk_id=row.chunk_id,
            content=row.content,
            embedding=list(row.embedding),
            metadata=metadata,
        )
