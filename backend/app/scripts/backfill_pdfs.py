"""Issue PDFs for certificates created before issuance existed.

Run: docker compose exec api python -m app.scripts.backfill_pdfs

Idempotent. A certificate whose stored file is present is skipped, so a hash a
verifier has already seen is never replaced. A row that has a hash but no file
(the uploads volume was recreated) is rebuilt and its new hash written — the
audit row records that as a re-issue.
"""

import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models import Certificate
from app.services import certificates as service


def backfill(db: Session) -> list[str]:
    log: list[str] = []
    certificates = db.scalars(select(Certificate).order_by(Certificate.cert_number)).all()
    done = 0
    for cert in certificates:
        if not service.needs_pdf(cert):
            continue
        reason = service.backfill_pdf(db, cert)
        done += 1
        log.append(f"issued {cert.cert_number} ({reason}) sha256={cert.file_sha256[:12]}…")
    log.append(f"{done} issued, {len(certificates) - done} already had a stored PDF")
    return log


def main() -> int:
    with SessionLocal() as db:
        for line in backfill(db):
            print(f"backfill: {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
