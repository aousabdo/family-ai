"""Database ORM models."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Household(Base, TimestampMixin):
    __tablename__ = "households"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255))
    country: Mapped[str] = mapped_column(String(5), default="JO")
    language_preference: Mapped[str] = mapped_column(String(16), default="ar")
    timezone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    parents: Mapped[list["ParentUser"]] = relationship("ParentUser", back_populates="household", cascade="all,delete-orphan")
    children: Mapped[list["Child"]] = relationship("Child", back_populates="household", cascade="all,delete-orphan")


class ParentUser(Base, TimestampMixin):
    __tablename__ = "parent_users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    household: Mapped[Household] = relationship("Household", back_populates="parents")


class Child(Base, TimestampMixin):
    __tablename__ = "children"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    age: Mapped[int] = mapped_column(Integer)
    favorite_topics: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    household: Mapped[Household] = relationship("Household", back_populates="children")


class DocumentMeta(Base, TimestampMixin):
    __tablename__ = "document_chunks"

    chunk_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(64), index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    topic: Mapped[str] = mapped_column(String(64), default="general", index=True)
    age_range: Mapped[str] = mapped_column(String(32), default="all", index=True)
    tone: Mapped[str] = mapped_column(String(32), default="supportive")
    country: Mapped[str] = mapped_column(String(8), default="jo")
    language: Mapped[str] = mapped_column(String(8), default="ar")
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = Column(Vector(3072))


class ChatLog(Base, TimestampMixin):
    __tablename__ = "chat_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    household_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    persona: Mapped[str] = mapped_column(String(16), default="neutral")
    language: Mapped[str] = mapped_column(String(16), default="msa")
    user_message: Mapped[str] = mapped_column(Text)
    assistant_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    needs_human: Mapped[bool] = mapped_column(Boolean, default=False)
    safety_reasons: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    context_snippets: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)


class DocumentRegistry(Base, TimestampMixin):
    __tablename__ = "document_registry"

    document_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    file_name: Mapped[str] = mapped_column(String(255))
    topic: Mapped[str] = mapped_column(String(64), default="general", index=True)
    age_range: Mapped[str] = mapped_column(String(32), default="all", index=True)
    tone: Mapped[str] = mapped_column(String(32), default="supportive")
    country: Mapped[str] = mapped_column(String(8), default="jo")
    language: Mapped[str] = mapped_column(String(8), default="ar")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    s3_uploaded: Mapped[bool] = mapped_column(Boolean, default=False)


# --- Chat memory (per-thread) ---


class ChatTurn(Base):
    __tablename__ = "chat_turns"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    thread_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class ChatThread(Base):
    __tablename__ = "chat_threads"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    browser_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    household_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("households.id"), nullable=True, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    persona: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    lang: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class HouseholdAuth(Base):
    __tablename__ = "household_auth"

    household_id: Mapped[str] = mapped_column(String(64), ForeignKey("households.id"), primary_key=True)
    secret_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
