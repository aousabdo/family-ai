"""CRUD helpers for application data."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.db import models


def get_chunk_ids_by_document(session: Session, document_id: str) -> list[str]:
    stmt = select(models.DocumentMeta.chunk_id).where(models.DocumentMeta.document_id == document_id)
    return [row[0] for row in session.execute(stmt).all()]


def delete_document_metadata(session: Session, document_id: str) -> int:
    stmt = select(models.DocumentMeta).where(models.DocumentMeta.document_id == document_id)
    rows = session.scalars(stmt).all()
    deleted = len(rows)
    for row in rows:
        session.delete(row)
    return deleted


def upsert_document_registry(
    session: Session,
    *,
    document_id: str,
    file_name: str,
    metadata: dict[str, str],
    chunk_count: int,
    s3_uploaded: bool,
) -> models.DocumentRegistry:
    registry = session.get(models.DocumentRegistry, document_id)
    if registry is None:
        registry = models.DocumentRegistry(document_id=document_id, file_name=file_name)
        session.add(registry)

    registry.file_name = file_name
    registry.topic = metadata.get("topic", registry.topic)
    registry.age_range = metadata.get("age_range", registry.age_range)
    registry.tone = metadata.get("tone", registry.tone)
    registry.country = metadata.get("country", registry.country)
    registry.language = metadata.get("language", registry.language)
    registry.chunk_count = chunk_count
    registry.s3_uploaded = s3_uploaded or registry.s3_uploaded
    session.flush()
    return registry


def list_documents(session: Session) -> list[models.DocumentRegistry]:
    stmt = select(models.DocumentRegistry).order_by(models.DocumentRegistry.updated_at.desc())
    return session.scalars(stmt).all()


def delete_document_registry(session: Session, document_id: str) -> None:
    registry = session.get(models.DocumentRegistry, document_id)
    if registry:
        session.delete(registry)


def get_household(session: Session, household_id: str) -> Optional[models.Household]:
    return session.get(models.Household, household_id)


def get_household_by_email(session: Session, email: str) -> Optional[models.Household]:
    stmt = (
        select(models.Household)
        .join(models.ParentUser)
        .where(models.ParentUser.email == email)
    )
    return session.scalars(stmt).first()


def upsert_household(session: Session, *, name: str, country: str, language_preference: str) -> models.Household:
    household = models.Household(name=name, country=country, language_preference=language_preference)
    session.add(household)
    session.flush()
    return household


def create_parent_user(
    session: Session,
    *,
    household: models.Household,
    email: str,
    password: str,
    is_admin: bool = False,
) -> models.ParentUser:
    parent = models.ParentUser(
        household_id=household.id,
        email=email,
        password_hash=get_password_hash(password),
        is_admin=is_admin,
    )
    session.add(parent)
    session.flush()
    return parent


def upsert_child(
    session: Session,
    *,
    household_id: str,
    name: str,
    age: int,
    favorite_topics: Optional[str],
) -> models.Child:
    child = models.Child(household_id=household_id, name=name, age=age, favorite_topics=favorite_topics)
    session.add(child)
    session.flush()
    return child


def record_chat_log(
    session: Session,
    *,
    household_id: Optional[str],
    persona: str,
    language: str,
    user_message: str,
    assistant_message: str,
    needs_human: bool,
    safety_reasons: list[str],
    context_snippets: list[str],
) -> models.ChatLog:
    log = models.ChatLog(
        household_id=household_id,
        persona=persona,
        language=language,
        user_message=user_message,
        assistant_message=assistant_message,
        needs_human=needs_human,
        safety_reasons=safety_reasons or None,
        context_snippets=context_snippets or None,
    )
    session.add(log)
    session.flush()
    return log
