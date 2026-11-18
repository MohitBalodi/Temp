"""The RQ job behind `POST /verify/upload`.

Runs in the worker process, so it owns its own DB session — the request that
enqueued it is long gone. The job's return value is the verification id, which
`GET /verify/jobs/{job_id}` hands back to the poller.

Keep this thin: it is the hardest code to test and the easiest to leave
half-finished. The work belongs in services.
"""

from __future__ import annotations

import logging
import uuid

from app.core.db import SessionLocal
from app.services import upload_verification

logger = logging.getLogger(__name__)


def verify_upload_job(upload_id: str, verifier_id: int) -> str:
    """Verify an uploaded document; return the verification id as a string.

    Arguments are plain types because RQ pickles them into Redis: a UUID or an
    ORM object would couple the queue to this process's classes.

    Any exception propagates, which is what marks the RQ job failed — the API
    reports that as `{"status": "failed"}` rather than inventing a result.
    """
    db = SessionLocal()
    try:
        upload, verifier = upload_verification.load_for_job(db, uuid.UUID(upload_id), verifier_id)
        verification = upload_verification.verify_upload(db, upload, verifier)
        logger.info(
            "upload %s verified as %s (verification %s)",
            upload_id,
            verification.result,
            verification.id,
        )
        return str(verification.id)
    finally:
        db.close()
