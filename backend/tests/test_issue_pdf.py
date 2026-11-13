"""Issuance: QR payload, the generated PDF, and GET /certificates/{id}/pdf."""

import io
from pathlib import Path
from typing import Any

import fitz
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pyzbar.pyzbar import decode as decode_qr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Certificate, Institution, User
from app.services import certificates as service
from app.services.hashing import sha256_bytes, sha256_file
from app.services.pdf_issue import issued_pdf_path
from app.services.qr import PREFIX, QrPayload, QrPayloadError, build_payload, parse_payload
from app.services.signing import CertificateRecord, verify_record
from tests.test_certificates import HEADER, row

URL = "/api/v1/certificates"
Headers = dict[str, dict[str, str]]


def payload(**overrides: Any) -> dict[str, Any]:
    body = {
        "cert_number": "TST-2024-9001",
        "student_name": "Aarav Sharma",
        "roll_number": "21cs901",
        "programme": "B.Tech Computer Science",
        "year_of_passing": 2024,
        "cgpa": "8.5",
        "marks": None,
        "issue_date": "2024-07-15",
    }
    body.update(overrides)
    return body


def create(client: TestClient, headers: Headers, **overrides: Any) -> dict[str, Any]:
    r = client.post(URL, json=payload(**overrides), headers=headers["institution"])
    assert r.status_code == 201, r.text
    return r.json()


