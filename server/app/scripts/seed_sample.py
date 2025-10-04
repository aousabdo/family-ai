"""Seed the knowledge base with sample corpus files."""
from __future__ import annotations

import asyncio
from pathlib import Path

from app.core.openai_client import OpenAIClient
from app.core.settings import get_settings
from app.db.session import SessionLocal
from app.rag.ingest import ingest_text

SCRIPT_PATH = Path(__file__).resolve()
ROOT_DIR = SCRIPT_PATH.parents[2]
SAMPLE_DIR_CANDIDATES = [
    ROOT_DIR / "sample_corpus",
    ROOT_DIR / "../sample_corpus",
    Path("/app/sample_corpus"),
]


def resolve_sample_dir() -> Path:
    for candidate in SAMPLE_DIR_CANDIDATES:
        path = candidate.resolve()
        if path.exists() and path.is_dir():
            return path
    return SAMPLE_DIR_CANDIDATES[0].resolve()


SAMPLE_DIR = resolve_sample_dir()


def parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    meta_block, body = parts[1], parts[2]
    metadata: dict[str, str] = {}
    for line in meta_block.strip().splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()
    return metadata, body.strip()


def load_samples() -> list[tuple[str, dict[str, str], str]]:
    items = []
    for file_path in SAMPLE_DIR.glob("*.md"):
        content = file_path.read_text(encoding="utf-8")
        metadata, body = parse_frontmatter(content)
        items.append((file_path.name, metadata, body))
    return items


async def main() -> None:
    settings = get_settings()
    openai_client = OpenAIClient(settings)
    session_factory = SessionLocal

    samples = load_samples()
    if not samples:
        print("No sample corpus files found.")
        return
    for file_name, metadata, body in samples:
        print(f"Ingesting {file_name} ...", flush=True)
        result = await ingest_text(
            text=body,
            file_name=file_name,
            metadata_overrides=metadata,
            session_factory=session_factory,
            settings=settings,
            openai_client=openai_client,
        )
        print(f" -> stored {result.stored_chunks} chunks with document {result.document_id}")


if __name__ == "__main__":
    asyncio.run(main())
