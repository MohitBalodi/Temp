"""Verification requests: who may do what, and how a case changes state.

Deliberately narrow. The flow itself (upload, OCR, the engine) is covered
elsewhere; what is new here is an authorization boundary between two
organisations and a small state machine, and those are what break silently.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Certificate, ReviewCase, ReviewStatus, Upload, User, Verification
from app.services import uploads

API = "/api/v1"
UNKNOWN_NUMBER = "TST2099ZZ0001"


def verify_unknown(client: TestClient, headers: dict[str, str]) -> dict:
    """A MANUAL_REVIEW verification: the one thing worth escalating."""
    r = client.post(f"{API}/verify/id", headers=headers, json={"cert_number": UNKNOWN_NUMBER})
    assert r.status_code == 200, r.text
    assert r.json()["result"] == "MANUAL_REVIEW"
    return r.json()


@pytest.fixture
def institution_id(client: TestClient, auth_headers: dict[str, dict[str, str]]) -> int:
    options = client.get(f"{API}/institutions/options", headers=auth_headers["verifier"]).json()
    return next(o["id"] for o in options if o["code"] == "TST")


@pytest.fixture
def case(client: TestClient, auth_headers: dict[str, dict[str, str]], institution_id: int) -> dict:
    """An open request from the verifier to TST."""
    verification = verify_unknown(client, auth_headers["verifier"])
    r = client.post(
        f"{API}/reviews",
        headers=auth_headers["verifier"],
        json={
            "verification_id": verification["id"],
            "institution_id": institution_id,
            "note": "Holder presented a printed copy.",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def fields(cert_number: str = UNKNOWN_NUMBER) -> dict:
    return {
        "cert_number": cert_number,
        "student_name": "Nandini Rao",
        "roll_number": "18CS999",
        "programme": "B.Tech Computer Science and Engineering",
        "year_of_passing": 2022,
        "cgpa": "8.56",
        "marks": None,
        "issue_date": "2022-07-20",
    }


# --- creating ------------------------------------------------------------------


def test_a_verifier_opens_a_request_on_a_result_that_needs_review(case: dict) -> None:
    assert case["status"] == ReviewStatus.PENDING.value
    assert case["decision"] is None
    assert case["institution"]["code"] == "TST"
    assert case["note"] == "Holder presented a printed copy."


def test_an_institution_cannot_open_a_request(
    client: TestClient, auth_headers: dict[str, dict[str, str]], institution_id: int
) -> None:
    verification = verify_unknown(client, auth_headers["verifier"])
    r = client.post(
        f"{API}/reviews",
        headers=auth_headers["institution"],
        json={"verification_id": verification["id"], "institution_id": institution_id},
    )
    assert r.status_code == 403


def test_an_admin_cannot_open_a_request(
    client: TestClient, auth_headers: dict[str, dict[str, str]], institution_id: int
) -> None:
    """The admin is a reader here: an escalation is the verifier's act."""
    verification = verify_unknown(client, auth_headers["verifier"])
    r = client.post(
        f"{API}/reviews",
        headers=auth_headers["admin"],
        json={"verification_id": verification["id"], "institution_id": institution_id},
    )
    assert r.status_code == 403