def qr_payloads_in_pdf(pdf_bytes: bytes) -> list[str]:
    """Every QR payload decodable from page 1 — from the embedded images first,
    falling back to a raster of the whole page."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[0]
    found: list[str] = []
    for image in page.get_images(full=True):
        data = doc.extract_image(image[0])["image"]
        found += [d.data.decode() for d in decode_qr(Image.open(io.BytesIO(data)))]
    if not found:
        pix = page.get_pixmap(dpi=250)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        found += [d.data.decode() for d in decode_qr(img)]
    doc.close()
    return found


# --- QR payload ---------------------------------------------------------------


def test_payload_round_trips() -> None:
    signature = "abcDEF-123_xyz"
    text = build_payload("TST20249001", "TST", signature)

    assert text == f"{PREFIX}|TST20249001|TST|{signature}"
    assert parse_payload(text) == QrPayload("TST20249001", "TST", signature)
    assert parse_payload(text).encode() == text


def test_payload_normalizes_ids() -> None:
    text = build_payload("tst-2024/9001", " tst ", "sig123")

    assert text == f"{PREFIX}|TST20249001|TST|sig123"
    assert parse_payload(f"{PREFIX}|tst-2024/9001|tst|sig123").cert_number == "TST20249001"


def test_payload_survives_scanner_whitespace() -> None:
    assert parse_payload(f"  {PREFIX}|TST1|TST|sig123\n").cert_number == "TST1"


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "AVA1|TST1|TST",  # too few parts
        "AVA1|TST1|TST|sig|extra",  # too many parts
        "AVA2|TST1|TST|sig123",  # unknown prefix
        "AVA1||TST|sig123",  # no cert number
        "AVA1|TST1||sig123",  # no institution code
        "AVA1|TST1|TST|",  # no signature
        "AVA1|TST1|TST|sig+123=",  # not base64url
    ],
)
def test_payload_rejects_malformed(text: str) -> None:
    with pytest.raises(QrPayloadError):
        parse_payload(text)


# --- issuance -----------------------------------------------------------------


def test_create_stores_pdf_once_with_matching_hash(
    client: TestClient, auth_headers: Headers, db: Session, issued_dir: Path
) -> None:
    body = create(client, auth_headers)
    cert = db.get(Certificate, body["id"])
    assert cert is not None

    path = issued_pdf_path(cert.id)
    assert path.is_file()
    assert path.parent == issued_dir
    assert cert.file_sha256 == sha256_file(path)
    assert body["file_sha256"] == cert.file_sha256
    assert path.read_bytes().startswith(b"%PDF-")


def test_pdf_endpoint_serves_the_stored_bytes(client: TestClient, auth_headers: Headers) -> None:
    body = create(client, auth_headers)
    stored = issued_pdf_path(body["id"]).read_bytes()

    first = client.get(f"{URL}/{body['id']}/pdf", headers=auth_headers["institution"])
    second = client.get(f"{URL}/{body['id']}/pdf", headers=auth_headers["admin"])

    assert first.status_code == 200
    assert first.headers["content-type"] == "application/pdf"
    assert body["cert_number"] in first.headers["content-disposition"]
    assert first.content == stored
    assert sha256_bytes(first.content) == body["file_sha256"]
    # Served, not rebuilt: a second request returns identical bytes.
    assert second.content == first.content


def test_pdf_carries_a_decodable_qr_matching_the_record(
    client: TestClient, auth_headers: Headers, db: Session
) -> None:
    body = create(client, auth_headers)
    cert = db.get(Certificate, body["id"])
    assert cert is not None
    institution = db.get(Institution, cert.institution_id)
    assert institution is not None

    payloads = qr_payloads_in_pdf(issued_pdf_path(cert.id).read_bytes())
    assert len(payloads) == 1

    parsed = parse_payload(payloads[0])
    assert parsed.cert_number == cert.cert_number
    assert parsed.institution_code == institution.code
    assert parsed.signature == cert.signature

    # The signature carried by the QR verifies against the institution key.
    record = CertificateRecord(
        cert_number=cert.cert_number,
        institution_code=institution.code,
        student_name=cert.student_name,
        roll_number=cert.roll_number,
        programme=cert.programme,
        year_of_passing=cert.year_of_passing,
        cgpa=cert.cgpa,
        marks=cert.marks,
        issue_date=cert.issue_date,
    )
    assert verify_record(institution.public_key, record, parsed.signature) is True


def test_import_issues_a_pdf_for_every_row(
    client: TestClient, auth_headers: Headers, db: Session
) -> None:
    content = ("\n".join([HEADER, row(901), row(902), row(903)]) + "\n").encode()

    r = client.post(
        f"{URL}/import",
        headers=auth_headers["institution"],
        files={"file": ("c.csv", content, "text/csv")},
    )

    assert r.status_code == 200, r.text
    assert r.json() == {"imported": 3}
    certs = db.scalars(select(Certificate)).all()
    assert len(certs) == 3
    for cert in certs:
        assert cert.file_sha256 == sha256_file(issued_pdf_path(cert.id))


def test_marks_only_certificate_issues_too(client: TestClient, auth_headers: Headers) -> None:
    body = create(client, auth_headers, cgpa=None, marks="78.4")

    assert body["file_sha256"] is not None
    assert issued_pdf_path(body["id"]).is_file()


# --- access and failure modes -------------------------------------------------


def test_pdf_requires_the_right_role(client: TestClient, auth_headers: Headers) -> None:
    body = create(client, auth_headers)
    url = f"{URL}/{body['id']}/pdf"

    assert client.get(url).status_code == 401
    assert client.get(url, headers=auth_headers["verifier"]).status_code == 403
    # Another institution cannot tell absent from foreign.
    assert client.get(url, headers=auth_headers["other_institution"]).status_code == 404


def test_pdf_missing_on_disk_is_reported_not_regenerated(
    client: TestClient, auth_headers: Headers
) -> None:
    body = create(client, auth_headers)
    issued_pdf_path(body["id"]).unlink()

    r = client.get(f"{URL}/{body['id']}/pdf", headers=auth_headers["institution"])

    assert r.status_code == 404
    assert r.json()["error"]["code"] == "pdf_not_available"
    assert not issued_pdf_path(body["id"]).is_file()


def test_backfill_issues_missing_pdfs_and_is_idempotent(
    client: TestClient, auth_headers: Headers, db: Session
) -> None:
    body = create(client, auth_headers)
    cert = db.get(Certificate, body["id"])
    assert cert is not None

    # A certificate from before issuance existed: no hash, no file.
    issued_pdf_path(cert.id).unlink()
    cert.file_sha256 = None
    db.flush()

    assert service.needs_pdf(cert) is True
    assert service.backfill_pdf(db, cert) == "missing_hash"

    path = issued_pdf_path(cert.id)
    assert path.is_file()
    assert cert.file_sha256 == sha256_file(path)

    audited = db.scalars(
        select(AuditLog).where(AuditLog.action == "certificate.pdf_backfill")
    ).all()
    assert len(audited) == 1
    assert audited[0].meta["cert_number"] == cert.cert_number
    assert audited[0].meta["reason"] == "missing_hash"

    # Running again is a no-op: same file, same hash.
    stable = cert.file_sha256
    assert service.needs_pdf(cert) is False
    assert sha256_file(path) == stable


def test_backfill_rebuilds_when_only_the_file_is_missing(
    client: TestClient, auth_headers: Headers, db: Session, users: dict[str, User]
) -> None:
    body = create(client, auth_headers)
    cert = db.get(Certificate, body["id"])
    assert cert is not None
    issued_pdf_path(cert.id).unlink()

    assert service.needs_pdf(cert) is True
    assert service.backfill_pdf(db, cert, actor_id=users["admin"].id) == "missing_file"
    assert cert.file_sha256 == sha256_file(issued_pdf_path(cert.id))
