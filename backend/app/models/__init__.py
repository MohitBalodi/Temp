"""SQLAlchemy models. Import every model module here so Alembic autogenerate
sees them on `Base.metadata`."""

from app.core.db import Base
from app.models.audit import AuditLog
from app.models.certificate import Certificate, CertificateStatus
from app.models.institution import Institution
from app.models.review import ReviewCase, ReviewDecision, ReviewMessage, ReviewStatus
from app.models.upload import Upload
from app.models.user import Role, User
from app.models.verification import (
    Verification,
    VerificationMethod,
    VerificationResult,
)

__all__ = [
    "AuditLog",
    "Base",
    "Certificate",
    "CertificateStatus",
    "Institution",
    "ReviewCase",
    "ReviewDecision",
    "ReviewMessage",
    "ReviewStatus",
    "Role",
    "Upload",
    "User",
    "Verification",
    "VerificationMethod",
    "VerificationResult",
]
