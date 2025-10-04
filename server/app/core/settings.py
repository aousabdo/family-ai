"""Application settings and configuration management."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT.parent / ".env"
load_dotenv(ENV_FILE)

VectorBackend = Literal["pgvector", "chroma"]


class Settings(BaseSettings):
    """Strongly-typed application settings."""

    model_config = SettingsConfigDict(env_file=str(ENV_FILE), env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Family AI Companion"
    environment: Literal["development", "staging", "production"] = Field(default="development", alias="ENVIRONMENT")
    debug: bool = False

    openai_api_key: str = Field(default="", description="OpenAI API key for chat + embeddings")
    chat_model: str = Field(default="gpt-4o-mini", description="Primary chat completion model")
    embedding_model: str = Field(default="text-embedding-3-large", description="Embedding model name")

    vector_backend: VectorBackend = Field(default="pgvector", alias="VECTOR_BACKEND")
    database_url: str = Field(
        default="postgresql+psycopg://user:pass@db:5432/familyai",
        alias="DATABASE_URL",
    )
    chroma_persist_dir: str = Field(default="/data/chroma", alias="CHROMA_PERSIST_DIR")

    jwt_secret: str = Field(default="change-me", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256")
    jwt_exp_minutes: int = Field(default=60 * 24)

    cors_origins: str | list[str] = Field(default="*", alias="CORS_ORIGINS")
    allowed_hosts: str | list[str] = Field(default="*", alias="ALLOWED_HOSTS")

    s3_bucket_corpus: str = Field(default="", alias="S3_BUCKET_CORPUS")
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    aws_access_key_id: str = Field(default="", alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(default="", alias="AWS_SECRET_ACCESS_KEY")

    sqlalchemy_echo: bool = Field(default=False)

    max_context_docs: int = Field(default=6)
    max_response_words: int = Field(default=300)

    default_daily_tips: dict[str, list[str]] = Field(
        default={
            "0-2": [
                "خصص وقتاً يومياً لقراءة قصة قصيرة باللغة العربية لطفلك." ,
                "استخدم كلمات بسيطة ومحببة أثناء اللعب لتشجيع طفلك على التعبير."
            ],
            "3-5": [
                "شجع طفلك على رواية ما حدث في روضته مستخدماً جملاً كاملة.",
                "ابتكر ألعاب أدوار مع طفلك لتطوير تعبيره العاطفي باللغة العربية."
            ],
            "6-9": [
                "قم بطرح أسئلة مفتوحة بعد المدرسة لتحفيز التفكير النقدي.",
                "حدد وقتاً أسبوعياً للحديث عن المشاعر وكيفية التعبير عنها باحترام." 
            ],
        }
    )

    model_config = SettingsConfigDict(populate_by_name=True)

    @property
    def cors_origin_list(self) -> list[str]:
        return _split_str_setting(self.cors_origins)

    @property
    def allowed_host_list(self) -> list[str]:
        return _split_str_setting(self.allowed_hosts)

    @property
    def is_pgvector(self) -> bool:
        return self.vector_backend.lower() == "pgvector"


def _split_str_setting(value: str | list[str]) -> list[str]:
    if isinstance(value, list):
        return value
    if value == "*":
        return ["*"]
    return [item.strip() for item in value.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""

    return Settings()
