"""Request/response models for verification requests (review cases)."""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.certificates import CertificateFields, CertificateOut
from app.schemas.verify import VerificationOut

MAX_NOTE = 2000


class ReviewCreate(BaseModel):
    """What a verifier sends to open a request."""

    verification_id: uuid.UUID
    institution_id: int | None = Field(
        default=None,
        description=(
            "Required only when the document identified no institution; ignored when it did, "
            "because a known certificate is always sent to its own issuer."
        ),
    )
    note: str | None = Field(default=None, max_length=MAX_NOTE)


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=MAX_NOTE)

    @field_validator("body")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v.strip()


class ConfirmDecision(BaseModel):
    """`Confirm genuine`. A note is optional — the decision speaks for itself."""

    decision: Literal["confirmed"]
    note: str | None = Field(default=None, max_length=MAX_NOTE)


class ConfirmAndAddDecision(BaseModel):
    """`Confirm & add to registry`: the certificate to create, as the
    institution edited it. Validated exactly like a direct create, because it
    *is* one — same service, same signature, same issued PDF."""

    decision: Literal["confirmed_added"]
    certificate: CertificateFields


class NotIssuedDecision(BaseModel):
    """`Not issued by us`. The reason is required, not decorative: this is the
    one answer a holder can be harmed by."""

    decision: Literal["not_issued"]
    reason: str = Field(min_length=1, max_length=MAX_NOTE)

    @field_validator("reason")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v.strip()


DecisionRequest = Annotated[
    ConfirmDecision | ConfirmAndAddDecision | NotIssuedDecision,
    Field(discriminator="decision"),
]


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str


class InstitutionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    body: str
    author: UserSummary
    created_at: datetime


class ReviewListItem(BaseModel):
    """A row in either inbox: enough to triage, no thread, no document."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    verification_id: uuid.UUID
    cert_number: str | None
    result: str = Field(description="The result that prompted the request.")
    institution: InstitutionSummary
    requester: UserSummary
    status: str = Field(description="pending | needs_info | closed")
    decision: str | None = Field(
        default=None, description="confirmed | confirmed_added | not_issued"
    )
    created_at: datetime
    updated_at: datetime


class ReviewOut(BaseModel):
    """One case in full: the thread, the verification behind it, and — for the
    institution — its own matching record and a prefilled draft."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    verification_id: uuid.UUID
    cert_number: str | None
    institution: InstitutionSummary
    requester: UserSummary
    status: str
    note: str | None
    decision: str | None
    decision_note: str | None
    decider: UserSummary | None = None
    decided_at: datetime | None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut] = []
    verification: VerificationOut | None = None
    registry_match: CertificateOut | None = Field(
        default=None, description="The institution's own record for this document, if it has one."
    )
    prefill: dict[str, str] = Field(
        default_factory=dict,
        description="A draft for 'confirm & add', from what the document said. Editable.",
    )
    document_available: bool = Field(
        default=False, description="Whether the uploaded file can still be fetched."
    )
    can_decide: bool = Field(
        default=False, description="True for the institution asked, while the case is open."
    )
    can_reply: bool = Field(default=False)


class ReviewCounts(BaseModel):
    open: int = 0
    open_over_7_days: int = 0
