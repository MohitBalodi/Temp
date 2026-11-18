"""End-to-end verification of real documents, through the real pipeline.

Every input is generated inside the test run from the project's own issuance
code (see tests/ocr_fixtures.py) — there is no separate test-certificate
generator, which CLAUDE.md puts out of scope.

These are the tests that would catch a regression anywhere between the bytes
and the verdict: preprocessing, OCR, the template, field normalization, the
record lookup and the decision rules. They run real Tesseract, so they are
slow; that is the point of them.

The contract under test, stated once:
  * a genuine document never resolves to MISMATCH, however badly degraded;
  * an altered document resolves to MISMATCH with the offending field named;
  * anything unreadable or unknown resolves to MANUAL_REVIEW, never MISMATCH.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Certificate, Institution, Role, User, Verification
from app.schemas.certificates import CertificateCreate
from app.services import certificates as cert_service
from app.services import uploads
from app.services.pdf_issue import issued_pdf_path
from app.workers import ocr_job
from app.workers.ocr_job import verify_upload_job
from tests.conftest import make_institution
from tests.ocr_fixtures import (
    cover_pdf_text,
    degrade,
    edit_pdf_text,
    noise_image,
    photo_of_certificate,
    render_png,
    to_jpeg,
)

CERT_NUMBER = "TST2024CS0042"
STUDENT = "Aarav Sharma"
ROLL = "21CS901"
PROGRAMME = "B.Tech Computer Science"
YEAR = 2024
CGPA = Decimal("8.50")
ISSUE_DATE = date(2024, 7, 15)


@pytest.fixture(autouse=True)
def upload_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "uploads"
    monkeypatch.setattr(settings, "upload_dir", str(path))
    return path


@pytest.fixture(autouse=True)
def job_session(db: Session, monkeypatch: pytest.MonkeyPatch) -> Session:
    """The job opens its own session; hand it the test one so everything stays
    inside the rolled-back transaction and the `<db>_test` database."""
    monkeypatch.setattr(db, "close", lambda: None)
    monkeypatch.setattr(ocr_job, "SessionLocal", lambda: db)
    return db


@pytest.fixture
def institution(db: Session) -> Institution:
    return make_institution(db, "TST", "Test Institute (fictional)")


@pytest.fixture
def verifier(db: Session) -> User:
    user = User(email="e2e-verifier@t.test", role=Role.VERIFIER.value, password_hash="x")
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def issued(db: Session, institution: Institution) -> tuple[Certificate, bytes]:
    """A certificate issued through the real service, with its stored PDF."""
    issuer = User(
        email="e2e-issuer@t.test",
        role=Role.INSTITUTION.value,
        institution_id=institution.id,
        password_hash="x",
    )
    db.add(issuer)
    db.flush()

    cert = cert_service.create_certificate(
        db,
        issuer,
        CertificateCreate(
            cert_number=CERT_NUMBER,
            student_name=STUDENT,
            roll_number=ROLL,
            programme=PROGRAMME,
            year_of_passing=YEAR,
            cgpa=CGPA,
            marks=None,
            issue_date=ISSUE_DATE,
        ),
    )
    db.flush()
    return cert, Path(issued_pdf_path(cert.id)).read_bytes()


def verify(db: Session, verifier: User, data: bytes) -> Verification:
    """Store `data` as an upload and run the real job over it."""
    upload = uploads.store(db, data)
    db.flush()
    verification_id = verify_upload_job(str(upload.id), verifier.id)
    stored = db.get(Verification, uuid.UUID(verification_id))
    assert stored is not None
    return stored


def checks(verification: Verification) -> dict[str, str]:
    return {c["name"]: c["status"] for c in verification.checks}


def details(verification: Verification) -> str:
    return " ".join(c["detail"] for c in verification.checks)


# --- 1. an untouched issued PDF ----------------------------------------------


def test_untouched_issued_pdf_verifies_by_file_hash(
    db: Session, verifier: User, issued: tuple[Certificate, bytes]
) -> None:
    cert, pdf = issued
    result = verify(db, verifier, pdf)

    assert result.result == "VERIFIED"
    assert result.certificate_id == cert.id
    assert checks(result)["file_hash"] == "pass"
    assert result.extracted_fields["file_sha256"] == cert.file_sha256
    assert result.extracted_fields["text_source"] == "pdf_text_layer"


def test_untouched_issued_pdf_also_matches_every_field(
    db: Session, verifier: User, issued: tuple[Certificate, bytes]
) -> None:
    """The hash decides it, but the field comparison must agree independently."""
    _, pdf = issued
    result = verify(db, verifier, pdf)

    field_checks = {k: v for k, v in checks(result).items() if k.startswith("field_match.")}
    assert field_checks
    assert all(status == "pass" for status in field_checks.values()), field_checks


# --- 2. the same certificate rendered to an image ----------------------------


def test_rendered_png_verifies_through_the_qr_and_fields(
    db: Session, verifier: User, issued: tuple[Certificate, bytes]
) -> None:
    """A screenshot or scan: different bytes, so the hash cannot help. The
    signed QR and the printed fields carry it instead."""
    cert, pdf = issued
    result = verify(db, verifier, render_png(pdf))

    assert result.result == "VERIFIED"
    assert result.certificate_id == cert.id
    assert checks(result)["file_hash"] == "uncertain", "a render is not the original bytes"
    assert checks(result)["qr_signature"] == "pass"
    assert result.extracted_fields["text_source"] == "ocr"
    assert result.extracted_fields["template"] == "nbit"


def test_rendered_jpeg_verifies_too(
    db: Session, verifier: User, issued: tuple[Certificate, bytes]
) -> None:
    _, pdf = issued
    result = verify(db, verifier, to_jpeg(render_png(pdf)))
    assert result.result == "VERIFIED"


def test_a_photographed_page_verifies(
    db: Session, verifier: User, issued: tuple[Certificate, bytes]
) -> None:
    """Photographed on a desk, so the page has an outline to crop to."""
    _, pdf = issued
    result = verify(db, verifier, photo_of_certificate(render_png(pdf)))
    assert result.result == "VERIFIED"


# --- 3. a degraded image: never MISMATCH -------------------------------------


@pytest.mark.parametrize(
    ("label", "kwargs"),
    [
        ("rotated 5 degrees", {"degrees": 5.0, "blur": 0, "jpeg_quality": 95}),
        ("blurred", {"degrees": 0.0, "blur": 5, "jpeg_quality": 95}),
        ("heavily compressed", {"degrees": 0.0, "blur": 0, "jpeg_quality": 25}),
        ("rotated, blurred and compressed", {"degrees": 5.0, "blur": 3, "jpeg_quality": 60}),
        ("rotated the other way", {"degrees": -5.0, "blur": 3, "jpeg_quality": 60}),
    ],
)
def test_a_degraded_genuine_document_is_never_a_mismatch(
    db: Session,
    verifier: User,
    issued: tuple[Certificate, bytes],
    label: str,
    kwargs: dict[str, float | int],
) -> None:
    """The headline safety property: degrading a genuine document may cost
    certainty, but it must never produce an accusation."""
    _, pdf = issued
    result = verify(db, verifier, degrade(render_png(pdf), **kwargs))

    assert result.result in {"VERIFIED", "MANUAL_REVIEW"}, f"{label} gave {result.result}"
    assert result.result != "MISMATCH"


def test_the_usual_degraded_scan_still_verifies(
    db: Session, verifier: User, issued: tuple[Certificate, bytes]
) -> None:
    """Not just "not a mismatch": the common case should still verify, because
    the QR survives this much degradation."""
    _, pdf = issued
    result = verify(db, verifier, degrade(render_png(pdf)))
    assert result.result == "VERIFIED"
    assert checks(result)["qr_signature"] == "pass"


# --- 4. an edited PDF: MISMATCH, with the field named ------------------------


def test_an_edited_cgpa_is_a_mismatch_naming_the_field(
    db: Session, verifier: User, issued: tuple[Certificate, bytes]
) -> None:
    """One printed value changed, QR left alone. The document now disagrees
    with what the institution signed."""
    _, pdf = issued
    tampered = edit_pdf_text(pdf, "CGPA 8.50 / 10.00", "CGPA 9.90 / 10.00")

    result = verify(db, verifier, tampered)

    assert result.result == "MISMATCH"
    assert checks(result)["field_match.cgpa"] == "fail"
    # The QR still verifies — which is precisely why the field check matters.
    assert checks(result)["qr_signature"] == "pass"
    # The diff is in the evidence for the result page to render.
    assert "9.90" in details(result) and "8.50" in details(result)


def test_an_edited_name_is_a_mismatch(
    db: Session, verifier: User, issued: tuple[Certificate, bytes]
) -> None:
    _, pdf = issued
    tampered = edit_pdf_text(pdf, STUDENT, "Rohan Verma")

    result = verify(db, verifier, tampered)
    assert result.result == "MISMATCH"
    assert checks(result)["field_match.student_name"] == "fail"


def test_a_mismatch_still_does_not_accuse(
    db: Session, verifier: User, issued: tuple[Certificate, bytes]
) -> None:
    _, pdf = issued
    result = verify(db, verifier, edit_pdf_text(pdf, "CGPA 8.50 / 10.00", "CGPA 9.90 / 10.00"))

    text = details(result).lower()
    for word in ("fake", "forged", "fraud", "tamper", "criminal"):
        assert word not in text


def test_only_the_edited_field_fails(
    db: Session, verifier: User, issued: tuple[Certificate, bytes]
) -> None:
    """A field-level diff, not a blanket rejection: everything else still passes."""
    _, pdf = issued
    result = verify(db, verifier, edit_pdf_text(pdf, "CGPA 8.50 / 10.00", "CGPA 9.90 / 10.00"))

    failing = [k for k, v in checks(result).items() if k.startswith("field_match.") and v == "fail"]
    assert failing == ["field_match.cgpa"]
    assert checks(result)["field_match.student_name"] == "pass"
    assert checks(result)["field_match.cert_number"] == "pass"


# --- 5. a document that is not a certificate ---------------------------------


def test_a_random_image_is_manual_review(db: Session, verifier: User) -> None:
    """No template, no record, no evidence either way."""
    result = verify(db, verifier, noise_image())

    assert result.result == "MANUAL_REVIEW"
    assert result.certificate_id is None
    assert result.extracted_fields["template"] is None
    assert checks(result)["field_match"] in {"skipped", "uncertain"}


def test_an_unrelated_pdf_is_manual_review(db: Session, verifier: User) -> None:
    result = verify(db, verifier, b"%PDF-1.7\n% not a certificate at all\n")
    assert result.result == "MANUAL_REVIEW"
    assert result.certificate_id is None


def test_a_random_image_result_does_not_accuse(db: Session, verifier: User) -> None:
    text = details(verify(db, verifier, noise_image())).lower()
    for word in ("fake", "forged", "fraud"):
        assert word not in text


# --- revocation on the upload path -------------------------------------------


def test_a_genuine_pdf_of_a_revoked_certificate_is_revoked(
    db: Session, verifier: User, issued: tuple[Certificate, bytes]
) -> None:
    """Rule 1 outranks a byte-perfect hash match."""
    cert, pdf = issued
    issuer = db.scalar(
        __import__("sqlalchemy").select(User).where(User.email == "e2e-issuer@t.test")
    )
    cert_service.revoke_certificate(db, issuer, cert.id, reason="Issued in error (test)")
    db.flush()

    result = verify(db, verifier, pdf)
    assert result.result == "REVOKED"
    assert checks(result)["revocation"] == "fail"


# --- what gets stored --------------------------------------------------------


def test_the_stored_evidence_is_auditable_but_not_the_document(
    db: Session, verifier: User, issued: tuple[Certificate, bytes]
) -> None:
    """`extracted_fields` carries the fields and their confidences, the
    template and the text source — never the document's full text."""
    _, pdf = issued
    result = verify(db, verifier, render_png(pdf))
    extracted = result.extracted_fields

    assert extracted["template"] == "nbit"
    assert extracted["ocr_engine"] == "tesseract"
    assert extracted["text_source"] == "ocr"
    assert extracted["qr_present"] is True
    assert 0.0 < extracted["mean_line_confidence"] <= 1.0

    cert_number = extracted["fields"]["cert_number"]
    assert cert_number["value"] == CERT_NUMBER
    assert 0.0 <= cert_number["confidence"] <= 1.0

    # No full-text dump anywhere in the stored evidence.
    assert "text" not in extracted
    assert "lines" not in extracted
    assert PROGRAMME.upper() not in str(extracted.get("raw_text", ""))


