"""Institution registry: create, bulk import, list, get."""

import csv
import io
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.models import Certificate, CertificateStatus, Institution, Role, User
from app.schemas.certificates import CSV_COLUMNS, CertificateFields, CertificateImportRow
from app.services import audit
from app.services.hashing import sha256_bytes
from app.services.normalize import normalize_id
from app.services.pdf_issue import (
    CertificatePdfData,
    build_certificate_pdf,
    delete_issued_pdf,
    issued_pdf_path,
    write_issued_pdf,
)
from app.services.signing import (
    CertificateRecord,
    SigningKeyMissing,
    load_private_key,
    sign_record,
)


def _institution_of(user: User) -> Institution:
    if user.role != Role.INSTITUTION or user.institution is None:
        raise AppError(403, "forbidden", "Only institution users can add certificates.")
    return user.institution


def _signing_key(institution: Institution) -> Ed25519PrivateKey:
    try:
        return load_private_key(institution.code)
    except SigningKeyMissing as exc:
        raise AppError(
            500, "signing_key_missing", f"No signing key configured for {institution.code}."
        ) from exc


def _build(
    institution: Institution, key: Ed25519PrivateKey, data: CertificateFields
) -> Certificate:
    record = CertificateRecord(
        cert_number=data.cert_number,
        institution_code=institution.code,
        student_name=data.student_name,
        roll_number=data.roll_number,
        programme=data.programme,
        year_of_passing=data.year_of_passing,
        cgpa=data.cgpa,
        marks=data.marks,
        issue_date=data.issue_date,
    )
    return Certificate(
        id=uuid.uuid4(),
        cert_number=data.cert_number,
        institution_id=institution.id,
        student_name=data.student_name,
        roll_number=data.roll_number,
        programme=data.programme,
        year_of_passing=data.year_of_passing,
        cgpa=data.cgpa,
        marks=data.marks,
        issue_date=data.issue_date,
        signature=sign_record(key, record),
        status=CertificateStatus.ACTIVE.value,
    )


def _issue_pdf(institution: Institution, cert: Certificate) -> bytes:
    """Build the certificate PDF once and record its hash on the row. The bytes
    are written to disk by `_commit_with_pdfs` after the insert succeeds."""
    pdf = build_certificate_pdf(
        CertificatePdfData(
            cert_number=cert.cert_number,
            institution_name=institution.name,
            institution_code=institution.code,
            student_name=cert.student_name,
            roll_number=cert.roll_number,
            programme=cert.programme,
            year_of_passing=cert.year_of_passing,
            issue_date=cert.issue_date,
            signature=cert.signature,
            cgpa=cert.cgpa,
            marks=cert.marks,
        )
    )
    cert.file_sha256 = sha256_bytes(pdf)
    return pdf


def _commit_with_pdfs(
    db: Session,
    pdfs: list[tuple[uuid.UUID, bytes]],
    *,
    on_conflict: Callable[[], AppError],
) -> None:
    """Write the issued PDFs, then commit. If either step fails, roll back and
    remove whatever was written, so a stored file never outlives its row."""
    written: list[uuid.UUID] = []
    try:
        for cert_id, pdf in pdfs:
            write_issued_pdf(cert_id, pdf)
            written.append(cert_id)
        db.commit()
    except IntegrityError as exc:  # lost a race with a concurrent insert
        db.rollback()
        for cert_id in written:
            delete_issued_pdf(cert_id)
        raise on_conflict() from exc
    except OSError as exc:
        db.rollback()
        for cert_id in written:
            delete_issued_pdf(cert_id)
        raise AppError(
            500, "pdf_write_failed", "Could not store the issued certificate PDF."
        ) from exc


def issued_pdf(cert: Certificate) -> Path:
    """Path of the stored PDF for this certificate. Never regenerates: if the
    file is gone, say so rather than serving bytes with a different hash."""
    path = issued_pdf_path(cert.id)
    if cert.file_sha256 is None or not path.is_file():
        raise AppError(
            404,
            "pdf_not_available",
            "No issued PDF is stored for this certificate.",
        )
    return path


