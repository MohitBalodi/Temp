import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.auth import InstitutionSummary
from app.services.normalize import clean_text, normalize_decimal, normalize_id

MIN_YEAR = 1950


class CertificateFields(BaseModel):
    """Fields an institution supplies for a certificate. Values come out
    normalized: IDs in normalized form, text with whitespace collapsed,
    grades rounded to two decimals."""

    cert_number: str = Field(min_length=1, max_length=64, examples=["NBIT2024CS0001"])
    student_name: str = Field(min_length=1, max_length=255)
    roll_number: str = Field(min_length=1, max_length=64)
    programme: str = Field(min_length=1, max_length=255)
    year_of_passing: int
    cgpa: Decimal | None = Field(default=None, ge=0, le=10, description="0–10 scale")
    marks: Decimal | None = Field(default=None, ge=0, le=100, description="Percentage, 0–100")
    issue_date: date = Field(description="YYYY-MM-DD")

    @field_validator("cgpa", "marks", mode="before")
    @classmethod
    def _blank_is_none(cls, v: Any) -> Any:
        return None if isinstance(v, str) and not v.strip() else v

    @field_validator("cert_number", "roll_number")
    @classmethod
    def _id(cls, v: str) -> str:
        out = normalize_id(v)
        if not out:
            raise ValueError("must contain at least one letter or digit")
        return out

    @field_validator("student_name", "programme")
    @classmethod
    def _text(cls, v: str) -> str:
        out = clean_text(v)
        if not out:
            raise ValueError("must not be blank")
        return out

    @field_validator("cgpa", "marks")
    @classmethod
    def _grade(cls, v: Decimal | None) -> Decimal | None:
        return normalize_decimal(v)

    @model_validator(mode="after")
    def _cross_field(self) -> Self:
        this_year = datetime.now(UTC).year
        if not MIN_YEAR <= self.year_of_passing <= this_year:
            raise ValueError(f"year_of_passing must be between {MIN_YEAR} and {this_year}")
        if self.cgpa is None and self.marks is None:
            raise ValueError("at least one of cgpa or marks is required")
        if self.issue_date > datetime.now(UTC).date():
            raise ValueError("issue_date cannot be in the future")
        if self.issue_date.year < self.year_of_passing:
            raise ValueError("issue_date cannot be before the year of passing")
        return self


class CertificateCreate(CertificateFields):
    """POST /certificates. The institution is taken from the logged-in user."""


class CertificateImportRow(CertificateFields):
    """One CSV row for POST /certificates/import."""

    institution_code: str = Field(min_length=1, max_length=32)

    @field_validator("institution_code")
    @classmethod
    def _code(cls, v: str) -> str:
        return normalize_id(v)


# Exact header for the import CSV (order-insensitive), from the project spec.
CSV_COLUMNS = (
    "cert_number",
    "institution_code",
    "student_name",
    "roll_number",
    "programme",
    "year_of_passing",
    "cgpa",
    "marks",
    "issue_date",
)


class CertificateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cert_number: str
    institution: InstitutionSummary
    student_name: str
    roll_number: str
    programme: str
    year_of_passing: int
    cgpa: Decimal | None
    marks: Decimal | None
    issue_date: date
    status: str
    revoked_at: datetime | None
    file_sha256: str | None
    signature: str
    created_at: datetime


class RevokeRequest(BaseModel):
    """Revocation always carries a reason: the audit trail should say why."""

    reason: str = Field(
        min_length=3,
        max_length=500,
        examples=["Issued in error — duplicate record"],
    )

    @field_validator("reason")
    @classmethod
    def _reason(cls, v: str) -> str:
        out = clean_text(v)
        if len(out) < 3:
            raise ValueError("must say why the certificate is being revoked")
        return out


class ImportResult(BaseModel):
    imported: int


class ImportRowError(BaseModel):
    row: int = Field(description="Line number in the CSV file (header is line 1).")
    field: str | None = Field(description="Column name, or null for whole-row problems.")
    message: str


class ImportErrorBody(BaseModel):
    code: str
    message: str
    rows: list[ImportRowError] = []


class ImportErrorResponse(BaseModel):
    error: ImportErrorBody
