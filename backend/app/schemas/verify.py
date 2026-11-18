import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.certificates import CertificateOut
from app.services.normalize import normalize_id


class VerifyByIdRequest(BaseModel):
    cert_number: str = Field(min_length=1, max_length=64, examples=["NBIT2024CS0001"])

    @field_validator("cert_number")
    @classmethod
    def _id(cls, v: str) -> str:
        out = normalize_id(v)
        if not out:
            raise ValueError("must contain at least one letter or digit")
        return out


class VerifyByQrRequest(BaseModel):
    payload: str = Field(
        min_length=1,
        max_length=1024,
        description="The text decoded from the QR code.",
        examples=["AVA1|NBIT2024CS0001|NBIT|<base64url signature>"],
    )


class UploadAccepted(BaseModel):
    """What `POST /verify/upload` returns: the job to poll, not a result."""

    job_id: str = Field(description="Poll GET /verify/jobs/{job_id} for the outcome.")
    upload_id: uuid.UUID


class JobStatusOut(BaseModel):
    status: str = Field(description="queued | running | done | failed")
    verification_id: uuid.UUID | None = Field(
        default=None, description="Set once status is done; fetch GET /verifications/{id}."
    )
    error: str | None = Field(
        default=None, description="Why the job failed, when it did. Never a verdict."
    )


class CheckOut(BaseModel):
    """One piece of evidence. `status` is pass | fail | skipped | uncertain."""

    name: str
    status: str
    detail: str


class VerifierSummary(BaseModel):
    """Who ran the verification. Shown on the result page and nowhere else."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str


class ReviewSummary(BaseModel):
    """A request made about this verification, as the result page shows it.

    Defined here rather than imported from `schemas.reviews` because that
    module imports `VerificationOut` — the dependency runs one way only.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str = Field(description="pending | needs_info | closed")
    decision: str | None = Field(
        default=None, description="confirmed | confirmed_added | not_issued"
    )
    decision_note: str | None = None
    institution_name: str
    institution_code: str
    created_at: datetime
    decided_at: datetime | None = None


class VerificationListItem(BaseModel):
    """A row in a verifier's history — no checks, no record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    method: str
    result: str
    cert_number: str | None
    created_at: datetime


class VerificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    method: str
    result: str = Field(description="VERIFIED | MISMATCH | REVOKED | MANUAL_REVIEW")
    checks: list[CheckOut]
    certificate: CertificateOut | None = Field(
        default=None, description="The registry record, when one was found."
    )
    extracted_fields: dict[str, Any] | None = Field(
        default=None, description="What the request itself carried (number, QR fields)."
    )
    verifier: VerifierSummary | None = None
    reviews: list[ReviewSummary] = Field(
        default_factory=list,
        description="Requests sent to the issuing institution about this result, newest first.",
    )
    created_at: datetime
