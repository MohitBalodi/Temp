"""Upload storage, type sniffing, retention and the submit/poll endpoints.

The RQ queue is faked: these tests are about the API contract and the stored
file, not about Redis. The job itself is exercised in test_upload_job.py.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Upload, User
from app.services import upload_jobs, uploads
from app.workers.queue import JobState, state_for

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"
PDF_MAGIC = b"%PDF-"


def png_bytes(body: bytes = b"payload") -> bytes:
    return PNG_MAGIC + body


def pdf_bytes(body: bytes = b"1.7 payload") -> bytes:
    return PDF_MAGIC + body


# --- fake queue ---------------------------------------------------------------


@dataclass
class FakeJob:
    id: str
    meta: dict[str, Any]
    _status: str = "queued"
    _result: Any = None

    def get_status(self, refresh: bool = True) -> str:
        return self._status

    def return_value(self) -> Any:
        return self._result


@dataclass
class FakeQueue:
    jobs: dict[str, FakeJob] = field(default_factory=dict)
    enqueued: list[tuple[str, tuple[Any, ...]]] = field(default_factory=list)

    def enqueue(self, path: str, *args: Any, **kwargs: Any) -> FakeJob:
        job = FakeJob(id=str(uuid.uuid4()), meta=dict(kwargs.get("meta") or {}))
        self.jobs[job.id] = job
        self.enqueued.append((path, args))
        return job


@pytest.fixture
def queue(monkeypatch: pytest.MonkeyPatch) -> FakeQueue:
    q = FakeQueue()
    monkeypatch.setattr(upload_jobs, "get_queue", lambda: q)
    monkeypatch.setattr(upload_jobs, "fetch_job", lambda job_id: q.jobs.get(job_id))
    return q


@pytest.fixture(autouse=True)
def upload_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Uploads go to a per-test temp dir, never the real volume."""
    path = tmp_path / "uploads"
    monkeypatch.setattr(settings, "upload_dir", str(path))
    return path


# --- type sniffing (pure) -----------------------------------------------------


@pytest.mark.parametrize(
    ("data", "mime", "extension"),
    [
        (PNG_MAGIC + b"rest", "image/png", ".png"),
        (PDF_MAGIC + b"1.4", "application/pdf", ".pdf"),
        (JPEG_MAGIC + b"\xe0\x00", "image/jpeg", ".jpg"),
    ],
)
def test_sniff_type_reads_magic_bytes(data: bytes, mime: str, extension: str) -> None:
    file_type = uploads.sniff_type(data)
    assert file_type is not None
    assert (file_type.mime, file_type.extension) == (mime, extension)


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"GIF89a",
        b"<html><body>not a certificate</body></html>",
        b"PK\x03\x04",  # a zip/docx
        b"\x00\x00\x00\x00",
    ],
)
def test_sniff_type_rejects_everything_else(data: bytes) -> None:
    assert uploads.sniff_type(data) is None


def test_sniff_type_ignores_a_signature_that_is_not_at_the_start() -> None:
    """A PDF header further into the file is not a PDF."""
    assert uploads.sniff_type(b"junk" + PDF_MAGIC) is None


# --- storage ------------------------------------------------------------------


def test_store_writes_the_file_and_records_hash_and_type(db: Session, upload_dir: Path) -> None:
    data = png_bytes(b"certificate image")
    row = uploads.store(db, data)
    db.flush()

    assert row.mime == "image/png"
    assert row.path.endswith(".png")
    stored = Path(row.path)
    assert stored.read_bytes() == data
    # Beside ISSUED_DIR, not inside it: pruning can never reach issued PDFs.
    assert stored.parent == upload_dir / "verify"
    assert Path(settings.issued_dir) not in stored.parents

    import hashlib

    assert row.sha256 == hashlib.sha256(data).hexdigest()


