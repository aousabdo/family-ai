"""Family profile CRUD endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.security import create_access_token
from app.core.settings import Settings, get_settings
from app.db import crud
from app.db.session import session_scope

router = APIRouter()


class ChildPayload(BaseModel):
    name: str
    age: int = Field(ge=0)
    favorite_topics: Optional[str] = None


class ProfileCreatePayload(BaseModel):
    household_name: str
    country: str = "JO"
    language_preference: str = "ar"
    parent_email: str
    parent_password: str
    children: list[ChildPayload] = Field(default_factory=list)


class ProfileResponse(BaseModel):
    household_id: str
    admin_token: str | None = None


class ProfileUpdatePayload(BaseModel):
    household_name: Optional[str] = None
    language_preference: Optional[str] = None
    country: Optional[str] = None


@router.post("/profile", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(payload: ProfileCreatePayload, settings: Settings = Depends(get_settings)) -> ProfileResponse:
    with session_scope() as session:
        household = crud.upsert_household(
            session,
            name=payload.household_name,
            country=payload.country,
            language_preference=payload.language_preference,
        )
        parent = crud.create_parent_user(
            session,
            household=household,
            email=payload.parent_email,
            password=payload.parent_password,
            is_admin=True,
        )
        for child in payload.children:
            crud.upsert_child(
                session,
                household_id=household.id,
                name=child.name,
                age=child.age,
                favorite_topics=child.favorite_topics,
            )
        token = create_access_token(
            subject=parent.id,
            settings=settings,
            additional_claims={"email": parent.email, "household_id": household.id, "is_admin": True},
        )
        return ProfileResponse(household_id=household.id, admin_token=token)


@router.get("/profile/{household_id}")
async def get_profile(household_id: str):
    with session_scope() as session:
        household = crud.get_household(session, household_id)
        if not household:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Household not found")
        return {
            "household": {
                "id": household.id,
                "name": household.name,
                "country": household.country,
                "language_preference": household.language_preference,
            },
            "children": [
                {
                    "id": child.id,
                    "name": child.name,
                    "age": child.age,
                    "favorite_topics": child.favorite_topics,
                }
                for child in household.children
            ],
        }


@router.put("/profile/{household_id}")
async def update_profile(household_id: str, payload: ProfileUpdatePayload):
    with session_scope() as session:
        household = crud.get_household(session, household_id)
        if not household:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Household not found")
        if payload.household_name:
            household.name = payload.household_name
        if payload.language_preference:
            household.language_preference = payload.language_preference
        if payload.country:
            household.country = payload.country
        session.flush()
        return {"status": "updated"}
