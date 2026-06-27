from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class AuthRecordCreate(BaseModel):
    mode: str = Field(pattern="^(login|register)$")
    email: EmailStr
    password: str = Field(min_length=8)
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    rememberMe: Optional[bool] = None
    agreeToTerms: Optional[bool] = None
    source: str = "web-auth-page"


class AuthRecordResponse(BaseModel):
    insertedId: str
    createdAt: datetime
    message: str


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class AuthVerifyRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern="^[0-9]{6}$")