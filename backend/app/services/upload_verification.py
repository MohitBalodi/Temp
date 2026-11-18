"""Verifying an uploaded document: the I/O around the pure engine.

Mirrors `services/verifications.py` for the upload method. The decision still
belongs to `verification/engine.py`; this module reads the file, runs the OCR
pipeline, finds the candidate record and keeps the evidence.

How the candidate record is found, in order:
1. the QR payload on the page, if one decoded — it names the certificate;
2. the file's SHA-256 against a stored issued PDF;
3. the certificate number read off the document.

All three are untrusted hints about *which* record to compare against. None of
them decides anything: the engine does that from the record it is given.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.models import Certificate, Upload, User, Verification
from app.services import audit
from app.services.ocr import extract, extract_fields
from app.services.ocr.extract_text import ExtractedPage, TextSource
from app.services.qr import QrPayload, QrPayloadError, parse_payload
from app.services.verification.engine import (
    CRITICAL_FIELDS,
    ExtractedFieldValue,
    Thresholds,
    UploadEvidence,
    VerificationInput,
    VerificationMethod,
    evaluate,
)
from app.services.verifications import registry_record

logger = logging.getLogger(__name__)


def _thresholds() -> Thresholds:
    return Thresholds(min_field_confidence=settings.ocr_min_field_confidence)


def _by_file_hash(db: Session, sha256: str) -> Certificate | None:
    """The certificate whose issued PDF has exactly these bytes."""
    return db.scalar(select(Certificate).where(Certificate.file_sha256 == sha256))


def _by_number(db: Session, cert_number: str) -> Certificate | None:
    return db.scalar(select(Certificate).where(Certificate.cert_number == cert_number))


def _first_qr(page: ExtractedPage) -> QrPayload | None:
    """The first decodable AVA1 payload on the page.

    Unreadable QR text is ignored rather than raised: unlike the scan
    endpoint, the verifier did not claim this was a QR code, so a sticker or a
    barcode on the page must not fail the whole verification.
    """
    for raw in page.qr_payloads:
        try:
            return parse_payload(raw)
        except QrPayloadError:
            logger.info("ignoring a non-AVA1 code found on an uploaded page")
    return None


def _evidence(upload: Upload, page: ExtractedPage, extraction) -> UploadEvidence:
    fields = {
        name: ExtractedFieldValue(value=found.value, confidence=found.confidence)
        for name, found in extraction.fields.items()
        if name in CRITICAL_FIELDS
    }
    return UploadEvidence(
        sha256=upload.sha256,
        template=extraction.template,
        fields=fields,
        has_text=not page.is_empty,
    )


def _extracted_summary(
    upload: Upload, page: ExtractedPage, extraction, qr: QrPayload | None
) -> dict[str, object]:
    """What goes into `verifications.extracted_fields`.

    Field values and confidences, the template, the text source — never the
    document's full text, and never the file itself.
    """
    summary: dict[str, object] = {
        "file_sha256": upload.sha256,
        "mime": upload.mime,
        "text_source": page.source.value,
        "template": extraction.template,
        "ocr_engine": page.engine,
        "line_count": len(page.lines),
        "mean_line_confidence": round(page.mean_confidence, 4),
        "fields": {name: f.as_dict() for name, f in extraction.fields.items()},
    }
    if qr is not None:
        summary["qr_present"] = True
        summary["cert_number"] = qr.cert_number
        summary["institution_code"] = qr.institution_code
    else:
        summary["qr_present"] = False
        if number := extraction.value("cert_number"):
            summary["cert_number"] = number
    return summary


def verify_upload(db: Session, upload: Upload, verifier: User) -> Verification:
    """Run the upload through the OCR pipeline and the engine, and record it.

    Always produces a Verification: an unreadable or unknown document is
    MANUAL_REVIEW, never an accusation.
    """
    data = _read(upload)
    page = extract(data, upload.mime)
    extraction = extract_fields(page.lines)
    qr = _first_qr(page)

    cert = None
    if qr is not None:
        cert = _by_number(db, qr.cert_number)
    if cert is None:
        cert = _by_file_hash(db, upload.sha256)
    if cert is None and (number := extraction.value("cert_number")):
        cert = _by_number(db, number)

    outcome = evaluate(
        VerificationInput(
            method=VerificationMethod.UPLOAD,
            cert_number=(cert.cert_number if cert else (extraction.value("cert_number") or "")),
            record=registry_record(cert) if cert else None,
            qr=qr,
            upload=_evidence(upload, page, extraction),
            thresholds=_thresholds(),
        )
    )

    verification = Verification(
        id=uuid.uuid4(),
        verifier_id=verifier.id,
        method=VerificationMethod.UPLOAD.value,
        certificate_id=cert.id if cert else None,
        result=outcome.result.value,
        checks=outcome.checks_as_dicts(),
        extracted_fields=_extracted_summary(upload, page, extraction, qr),
    )
    db.add(verification)
    audit.record(
        db,
        actor_id=verifier.id,
        action="verification.create",
        entity="verification",
        entity_id=str(verification.id),
        meta={
            "method": VerificationMethod.UPLOAD.value,
            "result": outcome.result.value,
            "upload_id": str(upload.id),
            "certificate_id": str(cert.id) if cert else None,
            "text_source": page.source.value,
            "template": extraction.template,
        },
    )
    db.commit()
    db.refresh(verification)
    return verification


def _read(upload: Upload) -> bytes:
    from pathlib import Path

    try:
        return Path(upload.path).read_bytes()
    except OSError as exc:
        raise AppError(
            500,
            "upload_unreadable",
            "The uploaded file could not be read back from storage.",
        ) from exc


def load_for_job(db: Session, upload_id: uuid.UUID, verifier_id: int) -> tuple[Upload, User]:
    """Fetch the job's upload and verifier, or fail loudly.

    The job runs after the request, so both may have gone; an RQ failure with a
    clear message beats a half-written verification.
    """
    upload = db.get(Upload, upload_id)
    if upload is None:
        raise AppError(404, "upload_not_found", f"Upload {upload_id} no longer exists.")
    verifier = db.get(User, verifier_id)
    if verifier is None:
        raise AppError(404, "not_found", f"User {verifier_id} no longer exists.")
    return upload, verifier


__all__ = ["TextSource", "load_for_job", "verify_upload"]
