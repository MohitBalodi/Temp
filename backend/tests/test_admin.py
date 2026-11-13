"""Login auditing, GET /admin/audit and GET /admin/stats."""

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Certificate, User
from tests.conftest import PASSWORD

LOGIN_URL = "/api/v1/auth/login"
AUDIT_URL = "/api/v1/admin/audit"
STATS_URL = "/api/v1/admin/stats"
CERTS_URL = "/api/v1/certificates"
VERIFY_ID_URL = "/api/v1/verify/id"

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


def rows(db: Session, action: str) -> list[AuditLog]:
    return list(db.scalars(select(AuditLog).where(AuditLog.action == action)))


# --- login auditing -----------------------------------------------------------


def test_successful_login_is_audited(
    client: TestClient, users: dict[str, User], db: Session
) -> None:
    r = client.post(LOGIN_URL, json={"email": users["verifier"].email, "password": PASSWORD})

    assert r.status_code == 200
    logged = rows(db, "auth.login")
    assert len(logged) == 1
    assert logged[0].actor_id == users["verifier"].id
    assert logged[0].meta == {"role": "verifier"}
    # The password never reaches the log, and neither does a token.
    assert "password" not in str(logged[0].meta)


def test_failed_login_records_only_the_email_domain(
    client: TestClient, users: dict[str, User], db: Session
) -> None:
    r = client.post(LOGIN_URL, json={"email": "Someone@Example.TEST", "password": "wrong"})

    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_credentials"
    logged = rows(db, "auth.login_failed")
    assert len(logged) == 1
    assert logged[0].actor_id is None
    assert logged[0].meta == {"email_domain": "example.test"}
    # The local part is not stored anywhere in the row.
    assert "someone" not in str(logged[0].meta).lower()
    assert "wrong" not in str(logged[0].meta)


def test_wrong_password_for_a_real_user_is_a_failure_too(
    client: TestClient, users: dict[str, User], db: Session
) -> None:
    client.post(LOGIN_URL, json={"email": users["admin"].email, "password": "not-it"})

    logged = rows(db, "auth.login_failed")
    assert len(logged) == 1
    assert logged[0].meta == {"email_domain": "t.test"}
    assert rows(db, "auth.login") == []


def test_inactive_user_login_is_recorded_as_a_failure(
    client: TestClient, users: dict[str, User], db: Session
) -> None:
    client.post(LOGIN_URL, json={"email": users["inactive"].email, "password": PASSWORD})

    assert len(rows(db, "auth.login_failed")) == 1
    assert rows(db, "auth.login") == []


# --- GET /admin/audit ---------------------------------------------------------


def test_audit_log_is_admin_only(client: TestClient, auth_headers: Headers) -> None:
    assert client.get(AUDIT_URL).status_code == 401
    assert client.get(AUDIT_URL, headers=auth_headers["verifier"]).status_code == 403
    assert client.get(AUDIT_URL, headers=auth_headers["institution"]).status_code == 403
    assert client.get(AUDIT_URL, headers=auth_headers["admin"]).status_code == 200


def test_audit_log_lists_newest_first_with_the_actor(
    client: TestClient, auth_headers: Headers, users: dict[str, User]
) -> None:
    client.post(CERTS_URL, json=payload(), headers=auth_headers["institution"])

    body = client.get(AUDIT_URL, headers=auth_headers["admin"]).json()

    assert body["total"] >= 1
    first = body["items"][0]
    assert first["action"] == "certificate.create"
    assert first["actor_id"] == users["institution"].id
    assert first["actor_email"] == users["institution"].email
    assert first["meta"]["cert_number"] == "TST2024CS0001"


def test_audit_log_filters_by_action_prefix(
    client: TestClient, auth_headers: Headers, users: dict[str, User]
) -> None:
    client.post(CERTS_URL, json=payload(), headers=auth_headers["institution"])
    client.post(LOGIN_URL, json={"email": users["verifier"].email, "password": PASSWORD})
    client.post(LOGIN_URL, json={"email": "nobody@other.test", "password": "wrong"})

    certificates = client.get(
        AUDIT_URL, params={"action": "certificate."}, headers=auth_headers["admin"]
    ).json()
    all_auth = client.get(
        AUDIT_URL, params={"action": "auth."}, headers=auth_headers["admin"]
    ).json()
    successes = client.get(
        AUDIT_URL, params={"action": "auth.login"}, headers=auth_headers["admin"]
    ).json()
    failures = client.get(
        AUDIT_URL, params={"action": "auth.login_failed"}, headers=auth_headers["admin"]
    ).json()

    assert {i["action"] for i in certificates["items"]} == {"certificate.create"}
    assert all_auth["total"] >= 2
    # "auth.login" is a prefix of "auth.login_failed", so it covers both.
    assert successes["total"] == all_auth["total"]
    assert {i["action"] for i in failures["items"]} == {"auth.login_failed"}