def test_a_verified_result_cannot_be_escalated(
    client: TestClient,
    db: Session,
    users: dict[str, User],
    auth_headers: dict[str, dict[str, str]],
    institution_id: int,
) -> None:
    """Asking an institution to re-confirm cryptography teaches verifiers to
    distrust it, so only MANUAL_REVIEW and MISMATCH may be sent."""
    verification = Verification(
        verifier_id=users["verifier"].id, method="id", result="VERIFIED", checks=[]
    )
    db.add(verification)
    db.flush()
    r = client.post(
        f"{API}/reviews",
        headers=auth_headers["verifier"],
        json={"verification_id": str(verification.id), "institution_id": institution_id},
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "not_escalatable"


def test_an_unidentified_document_needs_an_institution_chosen(
    client: TestClient, auth_headers: dict[str, dict[str, str]]
) -> None:
    verification = verify_unknown(client, auth_headers["verifier"])
    r = client.post(
        f"{API}/reviews",
        headers=auth_headers["verifier"],
        json={"verification_id": verification["id"]},
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "institution_required"


def test_only_one_request_may_be_open_per_verification(
    client: TestClient, auth_headers: dict[str, dict[str, str]], case: dict, institution_id: int
) -> None:
    r = client.post(
        f"{API}/reviews",
        headers=auth_headers["verifier"],
        json={"verification_id": case["verification_id"], "institution_id": institution_id},
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "request_already_open"


# --- who can see what ----------------------------------------------------------


def test_another_institution_cannot_see_the_case(
    client: TestClient, auth_headers: dict[str, dict[str, str]], case: dict
) -> None:
    """404, not 403: whether a request exists is itself information."""
    r = client.get(f"{API}/reviews/{case['id']}", headers=auth_headers["other_institution"])
    assert r.status_code == 404
    listed = client.get(f"{API}/reviews", headers=auth_headers["other_institution"]).json()
    assert listed["total"] == 0


def test_the_addressed_institution_and_the_admin_both_see_it(
    client: TestClient, auth_headers: dict[str, dict[str, str]], case: dict
) -> None:
    for who in ("institution", "admin", "verifier"):
        r = client.get(f"{API}/reviews/{case['id']}", headers=auth_headers[who])
        assert r.status_code == 200, who


def test_the_institution_sees_the_verification_behind_the_request(
    client: TestClient, auth_headers: dict[str, dict[str, str]], case: dict
) -> None:
    """It cannot judge a document it is not shown."""
    body = client.get(f"{API}/reviews/{case['id']}", headers=auth_headers["institution"]).json()
    assert body["verification"]["result"] == "MANUAL_REVIEW"
    assert body["can_decide"] is True
    assert body["can_reply"] is True


def test_the_admin_may_read_but_not_decide(
    client: TestClient, auth_headers: dict[str, dict[str, str]], case: dict
) -> None:
    body = client.get(f"{API}/reviews/{case['id']}", headers=auth_headers["admin"]).json()
    assert body["can_decide"] is False
    assert body["can_reply"] is False
    r = client.post(
        f"{API}/reviews/{case['id']}/decision",
        headers=auth_headers["admin"],
        json={"decision": "confirmed"},
    )
    assert r.status_code == 403


def test_a_verifier_cannot_answer_their_own_request(
    client: TestClient, auth_headers: dict[str, dict[str, str]], case: dict
) -> None:
    r = client.post(
        f"{API}/reviews/{case['id']}/decision",
        headers=auth_headers["verifier"],
        json={"decision": "confirmed"},
    )
    assert r.status_code == 403


# --- status changes ------------------------------------------------------------


def test_asking_for_more_info_moves_the_case_to_needs_info(
    client: TestClient, auth_headers: dict[str, dict[str, str]], case: dict
) -> None:
    r = client.post(
        f"{API}/reviews/{case['id']}/needs-info",
        headers=auth_headers["institution"],
        json={"body": "Which year was this issued?"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == ReviewStatus.NEEDS_INFO.value
    assert [m["body"] for m in body["messages"]] == ["Which year was this issued?"]


def test_the_verifier_replying_puts_it_back_to_pending(
    client: TestClient, auth_headers: dict[str, dict[str, str]], case: dict
) -> None:
    """needs_info <-> pending: a reply hands the question back."""
    client.post(
        f"{API}/reviews/{case['id']}/needs-info",
        headers=auth_headers["institution"],
        json={"body": "Which year?"},
    )
    r = client.post(
        f"{API}/reviews/{case['id']}/messages",
        headers=auth_headers["verifier"],
        json={"body": "The document says 2022."},
    )
    assert r.status_code == 201
    body = client.get(f"{API}/reviews/{case['id']}", headers=auth_headers["verifier"]).json()
    assert body["status"] == ReviewStatus.PENDING.value
    assert len(body["messages"]) == 2


def test_the_institution_replying_leaves_it_needing_info(
    client: TestClient, auth_headers: dict[str, dict[str, str]], case: dict
) -> None:
    """Only the verifier's answer clears the question it is waiting on."""
    client.post(
        f"{API}/reviews/{case['id']}/needs-info",
        headers=auth_headers["institution"],
        json={"body": "Which year?"},
    )
    client.post(
        f"{API}/reviews/{case['id']}/messages",
        headers=auth_headers["institution"],
        json={"body": "Any year will do."},
    )
    body = client.get(f"{API}/reviews/{case['id']}", headers=auth_headers["institution"]).json()
    assert body["status"] == ReviewStatus.NEEDS_INFO.value


def test_confirming_closes_the_case_and_records_who_decided(
    client: TestClient, auth_headers: dict[str, dict[str, str]], case: dict
) -> None:
    r = client.post(
        f"{API}/reviews/{case['id']}/decision",
        headers=auth_headers["institution"],
        json={"decision": "confirmed", "note": "Matches our paper records."},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == ReviewStatus.CLOSED.value
    assert body["decision"] == "confirmed"
    assert body["decision_note"] == "Matches our paper records."
    assert body["decider"]["email"] == "inst@t.test"
    assert body["decided_at"] is not None
    assert body["can_decide"] is False


def test_not_issued_requires_a_reason(
    client: TestClient, auth_headers: dict[str, dict[str, str]], case: dict
) -> None:
    """The one answer a holder can be harmed by does not get to be a bare flag."""
    blank = client.post(
        f"{API}/reviews/{case['id']}/decision",
        headers=auth_headers["institution"],
        json={"decision": "not_issued", "reason": "   "},
    )
    assert blank.status_code == 422

    r = client.post(
        f"{API}/reviews/{case['id']}/decision",
        headers=auth_headers["institution"],
        json={"decision": "not_issued", "reason": "No such number in our 2022 register."},
    )
    assert r.status_code == 200
    assert r.json()["decision"] == "not_issued"
    assert r.json()["decision_note"] == "No such number in our 2022 register."


def test_a_closed_case_takes_no_more_replies_or_decisions(
    client: TestClient, auth_headers: dict[str, dict[str, str]], case: dict
) -> None:
    """`closed` is terminal, so the record of what was answered when stays put."""
    client.post(
        f"{API}/reviews/{case['id']}/decision",
        headers=auth_headers["institution"],
        json={"decision": "confirmed"},
    )
    reply = client.post(
        f"{API}/reviews/{case['id']}/messages",
        headers=auth_headers["verifier"],
        json={"body": "thanks"},
    )
    assert reply.status_code == 409
    assert reply.json()["error"]["code"] == "case_closed"

    again = client.post(
        f"{API}/reviews/{case['id']}/decision",
        headers=auth_headers["institution"],
        json={"decision": "confirmed"},
    )
    assert again.status_code == 409


def test_a_new_request_may_be_opened_once_the_last_one_closed(
    client: TestClient, auth_headers: dict[str, dict[str, str]], case: dict, institution_id: int
) -> None:
    """The index bars a second *open* case, not a later question."""
    client.post(
        f"{API}/reviews/{case['id']}/decision",
        headers=auth_headers["institution"],
        json={"decision": "confirmed"},
    )
    r = client.post(
        f"{API}/reviews",
        headers=auth_headers["verifier"],
        json={"verification_id": case["verification_id"], "institution_id": institution_id},
    )
    assert r.status_code == 201


# --- confirm & add -------------------------------------------------------------


def test_confirm_and_add_creates_a_signed_certificate_and_closes_the_case(
    client: TestClient, db: Session, auth_headers: dict[str, dict[str, str]], case: dict
) -> None:
    """It goes through the ordinary create service, so the row is signed and
    has an issued PDF — there is no second way into the registry."""
    r = client.post(
        f"{API}/reviews/{case['id']}/decision",
        headers=auth_headers["institution"],
        json={"decision": "confirmed_added", "certificate": fields()},
    )
    assert r.status_code == 200, r.text
    assert r.json()["decision"] == "confirmed_added"

    cert = db.scalar(select(Certificate).where(Certificate.cert_number == UNKNOWN_NUMBER))
    assert cert is not None
    assert cert.signature
    assert cert.file_sha256
    assert cert.institution.code == "TST"


def test_a_failed_add_leaves_the_case_open_to_try_again(
    client: TestClient, auth_headers: dict[str, dict[str, str]], case: dict
) -> None:
    """A duplicate number must not burn the request: the institution corrects
    the form and answers again."""
    client.post(
        f"{API}/certificates", headers=auth_headers["institution"], json=fields("TST2022CS0001")
    )
    r = client.post(
        f"{API}/reviews/{case['id']}/decision",
        headers=auth_headers["institution"],
        json={"decision": "confirmed_added", "certificate": fields("TST2022CS0001")},
    )
    assert r.status_code == 409
    still = client.get(f"{API}/reviews/{case['id']}", headers=auth_headers["institution"]).json()
    assert still["status"] == ReviewStatus.PENDING.value


def test_a_decision_never_edits_the_verification(
    client: TestClient, db: Session, auth_headers: dict[str, dict[str, str]], case: dict
) -> None:
    """The verification records what the system concluded at the time; the
    institution's answer is a later, separate fact shown beside it."""
    client.post(
        f"{API}/reviews/{case['id']}/decision",
        headers=auth_headers["institution"],
        json={"decision": "confirmed_added", "certificate": fields()},
    )
    body = client.get(
        f"{API}/verifications/{case['verification_id']}", headers=auth_headers["verifier"]
    ).json()
    assert body["result"] == "MANUAL_REVIEW"
    assert body["certificate"] is None
    assert body["reviews"][0]["decision"] == "confirmed_added"
    assert body["reviews"][0]["institution_code"] == "TST"


def test_the_add_form_is_prefilled_from_what_the_document_said(
    client: TestClient,
    db: Session,
    users: dict[str, User],
    auth_headers: dict[str, dict[str, str]],
    institution_id: int,
) -> None:
    """The institution corrects a draft rather than retyping a page. The
    document's own casing is used, not the normalized comparison form."""
    verification = Verification(
        verifier_id=users["verifier"].id,
        method="upload",
        result="MANUAL_REVIEW",
        checks=[],
        extracted_fields={
            "fields": {
                "cert_number": {
                    "value": "TST2099ZZ0001",
                    "raw": "TST2099ZZ0001",
                    "confidence": 0.9,
                },
                "student_name": {"value": "NANDINI RAO", "raw": "Nandini Rao", "confidence": 0.8},
            }
        },
    )
    db.add(verification)
    db.flush()
    created = client.post(
        f"{API}/reviews",
        headers=auth_headers["verifier"],
        json={"verification_id": str(verification.id), "institution_id": institution_id},
    ).json()

    body = client.get(f"{API}/reviews/{created['id']}", headers=auth_headers["institution"]).json()
    assert body["prefill"]["student_name"] == "Nandini Rao"
    assert body["prefill"]["cert_number"] == "TST2099ZZ0001"


def test_no_draft_is_offered_when_the_registry_already_has_the_record(
    client: TestClient, db: Session, auth_headers: dict[str, dict[str, str]], case: dict
) -> None:
    """Nothing to add: the institution is being asked about a record it holds."""
    client.post(f"{API}/certificates", headers=auth_headers["institution"], json=fields())
    body = client.get(f"{API}/reviews/{case['id']}", headers=auth_headers["institution"]).json()
    assert body["registry_match"]["cert_number"] == UNKNOWN_NUMBER
    assert body["prefill"] == {}


# --- retention -----------------------------------------------------------------


def test_an_open_request_holds_its_document_back_from_retention(
    client: TestClient,
    db: Session,
    users: dict[str, User],
    auth_headers: dict[str, dict[str, str]],
    institution_id: int,
    tmp_path,
) -> None:
    """An institution cannot confirm a document that retention deleted while
    it was being asked about. The hold lasts exactly as long as the case."""
    path = tmp_path / "held.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\nnot really a png")
    upload = Upload(
        path=str(path),
        sha256="c" * 64,
        mime="image/png",
        expires_at=datetime.now(UTC) - timedelta(days=1),  # already due
    )
    db.add(upload)
    db.flush()
    verification = Verification(
        verifier_id=users["verifier"].id,
        method="upload",
        result="MANUAL_REVIEW",
        checks=[],
        upload_id=upload.id,
    )
    db.add(verification)
    db.flush()
    created = client.post(
        f"{API}/reviews",
        headers=auth_headers["verifier"],
        json={"verification_id": str(verification.id), "institution_id": institution_id},
    )
    assert created.status_code == 201

    rows, files = uploads.prune_expired(db)
    assert rows == 0, "an expired upload must survive while a request about it is open"
    assert path.is_file()

    client.post(
        f"{API}/reviews/{created.json()['id']}/decision",
        headers=auth_headers["institution"],
        json={"decision": "confirmed"},
    )
    rows, files = uploads.prune_expired(db)
    assert rows == 1, "normal retention resumes once the request closes"
    assert not path.is_file()


# --- audit ---------------------------------------------------------------------


def test_create_message_and_decision_are_each_audited(
    client: TestClient, db: Session, auth_headers: dict[str, dict[str, str]], case: dict
) -> None:
    client.post(
        f"{API}/reviews/{case['id']}/needs-info",
        headers=auth_headers["institution"],
        json={"body": "Which year?"},
    )
    client.post(
        f"{API}/reviews/{case['id']}/messages",
        headers=auth_headers["verifier"],
        json={"body": "2022."},
    )
    client.post(
        f"{API}/reviews/{case['id']}/decision",
        headers=auth_headers["institution"],
        json={"decision": "confirmed"},
    )
    actions = set(
        db.scalars(
            select(AuditLog.action).where(AuditLog.entity_id == case["id"]).order_by(AuditLog.id)
        )
    )
    assert actions == {"review.create", "review.needs_info", "review.message", "review.confirmed"}


def test_the_nav_badge_counts_only_what_the_user_may_see(
    client: TestClient, auth_headers: dict[str, dict[str, str]], case: dict
) -> None:
    assert client.get(f"{API}/reviews/counts", headers=auth_headers["institution"]).json() == {
        "open": 1,
        "open_over_7_days": 0,
    }
    assert client.get(
        f"{API}/reviews/counts", headers=auth_headers["other_institution"]
    ).json() == {"open": 0, "open_over_7_days": 0}


def test_an_open_case_is_findable_by_status(
    client: TestClient, auth_headers: dict[str, dict[str, str]], case: dict
) -> None:
    for status in ("open", "pending"):
        listed = client.get(
            f"{API}/reviews", headers=auth_headers["institution"], params={"status": status}
        ).json()
        assert [c["id"] for c in listed["items"]] == [case["id"]], status
    closed = client.get(
        f"{API}/reviews", headers=auth_headers["institution"], params={"status": "closed"}
    ).json()
    assert closed["total"] == 0
    assert (
        client.get(
            f"{API}/reviews", headers=auth_headers["institution"], params={"status": "nonsense"}
        ).status_code
        == 422
    )


def test_a_case_counts_as_overdue_after_seven_days(
    client: TestClient, db: Session, auth_headers: dict[str, dict[str, str]], case: dict
) -> None:
    """What the admin dashboard watches: an institution that never answers."""
    row = db.get(ReviewCase, case["id"])
    assert row is not None
    row.created_at = datetime.now(UTC) - timedelta(days=8)
    db.flush()
    counts = client.get(f"{API}/reviews/counts", headers=auth_headers["institution"]).json()
    assert counts == {"open": 1, "open_over_7_days": 1}
    stats = client.get(f"{API}/admin/stats", headers=auth_headers["admin"]).json()
    assert stats["requests_open"] == 1
    assert stats["requests_open_over_7_days"] == 1
