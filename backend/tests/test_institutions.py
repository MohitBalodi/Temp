"""Admin CRUD for institutions, their keypairs and their first user."""

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Certificate, Institution, User
from app.services.signing import CertificateRecord, private_key_path, verify_record
from tests.conftest import PASSWORD

URL = "/api/v1/institutions"
LOGIN_URL = "/api/v1/auth/login"
CERTS_URL = "/api/v1/certificates"

Headers = dict[str, dict[str, str]]


def new_institution(**overrides: Any) -> dict[str, Any]:
    body = {
        "name": "  Riverdale   Institute of Science ",
        "code": "rvs-01",
        "admin_email": "Registrar@RVS.test",
    }
    body.update(overrides)
    return body


def cert_payload(**overrides: Any) -> dict[str, Any]:
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


# --- create -------------------------------------------------------------------


def test_create_makes_keypair_user_and_password(
    client: TestClient, auth_headers: Headers, db: Session, keys_dir: Path
) -> None:
    r = client.post(URL, json=new_institution(), headers=auth_headers["admin"])

    assert r.status_code == 201, r.text
    body = r.json()
    # Name is cleaned, code normalized, email lowercased.
    assert body["institution"]["name"] == "Riverdale Institute of Science"
    assert body["institution"]["code"] == "RVS01"
    assert body["institution"]["is_active"] is True
    assert body["user"]["email"] == "registrar@rvs.test"
    assert body["user"]["role"] == "institution"
    assert body["user"]["institution"]["code"] == "RVS01"

    # The private key is on disk, the public key in the row, and they match.
    assert private_key_path("RVS01").is_file()
    assert "BEGIN PUBLIC KEY" in body["institution"]["public_key"]

    # The password is returned once, is not trivial, and is not the stored hash.
    password = body["password"]
    assert len(password) >= 12
    user = db.scalar(select(User).where(User.email == "registrar@rvs.test"))
    assert user is not None
    assert password not in user.password_hash

    # And it actually works.
    login = client.post(LOGIN_URL, json={"email": "registrar@rvs.test", "password": password})
    assert login.status_code == 200


