"""The OCR queue, and the job-status shape the API reports.

One place builds the Redis connection and the Queue, so the API, the worker and
the tests all agree on the queue name.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache

from redis import Redis
from rq import Queue
from rq.job import Job

from app.core.config import settings

QUEUE_NAME = "ocr"

# An OCR job is seconds of work; these bound a stuck one rather than tune it.
JOB_TIMEOUT_SECONDS = 300
JOB_RESULT_TTL_SECONDS = 24 * 60 * 60


class JobState(StrEnum):
    """What the API reports. Narrower than RQ's own statuses on purpose: a
    verifier watching a spinner needs four states, not eight."""

    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


# RQ status -> what we report. Anything unknown is treated as failed, so a
# status we have not mapped can never look like "still working" forever.
_STATE_BY_RQ_STATUS = {
    "queued": JobState.QUEUED,
    "deferred": JobState.QUEUED,
    "scheduled": JobState.QUEUED,
    "started": JobState.RUNNING,
    "finished": JobState.DONE,
    "failed": JobState.FAILED,
    "canceled": JobState.FAILED,
    "stopped": JobState.FAILED,
}


@dataclass(frozen=True, slots=True)
class JobStatus:
    state: JobState
    verification_id: uuid.UUID | None = None
    error: str | None = None


def state_for(rq_status: str | None) -> JobState:
    """Map an RQ status string onto a reported state."""
    if rq_status is None:
        return JobState.FAILED
    return _STATE_BY_RQ_STATUS.get(rq_status, JobState.FAILED)


@lru_cache
def get_redis() -> Redis:
    return Redis.from_url(settings.redis_url)


def get_queue() -> Queue:
    return Queue(QUEUE_NAME, connection=get_redis())


def fetch_job(job_id: str) -> Job | None:
    try:
        return Job.fetch(job_id, connection=get_redis())
    except Exception:
        # RQ raises NoSuchJobError, but a malformed id can fail earlier.
        return None
