from datetime import datetime, timezone
from typing import Annotated

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field


class AuthRecordCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    mode: str = Field(pattern="^(login|register)$")
    email: EmailStr
    password: str = Field(min_length=8)
    first_name: Annotated[
        str | None,
        Field(
            default=None,
            validation_alias=AliasChoices("firstName", "first_name"),
            serialization_alias="firstName",
        ),
    ] = None
    last_name: Annotated[
        str | None,
        Field(
            default=None,
            validation_alias=AliasChoices("lastName", "last_name"),
            serialization_alias="lastName",
        ),
    ] = None
    remember_me: Annotated[
        bool | None,
        Field(
            default=None,
            validation_alias=AliasChoices("rememberMe", "remember_me"),
            serialization_alias="rememberMe",
        ),
    ] = None
    agree_to_terms: Annotated[
        bool | None,
        Field(
            default=None,
            validation_alias=AliasChoices("agreeToTerms", "agree_to_terms"),
            serialization_alias="agreeToTerms",
        ),
    ] = None
    source: str = Field(default="web-auth-page")


class AuthRecordResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    inserted_id: Annotated[str, Field(serialization_alias="insertedId")]
    created_at: Annotated[datetime, Field(serialization_alias="createdAt")]
    message: str


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class AuthVerifyRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern="^[0-9]{6}$")