def needs_pdf(cert: Certificate) -> bool:
    """True when no issued PDF is stored for this certificate (never issued, or
    the file is gone because the volume was recreated)."""
    return cert.file_sha256 is None or not issued_pdf_path(cert.id).is_file()


def backfill_pdf(db: Session, cert: Certificate, *, actor_id: int | None = None) -> str:
    """Issue and store the PDF for a certificate that has none. Returns why it
    was needed. Only ever called for rows where `needs_pdf` is true, so an
    already-served hash is never replaced."""
    reason = "missing_hash" if cert.file_sha256 is None else "missing_file"
    pdf = _issue_pdf(cert.institution, cert)
    audit.record(
        db,
        actor_id=actor_id,
        action="certificate.pdf_backfill",
        entity="certificate",
        entity_id=str(cert.id),
        meta={"cert_number": cert.cert_number, "reason": reason, "file_sha256": cert.file_sha256},
    )
    _commit_with_pdfs(db, [(cert.id, pdf)], on_conflict=_duplicate_error)
    return reason


def _duplicate_error() -> AppError:
    return AppError(409, "duplicate_cert_number", "A certificate with this number already exists.")


def create_certificate(db: Session, user: User, data: CertificateFields) -> Certificate:
    institution = _institution_of(user)
    if db.scalar(select(Certificate.id).where(Certificate.cert_number == data.cert_number)):
        raise _duplicate_error()

    cert = _build(institution, _signing_key(institution), data)
    pdf = _issue_pdf(institution, cert)
    db.add(cert)
    audit.record(
        db,
        actor_id=user.id,
        action="certificate.create",
        entity="certificate",
        entity_id=str(cert.id),
        meta={
            "cert_number": cert.cert_number,
            "institution_code": institution.code,
            "file_sha256": cert.file_sha256,
        },
    )
    _commit_with_pdfs(db, [(cert.id, pdf)], on_conflict=_duplicate_error)
    db.refresh(cert)
    return cert


# --- CSV import ---------------------------------------------------------------


def _row_error(row: int, field: str | None, message: str) -> dict[str, Any]:
    return {"row": row, "field": field, "message": message}


def _pydantic_errors(row: int, exc: ValidationError) -> list[dict[str, Any]]:
    out = []
    for e in exc.errors():
        field = str(e["loc"][0]) if e["loc"] else None
        if e["type"].startswith("date_"):
            message = "Use the format YYYY-MM-DD, e.g. 2024-07-20."
        else:
            message = e["msg"].removeprefix("Value error, ")
            message = message[:1].upper() + message[1:]
        out.append(_row_error(row, field, message))
    return out


def _csv_invalid(message: str, rows: list[dict[str, Any]] | None = None) -> AppError:
    return AppError(422, "csv_invalid", message, rows=rows or [])