def test_every_upload_is_recorded_as_an_upload(
    db: Session, verifier: User, issued: tuple[Certificate, bytes]
) -> None:
    _, pdf = issued
    result = verify(db, verifier, pdf)
    assert result.method == "upload"
    assert result.verifier_id == verifier.id


# --- known limitation: a white box over the text layer -----------------------


def test_a_white_box_overlay_is_not_detected_on_the_pdf_path(
    db: Session, verifier: User, issued: tuple[Certificate, bytes]
) -> None:
    """KNOWN LIMITATION, pinned deliberately.

    Covering a value with a white rectangle and printing a different one on
    top leaves the original glyphs in the content stream. Our PDF path trusts
    the text layer, so it reads the *original* value, every field agrees, and
    the result is VERIFIED — while a human looking at the page sees the new
    value.

    This is not a mismatch and not a false accusation; it is a false
    reassurance, which is the more dangerous direction. Rendering the page and
    OCRing it instead does see the visible value (asserted below), so the fix
    is to cross-check the text layer against a raster of the page. That costs
    an OCR pass on every PDF, so it is a deliberate decision rather than an
    oversight — see CLAUDE.md.
    """
    _, pdf = issued
    covered = cover_pdf_text(pdf, "CGPA 8.50 / 10.00", "CGPA 9.90 / 10.00")

    result = verify(db, verifier, covered)

    # Current behaviour: the hidden original is what gets compared.
    assert result.result == "VERIFIED"
    assert result.extracted_fields["text_source"] == "pdf_text_layer"
    assert result.extracted_fields["fields"]["cgpa"]["value"] == "8.50"


def test_ocr_of_the_rendered_page_does_see_the_overlay(
    db: Session, verifier: User, issued: tuple[Certificate, bytes]
) -> None:
    """The other half of the limitation above: once the page is rasterised,
    the visible value is what is read, and the overlay is caught."""
    _, pdf = issued
    covered = cover_pdf_text(pdf, "CGPA 8.50 / 10.00", "CGPA 9.90 / 10.00")

    result = verify(db, verifier, render_png(covered))

    assert result.result == "MISMATCH"
    assert checks(result)["field_match.cgpa"] == "fail"
    assert result.extracted_fields["fields"]["cgpa"]["value"] == "9.90"