def test_store_sets_expiry_from_retention_days(db: Session) -> None:
    now = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)
    row = uploads.store(db, png_bytes(), now=now)
    assert row.expires_at == now + timedelta(days=settings.upload_retention_days)


def test_store_rejects_an_empty_file(db: Session) -> None:
    from app.core.errors import AppError

    with pytest.raises(AppError) as exc:
        uploads.store(db, b"")
    assert exc.value.code == "upload_empty"


def test_store_rejects_an_unsupported_type_without_writing_it(
    db: Session, upload_dir: Path
) -> None:
    from app.core.errors import AppError

    with pytest.raises(AppError) as exc:
        uploads.store(db, b"GIF89a and then some")
    assert exc.value.status_code == 415
    assert exc.value.code == "upload_unsupported_type"
    assert not (upload_dir / "verify").exists() or not list((upload_dir / "verify").iterdir())


def test_store_rejects_a_file_over_the_limit(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.errors import AppError

    monkeypatch.setattr(settings, "upload_max_mb", 1)
    oversize = png_bytes(b"x" * (1024 * 1024))

    with pytest.raises(AppError) as exc:
        uploads.store(db, oversize)
    assert exc.value.status_code == 413
    assert exc.value.code == "upload_too_large"


def test_store_accepts_a_file_exactly_at_the_limit(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "upload_max_mb", 1)
    limit = 1024 * 1024
    data = png_bytes() + b"x" * (limit - len(PNG_MAGIC) - len(b"payload"))
    assert len(data) == limit

    row = uploads.store(db, data)
    assert Path(row.path).stat().st_size == limit


# --- retention ----------------------------------------------------------------


def test_prune_expired_removes_due_rows_and_their_files(db: Session) -> None:
    now = datetime(2026, 3, 10, tzinfo=UTC)
    old = uploads.store(db, png_bytes(b"old"), now=now - timedelta(days=30))
    fresh = uploads.store(db, pdf_bytes(b"fresh"), now=now)
    db.flush()
    old_path, fresh_path = Path(old.path), Path(fresh.path)

    rows, files = uploads.prune_expired(db, now=now)
    db.flush()

    assert (rows, files) == (1, 1)
    assert not old_path.exists()
    assert fresh_path.exists()
    assert db.get(Upload, fresh.id) is not None


def test_prune_expired_tolerates_a_file_already_gone(db: Session) -> None:
    now = datetime(2026, 3, 10, tzinfo=UTC)
    row = uploads.store(db, png_bytes(), now=now - timedelta(days=30))
    db.flush()
    Path(row.path).unlink()

    rows, files = uploads.prune_expired(db, now=now)
    assert (rows, files) == (1, 0)


def test_prune_expired_leaves_an_upload_due_in_the_future(db: Session) -> None:
    now = datetime(2026, 3, 10, tzinfo=UTC)
    uploads.store(db, png_bytes(), now=now)
    db.flush()
    assert uploads.prune_expired(db, now=now) == (0, 0)


# --- job state mapping (pure) -------------------------------------------------


@pytest.mark.parametrize(
    ("rq_status", "expected"),
    [
        ("queued", JobState.QUEUED),
        ("deferred", JobState.QUEUED),
        ("scheduled", JobState.QUEUED),
        ("started", JobState.RUNNING),
        ("finished", JobState.DONE),
        ("failed", JobState.FAILED),
        ("canceled", JobState.FAILED),
        ("stopped", JobState.FAILED),
    ],
)
def test_state_for_maps_rq_statuses(rq_status: str, expected: JobState) -> None:
    assert state_for(rq_status) is expected


@pytest.mark.parametrize("rq_status", [None, "something-new"])
def test_state_for_treats_the_unknown_as_failed(rq_status: str | None) -> None:
    """Never report an unmapped status as still-working: the client would poll
    for ever."""
    assert state_for(rq_status) is JobState.FAILED


# --- endpoints ----------------------------------------------------------------


def _post(client: TestClient, headers: dict[str, str], data: bytes, name: str = "cert.png"):
    return client.post(
        "/api/v1/verify/upload",
        headers=headers,
        files={"file": (name, data, "application/octet-stream")},
    )


def test_upload_accepts_and_enqueues(
    client: TestClient,
    auth_headers: dict[str, dict[str, str]],
    queue: FakeQueue,
    db: Session,
) -> None:
    r = _post(client, auth_headers["verifier"], pdf_bytes(), "certificate.pdf")

    assert r.status_code == 202, r.text
    body = r.json()
    upload_id = uuid.UUID(body["upload_id"])
    assert body["job_id"] in queue.jobs

    row = db.get(Upload, upload_id)
    assert row is not None
    assert row.mime == "application/pdf"

    path, args = queue.enqueued[0]
    assert path == "app.workers.ocr_job.verify_upload_job"
    assert args == (str(upload_id), queue.jobs[body["job_id"]].meta["verifier_id"])


def test_upload_trusts_bytes_not_the_filename(
    client: TestClient, auth_headers: dict[str, dict[str, str]], queue: FakeQueue, db: Session
) -> None:
    """A PNG named .pdf is stored as a PNG."""
    r = _post(client, auth_headers["verifier"], png_bytes(), "actually_a_png.pdf")

    assert r.status_code == 202
    row = db.get(Upload, uuid.UUID(r.json()["upload_id"]))
    assert row is not None
    assert row.mime == "image/png"
    assert row.path.endswith(".png")


def test_upload_rejects_a_disguised_unsupported_file(
    client: TestClient, auth_headers: dict[str, dict[str, str]], queue: FakeQueue
) -> None:
    r = _post(client, auth_headers["verifier"], b"GIF89a pretending", "certificate.pdf")

    assert r.status_code == 415
    assert r.json()["error"]["code"] == "upload_unsupported_type"
    assert queue.enqueued == []


def test_upload_rejects_an_oversized_file(
    client: TestClient,
    auth_headers: dict[str, dict[str, str]],
    queue: FakeQueue,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "upload_max_mb", 1)
    r = _post(client, auth_headers["verifier"], png_bytes(b"x" * (1024 * 1024)))

    assert r.status_code == 413
    assert r.json()["error"]["code"] == "upload_too_large"
    assert queue.enqueued == []


def test_upload_requires_a_verifier_or_admin(
    client: TestClient, auth_headers: dict[str, dict[str, str]], queue: FakeQueue
) -> None:
    r = _post(client, auth_headers["institution"], pdf_bytes())
    assert r.status_code == 403
    assert queue.enqueued == []


def test_upload_requires_authentication(client: TestClient, queue: FakeQueue) -> None:
    r = client.post(
        "/api/v1/verify/upload", files={"file": ("c.pdf", pdf_bytes(), "application/pdf")}
    )
    assert r.status_code == 401


# --- polling ------------------------------------------------------------------


def test_job_status_reports_queued_then_running_then_done(
    client: TestClient, auth_headers: dict[str, dict[str, str]], queue: FakeQueue
) -> None:
    job_id = _post(client, auth_headers["verifier"], pdf_bytes()).json()["job_id"]
    job = queue.jobs[job_id]

    r = client.get(f"/api/v1/verify/jobs/{job_id}", headers=auth_headers["verifier"])
    assert r.json() == {"status": "queued", "verification_id": None, "error": None}

    job._status = "started"
    r = client.get(f"/api/v1/verify/jobs/{job_id}", headers=auth_headers["verifier"])
    assert r.json()["status"] == "running"

    verification_id = uuid.uuid4()
    job._status = "finished"
    job._result = str(verification_id)
    r = client.get(f"/api/v1/verify/jobs/{job_id}", headers=auth_headers["verifier"])
    body = r.json()
    assert body["status"] == "done"
    assert uuid.UUID(body["verification_id"]) == verification_id


def test_job_status_reports_a_failure_without_a_verdict(
    client: TestClient, auth_headers: dict[str, dict[str, str]], queue: FakeQueue
) -> None:
    """A failed extraction is not a judgement on the document."""
    job_id = _post(client, auth_headers["verifier"], pdf_bytes()).json()["job_id"]
    queue.jobs[job_id]._status = "failed"

    body = client.get(f"/api/v1/verify/jobs/{job_id}", headers=auth_headers["verifier"]).json()
    assert body["status"] == "failed"
    assert body["verification_id"] is None
    assert body["error"]
    for word in ("fake", "forged", "fraud"):
        assert word not in body["error"].lower()


def test_job_finished_without_an_id_is_reported_failed(
    client: TestClient, auth_headers: dict[str, dict[str, str]], queue: FakeQueue
) -> None:
    job_id = _post(client, auth_headers["verifier"], pdf_bytes()).json()["job_id"]
    job = queue.jobs[job_id]
    job._status = "finished"
    job._result = None

    body = client.get(f"/api/v1/verify/jobs/{job_id}", headers=auth_headers["verifier"]).json()
    assert body["status"] == "failed"
    assert body["verification_id"] is None


def test_job_status_hides_another_verifiers_job(
    client: TestClient,
    auth_headers: dict[str, dict[str, str]],
    users: dict[str, User],
    queue: FakeQueue,
) -> None:
    job_id = _post(client, auth_headers["verifier"], pdf_bytes()).json()["job_id"]
    # Re-point the job at somebody else.
    queue.jobs[job_id].meta["verifier_id"] = users["admin"].id + 999

    r = client.get(f"/api/v1/verify/jobs/{job_id}", headers=auth_headers["verifier"])
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "job_not_found"


def test_job_status_lets_an_admin_see_any_job(
    client: TestClient, auth_headers: dict[str, dict[str, str]], queue: FakeQueue
) -> None:
    job_id = _post(client, auth_headers["verifier"], pdf_bytes()).json()["job_id"]
    r = client.get(f"/api/v1/verify/jobs/{job_id}", headers=auth_headers["admin"])
    assert r.status_code == 200


def test_unknown_job_is_not_found(
    client: TestClient, auth_headers: dict[str, dict[str, str]], queue: FakeQueue
) -> None:
    r = client.get(f"/api/v1/verify/jobs/{uuid.uuid4()}", headers=auth_headers["verifier"])
    assert r.status_code == 404


# --- the prune command --------------------------------------------------------


def test_prune_command_skips_recent_orphans(db: Session, upload_dir: Path) -> None:
    """A file written by a request whose row has not committed yet must survive."""
    from app.scripts.prune_uploads import _orphan_files

    root = upload_dir / "verify"
    root.mkdir(parents=True)
    just_written = root / "in-flight.png"
    just_written.write_bytes(png_bytes())

    now = datetime.now(UTC)
    assert _orphan_files(set(), now) == []


def test_prune_command_finds_an_old_orphan(db: Session, upload_dir: Path) -> None:
    import os

    from app.scripts.prune_uploads import ORPHAN_GRACE, _orphan_files

    root = upload_dir / "verify"
    root.mkdir(parents=True)
    stale = root / "orphan.png"
    stale.write_bytes(png_bytes())
    old = (datetime.now(UTC) - ORPHAN_GRACE - timedelta(minutes=5)).timestamp()
    os.utime(stale, (old, old))

    assert _orphan_files(set(), datetime.now(UTC)) == [str(stale)]


def test_prune_command_never_lists_a_referenced_file(db: Session, upload_dir: Path) -> None:
    import os

    from app.scripts.prune_uploads import ORPHAN_GRACE, _orphan_files

    row = uploads.store(db, png_bytes())
    db.flush()
    old = (datetime.now(UTC) - ORPHAN_GRACE - timedelta(hours=1)).timestamp()
    os.utime(row.path, (old, old))

    assert _orphan_files({row.path}, datetime.now(UTC)) == []