def test_audit_log_filters_by_date_range(
    client: TestClient, auth_headers: Headers, db: Session
) -> None:
    # Rows are inserted with explicit timestamps: the append-only trigger
    # rejects UPDATE, so an existing row cannot be backdated.
    for day in (14, 15, 16):
        db.add(
            AuditLog(
                action="test.event",
                entity="test",
                meta={},
                created_at=datetime(2026, 1, day, 9, 0, tzinfo=UTC),
            )
        )
    db.flush()

    def count(**params: str) -> int:
        return client.get(
            AUDIT_URL, params={"action": "test.", **params}, headers=auth_headers["admin"]
        ).json()["total"]

    assert count() == 3
    # Both ends are inclusive of the whole day.
    assert count(date_from="2026-01-15", date_to="2026-01-15") == 1
    assert count(date_from="2026-01-14", date_to="2026-01-15") == 2
    assert count(date_from="2026-01-16") == 1
    assert count(date_to="2026-01-13") == 0


def test_audit_log_paginates(client: TestClient, auth_headers: Headers) -> None:
    for n in range(3):
        client.post(
            CERTS_URL,
            json=payload(cert_number=f"TST2024CS900{n}", roll_number=f"21CS90{n}"),
            headers=auth_headers["institution"],
        )

    first = client.get(
        AUDIT_URL,
        params={"action": "certificate.", "page": 1, "size": 2},
        headers=auth_headers["admin"],
    ).json()
    second = client.get(
        AUDIT_URL,
        params={"action": "certificate.", "page": 2, "size": 2},
        headers=auth_headers["admin"],
    ).json()

    assert first["total"] == 3
    assert len(first["items"]) == 2
    assert len(second["items"]) == 1
    assert {i["id"] for i in first["items"]}.isdisjoint({i["id"] for i in second["items"]})


# --- GET /admin/stats ---------------------------------------------------------


def test_stats_counts_the_registry_and_verifications(
    client: TestClient, auth_headers: Headers, db: Session
) -> None:
    cert = client.post(CERTS_URL, json=payload(), headers=auth_headers["institution"]).json()
    client.post(
        VERIFY_ID_URL, json={"cert_number": cert["cert_number"]}, headers=auth_headers["verifier"]
    )
    client.post(VERIFY_ID_URL, json={"cert_number": "TST9999"}, headers=auth_headers["verifier"])

    body = client.get(STATS_URL, headers=auth_headers["admin"]).json()

    assert body["institutions"] == 2  # the fixture makes TST and OTH
    assert body["users"] == 5
    assert body["certificates"] == 1
    assert body["certificates_revoked"] == 0
    assert body["verifications"] == 2
    assert body["verifications_by_result"] == {
        "VERIFIED": 1,
        "MISMATCH": 0,
        "REVOKED": 0,
        "MANUAL_REVIEW": 1,
    }
    assert body["last_7_days"]["certificates"] == 1
    assert body["last_7_days"]["verifications"] == 2


def test_stats_window_excludes_older_rows(
    client: TestClient, auth_headers: Headers, db: Session
) -> None:
    cert = client.post(CERTS_URL, json=payload(), headers=auth_headers["institution"]).json()
    row = db.get(Certificate, cert["id"])
    assert row is not None
    row.created_at = datetime.now(UTC) - timedelta(days=30)
    db.flush()

    body = client.get(STATS_URL, headers=auth_headers["admin"]).json()

    assert body["certificates"] == 1
    assert body["last_7_days"]["certificates"] == 0


def test_stats_counts_logins_in_the_window(
    client: TestClient, auth_headers: Headers, users: dict[str, User]
) -> None:
    client.post(LOGIN_URL, json={"email": users["verifier"].email, "password": PASSWORD})
    client.post(LOGIN_URL, json={"email": "nobody@other.test", "password": "wrong"})

    body = client.get(STATS_URL, headers=auth_headers["admin"]).json()

    # auth_headers logs every active fixture user in, so successes are >= 1.
    assert body["last_7_days"]["logins"] >= 1
    assert body["last_7_days"]["failed_logins"] == 1


def test_stats_is_admin_only(client: TestClient, auth_headers: Headers) -> None:
    assert client.get(STATS_URL).status_code == 401
    assert client.get(STATS_URL, headers=auth_headers["verifier"]).status_code == 403
    assert client.get(STATS_URL, headers=auth_headers["institution"]).status_code == 403
