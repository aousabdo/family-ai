"""Admin-only upload and corpus management endpoints."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.core.openai_client import OpenAIClient
from app.core.security import AuthenticatedUser, get_current_admin_user
from app.core.settings import Settings, get_settings
from app.db import crud, models
from app.db.session import SessionLocal
from app.rag.ingest import build_vector_store, ingest_upload

router = APIRouter()


class DocumentEntry(BaseModel):
    document_id: str
    file_name: str
    topic: str
    age_range: str
    tone: str
    country: str
    language: str
    chunk_count: int
    s3_uploaded: bool
    updated_at: datetime



async def get_openai_client(settings: Settings = Depends(get_settings)) -> OpenAIClient:
    return OpenAIClient(settings)


@router.post("/admin/upload")
async def upload_document(
    file: UploadFile = File(...),
    topic: str = Form(default="general"),
    age_range: str = Form(default="all"),
    tone: str = Form(default="supportive"),
    country: str = Form(default="jo"),
    language: str = Form(default="ar"),
    admin: AuthenticatedUser = Depends(get_current_admin_user),
    settings: Settings = Depends(get_settings),
    client: OpenAIClient = Depends(get_openai_client),
):
    overrides = {
        "topic": topic,
        "age_range": age_range,
        "tone": tone,
        "country": country,
        "language": language,
    }
    result = await ingest_upload(
        file=file,
        overrides=overrides,
        session_factory=SessionLocal,
        settings=settings,
        openai_client=client,
    )
    return {"document_id": result.document_id, "stored_chunks": result.stored_chunks}


@router.get("/admin/documents", response_model=list[DocumentEntry])
async def list_documents(admin: AuthenticatedUser = Depends(get_current_admin_user)):
    session = SessionLocal()
    try:
        records = crud.list_documents(session)
        return [
            DocumentEntry(
                document_id=doc.document_id,
                file_name=doc.file_name,
                topic=doc.topic,
                age_range=doc.age_range,
                tone=doc.tone,
                country=doc.country,
                language=doc.language,
                chunk_count=doc.chunk_count,
                s3_uploaded=doc.s3_uploaded,
                updated_at=doc.updated_at,
            )
            for doc in records
        ]
    finally:
        session.close()


@router.delete("/admin/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    admin: AuthenticatedUser = Depends(get_current_admin_user),
    settings: Settings = Depends(get_settings),
):
    session = SessionLocal()
    try:
        registry = session.get(models.DocumentRegistry, document_id)
        chunk_ids = crud.get_chunk_ids_by_document(session, document_id)
    finally:
        session.close()

    if not registry and not chunk_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    session = SessionLocal()
    try:
        crud.delete_document_metadata(session, document_id)
        crud.delete_document_registry(session, document_id)
        session.commit()
    finally:
        session.close()

    if not settings.is_pgvector and chunk_ids:
        store = build_vector_store(settings=settings, session_factory=SessionLocal)
        store.delete(chunk_ids)
