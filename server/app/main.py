"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, profile, tips, upload
from app.core.safety import SafetyChecker
from app.core.settings import Settings, get_settings
from app.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    app.state.safety_checker = SafetyChecker()
    yield


def create_app() -> FastAPI:
    settings: Settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat.router, prefix="/api", tags=["chat"])
    app.include_router(profile.router, prefix="/api", tags=["profile"])
    app.include_router(tips.router, prefix="/api", tags=["tips"])
    app.include_router(upload.router, prefix="/api", tags=["admin"])

    @app.get("/healthz", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
