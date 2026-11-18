"""The OCR job itself, against a real issued PDF.

No Redis: the job function is called directly, which is what RQ does with it.
The job opens its own session through `SessionLocal`; that name is patched to
hand back the test session, so these tests stay inside the rolled-back
transaction and the `<db>_test` database like every other test.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import AuditLog, Certificate, Institution, Role, User, Verification
from app.schemas.certificates import CertificateCreate
from app.services import certificates as cert_service
from app.services import uploads
from app.services.hashing import sha256_file
from app.services.pdf_issue import issued_pdf_path
from app.workers import ocr_job
from app.workers.ocr_job import verify_upload_job
from tests.conftest import make_institution


@pytest.fixture(autouse=True)
def upload_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from app.core.config import settings

    path = tmp_path / "uploads"
    monkeypatch.setattr(settings, "upload_dir", str(path))
    return path


@pytest.fixture(autouse=True)
def job_session(db: Session, monkeypatch: pytest.MonkeyPatch) -> Session:
    """Make the job use the test session instead of a real connection.

    `close()` is neutralised: the job closes the session it is given, and the
    `db` fixture still needs it to roll the transaction back afterwards.
    """
    monkeypatch.setattr(db, "close", lambda: None)
    monkeypatch.setattr(ocr_job, "SessionLocal", lambda: db)
    return db


@pytest.fixture
def institution(db: Session) -> Institution:
    return make_institution(db, "JOB", "Job Test Institute (fictional)")


@pytest.fixture
def verifier(db: Session) -> User:
    user = User(email="job-verifier@t.test", role=Role.VERIFIER.value, password_hash="x")
    db.add(user)
    db.flush()
    return user


def issue(db: Session, institution: Institution, **overrides: object) -> Certificate:
    """An issued certificate with its PDF on disk, through the real service."""
    issuer = User(
        email="job-issuer@t.test",
        role=Role.INSTITUTION.value,
        institution_id=institution.id,
        password_hash="x",
    )
    db.add(issuer)
    db.flush()

    body: dict[str, object] = {
        "cert_number": "JOB2024CS0001",
        "student_name": "Aarav Sharma",
        "roll_number": "21CS901",
        "programme": "B.Tech Computer Science",
        "year_of_passing": 2024,
        "cgpa": Decimal("8.50"),
        "marks": None,
        "issue_date": date(2024, 7, 15),
    }
    body.update(overrides)
    return cert_service.create_certificate(db, issuer, CertificateCreate(**body))


def test_job_verifies_an_untouched_issued_pdf_by_its_hash(
    db: Session, institution: Institution, verifier: User
) -> None:
    cert = issue(db, institution)
    pdf_path = issued_pdf_path(cert.id)
    assert cert.file_sha256 == sha256_file(pdf_path)

    upload = uploads.store(db, Path(pdf_path).read_bytes())
    db.flush()

    verification_id = verify_upload_job(str(upload.id), verifier.id)

    verification = db.get(Verification, uuid.UUID(verification_id))
    assert verification is not None
    assert verification.method == "upload"
    assert verification.result == "VERIFIED"
    assert verification.certificate_id == cert.id
    assert verification.extracted_fields["file_sha256"] == cert.file_sha256
    assert verification.verifier_id == verifier.id


def test_job_sends_an_unknown_document_to_manual_review(db: Session, verifier: User) -> None:
    """A PDF matching nothing in the registry is not an accusation."""
    upload = uploads.store(db, b"%PDF-1.7 not one of ours")
    db.flush()

    verification_id = verify_upload_job(str(upload.id), verifier.id)

    verification = db.get(Verification, uuid.UUID(verification_id))
    assert verification is not None
    assert verification.result == "MANUAL_REVIEW"
    assert verification.certificate_id is None


def test_job_result_never_accuses(db: Session, verifier: User) -> None:
    upload = uploads.store(db, b"%PDF-1.7 unknown")
    db.flush()
    verification_id = verify_upload_job(str(upload.id), verifier.id)

    verification = db.get(Verification, uuid.UUID(verification_id))
    assert verification is not None
    text = " ".join(c["detail"] for c in verification.checks).lower()
    for word in ("fake", "forged", "fraud"):
        assert word not in text


def test_job_writes_an_audit_row(db: Session, verifier: User) -> None:
    upload = uploads.store(db, b"%PDF-1.7 unknown")
    db.flush()

    verification_id = verify_upload_job(str(upload.id), verifier.id)

    row = db.scalar(
        select(AuditLog).where(
            AuditLog.action == "verification.create", AuditLog.entity_id == verification_id
        )
    )
    assert row is not None
    assert row.meta["method"] == "upload"
    assert row.meta["upload_id"] == str(upload.id)
    # The document's bytes are never in the audit trail.
    assert "text" not in row.meta


def test_job_fails_loudly_when_the_upload_is_gone(db: Session, verifier: User) -> None:
    """RQ marks the job failed; the API reports that, not a verdict."""
    with pytest.raises(AppError) as exc:
        verify_upload_job(str(uuid.uuid4()), verifier.id)
    assert exc.value.code == "upload_not_found"


def test_job_fails_loudly_when_the_verifier_is_gone(db: Session) -> None:
    upload = uploads.store(db, b"%PDF-1.7 x")
    db.flush()

    with pytest.raises(AppError):
        verify_upload_job(str(upload.id), 10**9)


def test_job_verifies_a_revoked_certificate_as_revoked(
    db: Session, institution: Institution, verifier: User
) -> None:
    """Rule 1 still wins on the upload path: a genuine PDF of a revoked
    certificate is REVOKED, not VERIFIED."""
    cert = issue(db, institution)
    pdf = Path(issued_pdf_path(cert.id)).read_bytes()

    issuer = db.scalar(select(User).where(User.email == "job-issuer@t.test"))
    assert issuer is not None
    cert_service.revoke_certificate(db, issuer, cert.id, reason="Issued in error (test)")

    upload = uploads.store(db, pdf)
    db.flush()

    verification_id = verify_upload_job(str(upload.id), verifier.id)
    verification = db.get(Verification, uuid.UUID(verification_id))
    assert verification is not None
    assert verification.result == "REVOKED"
