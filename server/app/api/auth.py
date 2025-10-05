"""Authentication endpoints for household access."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.security import create_access_token
from app.core.settings import get_settings
from app.db import crud
from app.db.session import session_scope

router = APIRouter(prefix="/auth", tags=["auth"])


class HouseholdLoginIn(BaseModel):
    household_id: str
    secret: str


class HouseholdLoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/household/login", response_model=HouseholdLoginOut)
async def household_login(payload: HouseholdLoginIn) -> HouseholdLoginOut:
    settings = get_settings()
    with session_scope() as session:
        if not crud.verify_household_secret(session, payload.household_id, payload.secret):
            raise HTTPException(status_code=401, detail="invalid credentials")
        token = create_access_token(
            subject=payload.household_id,
            settings=settings,
            additional_claims={"household_id": payload.household_id},
        )
    return HouseholdLoginOut(access_token=token)
