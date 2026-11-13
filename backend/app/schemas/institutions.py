from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.auth import UserOut
from app.services.normalize import clean_text, normalize_id


class InstitutionCreate(BaseModel):
    name: str = Field(
        min_length=1, max_length=255, examples=["Northbridge Institute of Technology"]
    )
    code: str = Field(min_length=2, max_length=32, examples=["NBIT"])
    admin_email: str = Field(
        min_length=3,
        max_length=255,
        description="Email of the institution's first user.",
        examples=["registrar@nbit.test"],
    )

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        out = clean_text(v)
        if not out:
            raise ValueError("must not be blank")
        return out

    @field_validator("code")
    @classmethod
    def _code(cls, v: str) -> str:
        out = normalize_id(v)
        if not out:
            raise ValueError("must contain at least one letter or digit")
        return out

    @field_validator("admin_email")
    @classmethod
    def _email(cls, v: str) -> str:
        out = v.strip().lower()
        if "@" not in out or out.startswith("@") or out.endswith("@"):
            raise ValueError("must be an email address")
        return out


class InstitutionUpdate(BaseModel):
    """Only the display name and the active flag can change. The code and the
    key are fixed: signatures already issued refer to them."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        out = clean_text(v)
        if not out:
            raise ValueError("must not be blank")
        return out


class InstitutionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    is_active: bool
    public_key: str
    certificate_count: int = 0
    user_count: int = 0
    created_at: datetime


class InstitutionCreated(BaseModel):
    """The one and only time the generated password is returned."""

    institution: InstitutionOut
    user: UserOut
    password: str = Field(description="Shown once. It is not stored in plain text anywhere.")
