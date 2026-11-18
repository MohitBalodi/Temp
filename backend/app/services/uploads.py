"""Verifier document uploads: sniff the type, store the bytes, hash them.

The declared filename and the browser's Content-Type are both attacker-chosen,
so neither decides anything here: the type comes from the file's own leading
bytes. An upload whose magic bytes are not PDF, PNG or JPEG is rejected before
it is written to disk.

Files go under `UPLOAD_DIR/verify/`, never inside `ISSUED_DIR` — pruning
expired uploads must not be able to reach an issued certificate PDF.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.models import ReviewCase, ReviewStatus, Upload, Verification
from app.services.hashing import sha256_bytes

MIME_PDF = "application/pdf"
MIME_PNG = "image/png"
MIME_JPEG = "image/jpeg"


@dataclass(frozen=True, slots=True)
class FileType:
    mime: str
    extension: str


# Leading bytes -> type. Ordered longest-prefix-first so no signature can be
# shadowed by a shorter one.
_SIGNATURES: tuple[tuple[bytes, FileType], ...] = (
    (b"\x89PNG\r\n\x1a\n", FileType(MIME_PNG, ".png")),
    (b"%PDF-", FileType(MIME_PDF, ".pdf")),
    (b"\xff\xd8\xff", FileType(MIME_JPEG, ".jpg")),
)

# Longest signature we need to look at.
SNIFF_BYTES = max(len(sig) for sig, _ in _SIGNATURES)

ACCEPTED_DESCRIPTION = "PDF, PNG or JPEG"


def sniff_type(data: bytes) -> FileType | None:
    """The file's real type from its magic bytes, or None if unrecognised.

    Pure: no filesystem, no settings. `data` may be just the first
    `SNIFF_BYTES` bytes.
    """
    for signature, file_type in _SIGNATURES:
        if data.startswith(signature):
            return file_type
    return None


def upload_root() -> Path:
    """Where verifier uploads live. Separate from ISSUED_DIR by construction."""
    return Path(settings.upload_dir) / "verify"


def max_bytes() -> int:
    return settings.upload_max_mb * 1024 * 1024


def _expires_at(now: datetime) -> datetime:
    return now + timedelta(days=settings.upload_retention_days)


def store(db: Session, data: bytes, *, now: datetime | None = None) -> Upload:
    """Validate, write and record an uploaded document.

    Raises AppError 400 for an empty file, 413 for one over `UPLOAD_MAX_MB`,
    and 415 when the magic bytes are not one of the accepted types. The row is
    added to the caller's transaction; the caller commits.
    """
    if not data:
        raise AppError(400, "upload_empty", "The uploaded file is empty.")

    limit = max_bytes()
    if len(data) > limit:
        raise AppError(
            413,
            "upload_too_large",
            f"The file is larger than the {settings.upload_max_mb} MB limit.",
            max_mb=settings.upload_max_mb,
        )

    file_type = sniff_type(data[:SNIFF_BYTES])
    if file_type is None:
        raise AppError(
            415,
            "upload_unsupported_type",
            f"Only {ACCEPTED_DESCRIPTION} files can be verified. "
            "The file's contents are not any of those, whatever its name says.",
        )

    now = now or datetime.now(UTC)
    upload_id = uuid.uuid4()
    root = upload_root()
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{upload_id}{file_type.extension}"
    # Written before the row is committed; a crash in between leaves an orphan
    # file, which the prune job will not see. Preferable to a committed row
    # pointing at a file that was never written.
    path.write_bytes(data)

    row = Upload(
        id=upload_id,
        path=str(path),
        sha256=sha256_bytes(data),
        mime=file_type.mime,
        expires_at=_expires_at(now),
    )
    db.add(row)
    return row


def get(db: Session, upload_id: uuid.UUID) -> Upload | None:
    return db.get(Upload, upload_id)


def held_upload_ids(db: Session) -> set[uuid.UUID]:
    """Uploads an open verification request is about.

    Retention must not delete the document while an institution is being
    asked to look at it — the case page would show a broken preview and the
    evidence behind the institution's answer would be gone. The hold lasts
    exactly as long as the case is open: once it closes, the ordinary
    expiry applies and the next prune takes the file.
    """
    return set(
        db.scalars(
            select(Verification.upload_id)
            .join(ReviewCase, ReviewCase.verification_id == Verification.id)
            .where(
                Verification.upload_id.is_not(None),
                ReviewCase.status != ReviewStatus.CLOSED.value,
            )
        )
    )


def prune_expired(db: Session, *, now: datetime | None = None) -> tuple[int, int]:
    """Delete uploads whose retention has passed, with their files.

    Returns (rows deleted, files removed). A file that is already gone is not
    an error — the row still goes. An upload held by an open verification
    request is skipped, however old it is. The caller commits.
    """
    now = now or datetime.now(UTC)
    held = held_upload_ids(db)
    rows = [
        row
        for row in db.scalars(select(Upload).where(Upload.expires_at <= now))
        if row.id not in held
    ]

    files_removed = 0
    for row in rows:
        try:
            Path(row.path).unlink()
            files_removed += 1
        except FileNotFoundError:
            pass
        db.delete(row)

    return len(rows), files_removed