def test_created_institution_can_issue_a_verifiable_certificate(
    client: TestClient, auth_headers: Headers, db: Session
) -> None:
    created = client.post(URL, json=new_institution(), headers=auth_headers["admin"]).json()
    token = client.post(
        LOGIN_URL, json={"email": "registrar@rvs.test", "password": created["password"]}
    ).json()["access_token"]

    cert = client.post(
        CERTS_URL,
        json=cert_payload(cert_number="RVS2024PH0001"),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert cert.status_code == 201, cert.text
    row = db.get(Certificate, cert.json()["id"])
    assert row is not None
    record = CertificateRecord(
        cert_number=row.cert_number,
        institution_code="RVS01",
        student_name=row.student_name,
        roll_number=row.roll_number,
        programme=row.programme,
        year_of_passing=row.year_of_passing,
        cgpa=row.cgpa,
        marks=row.marks,
        issue_date=row.issue_date,
    )
    # Signed with the key generated at creation time.
    assert verify_record(created["institution"]["public_key"], record, row.signature) is True


def test_create_is_audited_without_the_password(
    client: TestClient, auth_headers: Headers, db: Session
) -> None:
    body = client.post(URL, json=new_institution(), headers=auth_headers["admin"]).json()

    actions = {
        row.action: row
        for row in db.scalars(
            select(AuditLog).where(AuditLog.action.in_(["institution.create", "user.create"]))
        )
    }
    assert set(actions) == {"institution.create", "user.create"}
    assert actions["institution.create"].meta["code"] == "RVS01"
    for row in actions.values():
        assert body["password"] not in str(row.meta)


def test_duplicate_code_or_email_is_rejected(client: TestClient, auth_headers: Headers) -> None:
    client.post(URL, json=new_institution(), headers=auth_headers["admin"])

    same_code = client.post(
        URL, json=new_institution(admin_email="other@rvs.test"), headers=auth_headers["admin"]
    )
    same_email = client.post(URL, json=new_institution(code="RVS02"), headers=auth_headers["admin"])
    # The seeded fixture institution is TST.
    existing = client.post(
        URL,
        json=new_institution(code="TST", admin_email="new@tst.test"),
        headers=auth_headers["admin"],
    )

    assert same_code.status_code == 409
    assert same_code.json()["error"]["code"] == "duplicate_code"
    assert same_email.status_code == 409
    assert same_email.json()["error"]["code"] == "duplicate_email"
    assert existing.status_code == 409


def test_create_rejects_bad_input(client: TestClient, auth_headers: Headers) -> None:
    for body in (
        new_institution(name="   "),
        new_institution(code="!!"),
        new_institution(admin_email="not-an-email"),
    ):
        r = client.post(URL, json=body, headers=auth_headers["admin"])
        assert r.status_code == 422, body


# --- list, get, update ---------------------------------------------------------


def test_list_includes_counts(client: TestClient, auth_headers: Headers) -> None:
    client.post(CERTS_URL, json=cert_payload(), headers=auth_headers["institution"])

    body = client.get(URL, headers=auth_headers["admin"]).json()

    rows = {i["code"]: i for i in body["items"]}
    assert body["total"] == 2
    assert rows["TST"]["certificate_count"] == 1
    assert rows["TST"]["user_count"] == 1
    assert rows["OTH"]["certificate_count"] == 0


def test_update_changes_name_and_active_flag(
    client: TestClient, auth_headers: Headers, db: Session
) -> None:
    institution = db.scalar(select(Institution).where(Institution.code == "TST"))
    assert institution is not None

    renamed = client.patch(
        f"{URL}/{institution.id}", json={"name": "Test Institute"}, headers=auth_headers["admin"]
    )
    deactivated = client.patch(
        f"{URL}/{institution.id}", json={"is_active": False}, headers=auth_headers["admin"]
    )

    assert renamed.json()["name"] == "Test Institute"
    assert deactivated.json()["is_active"] is False
    assert db.scalar(select(AuditLog).where(AuditLog.action == "institution.update")) is not None


def test_deactivating_blocks_its_users_from_signing_in(
    client: TestClient, auth_headers: Headers, users: dict[str, User], db: Session
) -> None:
    institution = db.scalar(select(Institution).where(Institution.code == "TST"))
    assert institution is not None
    client.patch(
        f"{URL}/{institution.id}", json={"is_active": False}, headers=auth_headers["admin"]
    )

    blocked = client.post(
        LOGIN_URL, json={"email": users["institution"].email, "password": PASSWORD}
    )
    still_fine = client.post(
        LOGIN_URL, json={"email": users["verifier"].email, "password": PASSWORD}
    )

    assert blocked.status_code == 401
    assert still_fine.status_code == 200


def test_get_unknown_institution_is_404(client: TestClient, auth_headers: Headers) -> None:
    assert client.get(f"{URL}/9999", headers=auth_headers["admin"]).status_code == 404
    assert (
        client.patch(f"{URL}/9999", json={"name": "x"}, headers=auth_headers["admin"]).status_code
        == 404
    )


# --- delete --------------------------------------------------------------------


def test_delete_is_refused_when_certificates_exist(
    client: TestClient, auth_headers: Headers, db: Session
) -> None:
    client.post(CERTS_URL, json=cert_payload(), headers=auth_headers["institution"])
    institution = db.scalar(select(Institution).where(Institution.code == "TST"))
    assert institution is not None

    r = client.delete(f"{URL}/{institution.id}", headers=auth_headers["admin"])

    assert r.status_code == 409
    assert r.json()["error"]["code"] == "institution_has_certificates"
    assert "Deactivate" in r.json()["error"]["message"]
    assert db.get(Institution, institution.id) is not None


def test_delete_removes_an_institution_that_never_issued(
    client: TestClient, auth_headers: Headers, db: Session, keys_dir: Path
) -> None:
    created = client.post(URL, json=new_institution(), headers=auth_headers["admin"]).json()
    institution_id = created["institution"]["id"]

    r = client.delete(f"{URL}/{institution_id}", headers=auth_headers["admin"])

    assert r.status_code == 204
    assert db.get(Institution, institution_id) is None
    assert db.scalar(select(User).where(User.email == "registrar@rvs.test")) is None
    # The key file is left on disk on purpose: removing key material is a
    # deliberate, separate act.
    assert private_key_path("RVS01").is_file()


# --- access ---------------------------------------------------------------------


def test_institutions_are_admin_only(client: TestClient, auth_headers: Headers) -> None:
    assert client.get(URL).status_code == 401
    assert client.get(URL, headers=auth_headers["institution"]).status_code == 403
    assert client.get(URL, headers=auth_headers["verifier"]).status_code == 403
    assert (
        client.post(URL, json=new_institution(), headers=auth_headers["institution"]).status_code
        == 403
    )
    assert client.delete(f"{URL}/1", headers=auth_headers["verifier"]).status_code == 403
