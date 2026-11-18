import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Upload(Base):
    """A document a verifier uploaded, pending or past OCR.

    The file itself lives under `UPLOAD_DIR/verify/`, deliberately beside —
    not inside — `ISSUED_DIR`, so pruning uploads can never reach an issued
    certificate PDF. Rows are deleted together with their file once
    `expires_at` has passed (`app.scripts.prune_uploads`).

    Only what verification needs is kept: the path, the hash, the type. The
    extracted text is never stored on this row; what the OCR read goes into
    `verifications.extracted_fields` as fields, not as the document.
    """

    __tablename__ = "uploads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    path: Mapped[str] = mapped_column(String(512))
    # Lowercase hex. Indexed: the file-hash check looks certificates up by it,
    # and a repeat upload of the same document is recognisable.
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    mime: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