def _parse_csv(content: bytes) -> csv.DictReader[str]:
    if len(content) > settings.import_max_mb * 1024 * 1024:
        raise _csv_invalid(f"File is larger than {settings.import_max_mb} MB.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise _csv_invalid("File is not valid UTF-8 text.") from exc

    reader = csv.DictReader(io.StringIO(text, newline=""))
    header = [h.strip() for h in (reader.fieldnames or [])]
    missing = [c for c in CSV_COLUMNS if c not in header]
    unknown = [h for h in header if h not in CSV_COLUMNS]
    if missing or unknown:
        parts = []
        if missing:
            parts.append(f"missing columns: {', '.join(missing)}")
        if unknown:
            parts.append(f"unknown columns: {', '.join(unknown)}")
        raise _csv_invalid(
            f"Header is wrong ({'; '.join(parts)}). Expected: {','.join(CSV_COLUMNS)}"
        )
    reader.fieldnames = header
    return reader


def import_csv(db: Session, user: User, content: bytes, filename: str | None) -> int:
    """Validate every row; insert all of them or none. Returns the number imported."""
    institution = _institution_of(user)
    reader = _parse_csv(content)

    errors: list[dict[str, Any]] = []
    valid: list[tuple[int, CertificateImportRow]] = []
    first_seen: dict[str, int] = {}

    for raw in reader:
        line = reader.line_num
        if None in raw:  # more cells than header columns
            errors.append(_row_error(line, None, "Row has more cells than the header."))
            continue
        values = {k: (v or "").strip() for k, v in raw.items()}
        if not any(values.values()):
            continue  # blank line made of commas
        if len(valid) + len(errors) >= settings.import_max_rows:
            raise _csv_invalid(f"File has more than {settings.import_max_rows} rows.")

        try:
            row = CertificateImportRow.model_validate(values)
        except ValidationError as exc:
            errors.extend(_pydantic_errors(line, exc))
            continue

        if row.institution_code != institution.code:
            errors.append(
                _row_error(
                    line,
                    "institution_code",
                    f"Row is for institution {row.institution_code}; "
                    f"you can only import for {institution.code}.",
                )
            )
            continue
        if row.cert_number in first_seen:
            errors.append(
                _row_error(
                    line,
                    "cert_number",
                    f"Duplicate of row {first_seen[row.cert_number]} in this file.",
                )
            )
            continue
        first_seen[row.cert_number] = line
        valid.append((line, row))

    if valid:
        existing = set(
            db.scalars(
                select(Certificate.cert_number).where(
                    Certificate.cert_number.in_([r.cert_number for _, r in valid])
                )
            )
        )
        for line, row in valid:
            if row.cert_number in existing:
                errors.append(_row_error(line, "cert_number", "Already exists in the registry."))

    if errors:
        errors.sort(key=lambda e: e["row"])
        bad_rows = len({e["row"] for e in errors})
        raise _csv_invalid(
            f"{bad_rows} row(s) have errors. Nothing was imported — fix them and upload again.",
            errors,
        )
    if not valid:
        raise _csv_invalid("The file has no data rows.")

    key = _signing_key(institution)
    certs = [_build(institution, key, row) for _, row in valid]
    pdfs = [(cert.id, _issue_pdf(institution, cert)) for cert in certs]
    db.add_all(certs)
    audit.record(
        db,
        actor_id=user.id,
        action="certificate.import",
        entity="certificate",
        meta={"count": len(valid), "filename": filename, "institution_code": institution.code},
    )
    _commit_with_pdfs(
        db,
        pdfs,
        on_conflict=lambda: AppError(
            409, "duplicate_cert_number", "Some certificates were added meanwhile; upload again."
        ),
    )
    return len(valid)


# --- read ---------------------------------------------------------------------


def _scope(stmt, user: User):  # type: ignore[no-untyped-def]
    """Institution users only ever see their own institution's certificates."""
    if user.role == Role.INSTITUTION:
        return stmt.where(Certificate.institution_id == user.institution_id)
    return stmt


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def list_certificates(
    db: Session, user: User, *, q: str | None, page: int, size: int
) -> tuple[list[Certificate], int]:
    stmt = _scope(select(Certificate), user)
    if q and q.strip():
        conditions = [Certificate.student_name.ilike(f"%{_escape_like(q.strip())}%", escape="\\")]
        q_id = normalize_id(q)
        if q_id:
            pattern = f"%{_escape_like(q_id)}%"
            conditions += [
                Certificate.cert_number.like(pattern, escape="\\"),
                Certificate.roll_number.like(pattern, escape="\\"),
            ]
        stmt = stmt.where(or_(*conditions))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(
        stmt.order_by(Certificate.created_at.desc(), Certificate.cert_number)
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    return list(items), total


def get_certificate(db: Session, user: User, certificate_id: uuid.UUID) -> Certificate:
    cert = db.scalar(_scope(select(Certificate).where(Certificate.id == certificate_id), user))
    if cert is None:
        # Same answer for "doesn't exist" and "belongs to another institution".
        raise AppError(404, "not_found", "Certificate not found.")
    return cert
