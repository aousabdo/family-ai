"""Endpoints serving daily parenting tips."""
from __future__ import annotations

import random

from fastapi import APIRouter, Depends, Query

from app.core.settings import Settings, get_settings

router = APIRouter()


@router.get("/tips")
async def get_tips(
    age_range: str = Query(default="all", description="Age band, e.g. 0-2"),
    limit: int = Query(default=3, ge=1, le=5),
    settings: Settings = Depends(get_settings),
):
    bucket = settings.default_daily_tips.get(age_range) or settings.default_daily_tips.get("all", [])
    tips = bucket[:]
    random.shuffle(tips)
    return {"age_range": age_range, "tips": tips[:limit]}
