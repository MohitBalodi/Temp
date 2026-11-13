"""POST /verify/id, POST /verify/qr and GET /verifications/{id}."""

from datetime import UTC, date, datetime
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Certificate, User, Verification
from app.services.qr import build_payload
from app.services.signing import CertificateRecord, load_private_key, sign_record

CERTS_URL = "/api/v1/certificates"
VERIFY_ID_URL = "/api/v1/verify/id"
VERIFY_QR_URL = "/api/v1/verify/qr"
VERIFICATIONS_URL = "/api/v1/verifications"

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
    r = client.post(CERTS_URL, json=payload(**overrides), headers=headers["institution"])
    assert r.status_code == 201, r.text
    return r.json()


def checks_by_name(body: dict[str, Any]) -> dict[str, str]:
    return {c["name"]: c["status"] for c in body["checks"]}


def qr_for(cert: dict[str, Any], code: str = "TST") -> str:
    return build_payload(cert["cert_number"], code, cert["signature"])


# --- verify by number ---------------------------------------------------------


def test_genuine_number_verifies_and_is_recorded(
    client: TestClient, auth_headers: Headers, users: dict[str, User], db: Session
) -> None:
    cert = issue(client, auth_headers)

    r = client.post(
        VERIFY_ID_URL, json={"cert_number": cert["cert_number"]}, headers=auth_headers["verifier"]
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["result"] == "VERIFIED"
    assert body["method"] == "id"
    assert checks_by_name(body) == {
        "registry_lookup": "pass",
        "revocation": "pass",
        "record_signature": "pass",
        "qr_signature": "skipped",
    }
    # The record's fields come back with the result.
    assert body["certificate"]["student_name"] == "Aarav Sharma"
    assert body["certificate"]["cert_number"] == cert["cert_number"]
    assert body["extracted_fields"] == {"cert_number": cert["cert_number"]}

    stored = db.get(Verification, body["id"])
    assert stored is not None
    assert stored.verifier_id == users["verifier"].id
    assert stored.certificate_id is not None
    assert len(stored.checks) == 4

    logged = db.scalars(select(AuditLog).where(AuditLog.action == "verification.create")).all()
    assert len(logged) == 1
    assert logged[0].meta["result"] == "VERIFIED"
    assert logged[0].meta["method"] == "id"


def test_number_is_normalized_before_lookup(client: TestClient, auth_headers: Headers) -> None:
    cert = issue(client, auth_headers)

    r = client.post(
        VERIFY_ID_URL, json={"cert_number": " tst-2024/cs 0001 "}, headers=auth_headers["verifier"]
    )

    assert r.status_code == 200
    assert r.json()["result"] == "VERIFIED"
    assert r.json()["certificate"]["id"] == cert["id"]


def test_unknown_number_is_manual_review(client: TestClient, auth_headers: Headers) -> None:
    r = client.post(
        VERIFY_ID_URL, json={"cert_number": "TST9999"}, headers=auth_headers["verifier"]
    )

    assert r.status_code == 200
    body = r.json()
    assert body["result"] == "MANUAL_REVIEW"
    assert body["certificate"] is None
    assert checks_by_name(body)["registry_lookup"] == "fail"
    # Still recorded, with what was looked up.
    assert body["extracted_fields"] == {"cert_number": "TST9999"}


def test_revoked_certificate_is_revoked(
    client: TestClient, auth_headers: Headers, db: Session
) -> None:
    cert = issue(client, auth_headers)
    row = db.get(Certificate, cert["id"])
    assert row is not None
    row.status = "revoked"
    row.revoked_at = datetime(2025, 5, 6, tzinfo=UTC)
    db.flush()

    r = client.post(
        VERIFY_ID_URL, json={"cert_number": cert["cert_number"]}, headers=auth_headers["verifier"]
    )

    assert r.json()["result"] == "REVOKED"
    assert checks_by_name(r.json())["revocation"] == "fail"


# --- verify by QR -------------------------------------------------------------


def test_genuine_qr_verifies(client: TestClient, auth_headers: Headers, db: Session) -> None:
    cert = issue(client, auth_headers)

    r = client.post(VERIFY_QR_URL, json={"payload": qr_for(cert)}, headers=auth_headers["verifier"])

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["result"] == "VERIFIED"
    assert body["method"] == "qr"
    assert checks_by_name(body)["qr_signature"] == "pass"
    assert body["extracted_fields"] == {
        "cert_number": cert["cert_number"],
        "institution_code": "TST",
    }
    assert db.get(Verification, body["id"]) is not None


def test_qr_with_another_certificates_number_is_a_mismatch(
    client: TestClient, auth_headers: Headers
) -> None:
    first = issue(client, auth_headers)
    second = issue(client, auth_headers, cert_number="TST2024CS0002", roll_number="21CS002")

    # A real QR from `first`, with the number swapped for `second`.
    swapped = build_payload(second["cert_number"], "TST", first["signature"])
    r = client.post(VERIFY_QR_URL, json={"payload": swapped}, headers=auth_headers["verifier"])

    body = r.json()
    assert body["result"] == "MISMATCH"
    assert checks_by_name(body)["qr_signature"] == "fail"
    # The record it points at is still shown, so the verifier can see the conflict.
    assert body["certificate"]["cert_number"] == second["cert_number"]


def test_tampered_qr_signature_is_a_mismatch(client: TestClient, auth_headers: Headers) -> None:
    cert = issue(client, auth_headers)
    signature = cert["signature"]
    flipped = ("B" if signature[0] != "B" else "C") + signature[1:]

    r = client.post(
        VERIFY_QR_URL,
        json={"payload": build_payload(cert["cert_number"], "TST", flipped)},
        headers=auth_headers["verifier"],
    )

    assert r.json()["result"] == "MISMATCH"
    assert checks_by_name(r.json())["qr_signature"] == "fail"


def test_qr_resigned_for_another_programme_is_a_mismatch(
    client: TestClient, auth_headers: Headers, keys_dir: object
) -> None:
    """Someone edits the printed programme and re-signs with the real key: the
    registry still holds the original, so the signature cannot match both."""
    cert = issue(client, auth_headers)
    forged = sign_record(
        load_private_key("TST"),
        CertificateRecord(
            cert_number=cert["cert_number"],
            institution_code="TST",
            student_name=cert["student_name"],
            roll_number=cert["roll_number"],
            programme="B.Tech Artificial Intelligence",
            year_of_passing=cert["year_of_passing"],
            cgpa=cert["cgpa"],
            marks=cert["marks"],
            issue_date=date.fromisoformat(cert["issue_date"]),
        ),
    )

    r = client.post(
        VERIFY_QR_URL,
        json={"payload": build_payload(cert["cert_number"], "TST", forged)},
        headers=auth_headers["verifier"],
    )

    assert r.json()["result"] == "MISMATCH"


def test_qr_for_an_unknown_number_is_manual_review(
    client: TestClient, auth_headers: Headers
) -> None:
    r = client.post(
        VERIFY_QR_URL,
        json={"payload": build_payload("TST9999", "TST", "c2lnbmF0dXJl")},
        headers=auth_headers["verifier"],
    )

    body = r.json()
    assert body["result"] == "MANUAL_REVIEW"
    assert checks_by_name(body)["qr_signature"] == "skipped"


def test_unreadable_payload_is_rejected_not_recorded(
    client: TestClient, auth_headers: Headers, db: Session
) -> None:
    r = client.post(
        VERIFY_QR_URL,
        json={"payload": "https://example.test/not-a-cert"},
        headers=auth_headers["verifier"],
    )

    assert r.status_code == 422
    assert r.json()["error"]["code"] == "qr_payload_invalid"
    assert db.scalars(select(Verification)).all() == []


# --- access -------------------------------------------------------------------


def test_only_verifiers_and_admins_can_verify(client: TestClient, auth_headers: Headers) -> None:
    body = {"cert_number": "TST2024CS0001"}

    assert client.post(VERIFY_ID_URL, json=body).status_code == 401
    assert (
        client.post(VERIFY_ID_URL, json=body, headers=auth_headers["institution"]).status_code
        == 403
    )
    assert client.post(VERIFY_ID_URL, json=body, headers=auth_headers["admin"]).status_code == 200


def test_verification_is_readable_by_its_verifier_and_admins(
    client: TestClient, auth_headers: Headers
) -> None:
    cert = issue(client, auth_headers)
    created = client.post(
        VERIFY_ID_URL, json={"cert_number": cert["cert_number"]}, headers=auth_headers["verifier"]
    ).json()

    url = f"{VERIFICATIONS_URL}/{created['id']}"
    own = client.get(url, headers=auth_headers["verifier"])
    as_admin = client.get(url, headers=auth_headers["admin"])

    assert own.status_code == 200
    assert own.json()["result"] == "VERIFIED"
    assert own.json()["checks"] == created["checks"]
    assert as_admin.status_code == 200
    # An institution has no business reading verifier activity.
    assert client.get(url, headers=auth_headers["institution"]).status_code == 403


def test_another_verifier_cannot_read_someone_elses_verification(
    client: TestClient, auth_headers: Headers, db: Session, users: dict[str, User]
) -> None:
    cert = issue(client, auth_headers)
    created = client.post(
        VERIFY_ID_URL, json={"cert_number": cert["cert_number"]}, headers=auth_headers["admin"]
    ).json()

    # The admin ran it, so the verifier must not see it.
    r = client.get(f"{VERIFICATIONS_URL}/{created['id']}", headers=auth_headers["verifier"])

    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"
