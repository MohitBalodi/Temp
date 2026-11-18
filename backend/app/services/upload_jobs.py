"""Submitting upload jobs and reporting their status.

The boundary between the request and the worker: store the file, enqueue the
job, and later translate RQ's bookkeeping into the four states a verifier's
spinner needs.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Role, Upload, User
from app.schemas.verify import JobStatusOut, UploadAccepted
from app.services import audit, uploads
from app.workers.queue import (
    JOB_RESULT_TTL_SECONDS,
    JOB_TIMEOUT_SECONDS,
    JobState,
    fetch_job,
    get_queue,
    state_for,
)

JOB_PATH = "app.workers.ocr_job.verify_upload_job"


def submit(db: Session, data: bytes, verifier: User) -> UploadAccepted:
    """Store the document and queue it for extraction.

    The row is committed before the job is enqueued: the worker looks the
    upload up by id, so it must be visible to another connection by the time
    the job can be picked up.
    """
    upload = uploads.store(db, data)
    audit.record(
        db,
        actor_id=verifier.id,
        action="upload.create",
        entity="upload",
        entity_id=str(upload.id),
        # Hash and type only. The document's contents are never logged.
        meta={"mime": upload.mime, "sha256": upload.sha256, "bytes": len(data)},
    )
    db.commit()

    job = get_queue().enqueue(
        JOB_PATH,
        str(upload.id),
        verifier.id,
        job_timeout=JOB_TIMEOUT_SECONDS,
        result_ttl=JOB_RESULT_TTL_SECONDS,
        # Who may poll this job. Checked in `status()`.
        meta={"verifier_id": verifier.id, "upload_id": str(upload.id)},
    )
    return UploadAccepted(job_id=job.id, upload_id=upload.id)


def status(job_id: str, user: User) -> JobStatusOut:
    """Report a job to the verifier who submitted it, or to an admin.

    An unknown job and someone else's job give the same 404, so job ids cannot
    be probed.
    """
    job = fetch_job(job_id)
    if job is None:
        raise AppError(404, "job_not_found", "No such verification job.")

    owner = (job.meta or {}).get("verifier_id")
    if user.role != Role.ADMIN and owner != user.id:
        raise AppError(404, "job_not_found", "No such verification job.")

    state = state_for(job.get_status(refresh=True))

    verification_id: uuid.UUID | None = None
    error: str | None = None

    if state is JobState.DONE:
        verification_id = _verification_id(job.return_value())
        if verification_id is None:
            # Finished without a usable id: report it as failed rather than
            # leaving the client polling a job that will never resolve.
            state = JobState.FAILED
            error = "The job finished without recording a verification."
    elif state is JobState.FAILED:
        error = "Extraction failed. The document was not verified."

    return JobStatusOut(status=state.value, verification_id=verification_id, error=error)


def _verification_id(value: object) -> uuid.UUID | None:
    if isinstance(value, uuid.UUID):
        return value
    if isinstance(value, str):
        try:
            return uuid.UUID(value)
        except ValueError:
            return None
    return None


def get_upload(db: Session, upload_id: uuid.UUID) -> Upload:
    upload = uploads.get(db, upload_id)
    if upload is None:
        raise AppError(404, "upload_not_found", "Upload not found.")
    return upload
