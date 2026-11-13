"""POST /certificates/{id}/revoke and what verification says afterwards."""

from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Certificate
from app.services.hashing import sha256_file
from app.services.pdf_issue import issued_pdf_path
from app.services.qr import build_payload

URL = "/api/v1/certificates"
VERIFY_ID_URL = "/api/v1/verify/id"
VERIFY_QR_URL = "/api/v1/verify/qr"

Headers = dict[str, dict[str, str]]


def payload(**overrides: Any) -> dict[str, Any]:
    body = {
        "cert_number": "TST2024CS0001",
        "student_name": "Aarav Sharma",
        "roll_number": "21CS001",
        "programme": "B.Tech Computer Science",
        "year_of_passing": 2024,
        "cgpa": "8.5",
        "marks": None,
        "issue_date": "2024-07-15",
    }
    body.update(overrides)
    return body


def issue(client: TestClient, headers: Headers, **overrides: Any) -> dict[str, Any]:
    r = client.post(URL, json=payload(**overrides), headers=headers["institution"])
    assert r.status_code == 201, r.text
    return r.json()


def revoke(
    client: TestClient, headers: dict[str, str], cert_id: str, reason: str = "Issued in error"
):
    return client.post(f"{URL}/{cert_id}/revoke", json={"reason": reason}, headers=headers)


def test_revoke_sets_status_and_audits_the_reason(
    client: TestClient, auth_headers: Headers, db: Session
) -> None:
    cert = issue(client, auth_headers)

    r = revoke(client, auth_headers["institution"], cert["id"], "Duplicate  record ")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "revoked"
    assert body["revoked_at"] is not None

    row = db.get(Certificate, cert["id"])
    assert row is not None
    assert row.status == "revoked"
    assert row.revoked_at is not None

    logged = db.scalar(select(AuditLog).where(AuditLog.action == "certificate.revoke"))
    assert logged is not None
    assert logged.meta["cert_number"] == cert["cert_number"]
    # Whitespace is collapsed, like every other stored text.
    assert logged.meta["reason"] == "Duplicate record"


def test_revoking_leaves_the_record_and_its_pdf_untouched(
    client: TestClient, auth_headers: Headers, db: Session
) -> None:
    cert = issue(client, auth_headers)
    before = issued_pdf_path(cert["id"]).read_bytes()

    revoke(client, auth_headers["institution"], cert["id"])

    row = db.get(Certificate, cert["id"])
    assert row is not None
    # The signature still covers the record as issued; only the status moved.
    assert row.signature == cert["signature"]
    assert row.file_sha256 == cert["file_sha256"]
    assert issued_pdf_path(cert["id"]).read_bytes() == before
    assert sha256_file(issued_pdf_path(cert["id"])) == row.file_sha256


def test_reason_is_required(client: TestClient, auth_headers: Headers) -> None:
    cert = issue(client, auth_headers)

    for reason in ("", "  ", "ab"):
        r = client.post(
            f"{URL}/{cert['id']}/revoke",
            json={"reason": reason},
            headers=auth_headers["institution"],
        )
        assert r.status_code == 422, reason
    assert (
        client.post(
            f"{URL}/{cert['id']}/revoke", json={}, headers=auth_headers["institution"]
        ).status_code
        == 422
    )


def test_revoking_twice_is_rejected(client: TestClient, auth_headers: Headers) -> None:
    cert = issue(client, auth_headers)
    revoke(client, auth_headers["institution"], cert["id"])

    again = revoke(client, auth_headers["institution"], cert["id"])

    assert again.status_code == 409
    assert again.json()["error"]["code"] == "already_revoked"


def test_only_the_owning_institution_can_revoke(client: TestClient, auth_headers: Headers) -> None:
    cert = issue(client, auth_headers)

    assert revoke(client, {}, cert["id"]).status_code == 401
    assert revoke(client, auth_headers["verifier"], cert["id"]).status_code == 403
    # An admin is not an issuer.
    assert revoke(client, auth_headers["admin"], cert["id"]).status_code == 403
    # Another institution cannot tell absent from foreign.
    assert revoke(client, auth_headers["other_institution"], cert["id"]).status_code == 404


def test_verification_reports_revoked_by_number_and_by_qr(
    client: TestClient, auth_headers: Headers
) -> None:
    cert = issue(client, auth_headers)
    revoke(client, auth_headers["institution"], cert["id"], "Withdrawn by the department")

    by_number = client.post(
        VERIFY_ID_URL, json={"cert_number": cert["cert_number"]}, headers=auth_headers["verifier"]
    ).json()
    by_qr = client.post(
        VERIFY_QR_URL,
        json={"payload": build_payload(cert["cert_number"], "TST", cert["signature"])},
        headers=auth_headers["verifier"],
    ).json()

    assert by_number["result"] == "REVOKED"
    assert by_qr["result"] == "REVOKED"
    checks = {c["name"]: c for c in by_number["checks"]}
    assert checks["revocation"]["status"] == "fail"
    assert checks["registry_lookup"]["status"] == "pass"
    # A genuine QR still verifies; revocation is what decides the result.
    assert {c["name"]: c["status"] for c in by_qr["checks"]}["qr_signature"] == "pass"
    # The reason is for the institution's trail, not for the verifier.
    assert "Withdrawn by the department" not in str(by_number)
