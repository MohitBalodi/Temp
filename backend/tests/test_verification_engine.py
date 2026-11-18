"""Every rule path of the verification engine, with no database and no HTTP."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.services.qr import QrPayload
from app.services.signing import CertificateRecord, public_key_pem, sign_record
from app.services.verification.engine import (
    CHECK_FIELD_MATCH,
    CHECK_FILE_HASH,
    CHECK_QR_SIGNATURE,
    CHECK_RECORD_SIGNATURE,
    CHECK_REGISTRY_LOOKUP,
    CHECK_REVOCATION,
    CheckStatus,
    RegistryRecord,
    VerificationInput,
    VerificationMethod,
    VerificationResult,
    evaluate,
)

CERT_NUMBER = "TST2024CS0001"
OTHER_NUMBER = "TST2024CS0002"

# Stand-ins for real digests; only equality matters to the engine.
ISSUED_SHA = "a" * 64
OTHER_SHA = "b" * 64


def record(cert_number: str = CERT_NUMBER, institution_code: str = "TST") -> CertificateRecord:
    return CertificateRecord(
        cert_number=cert_number,
        institution_code=institution_code,
        student_name="Aarav Sharma",
        roll_number="21CS001",
        programme="B.Tech Computer Science",
        year_of_passing=2024,
        cgpa=Decimal("8.50"),
        marks=None,
        issue_date=date(2024, 7, 15),
    )


@pytest.fixture(scope="module")
def key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.generate()


def registry(
    key: Ed25519PrivateKey,
    *,
    cert_number: str = CERT_NUMBER,
    institution_code: str = "TST",
    status: str = "active",
    revoked_at: datetime | None = None,
    signed: CertificateRecord | None = None,
    file_sha256: str | None = ISSUED_SHA,
) -> RegistryRecord:
    """A stored record. `signed` lets a test sign *different* content than the
    record holds, which is what an altered row looks like."""
    stored = record(cert_number, institution_code)
    return RegistryRecord(
        record=stored,
        signature=sign_record(key, signed or stored),
        public_key_pem=public_key_pem(key),
        status=status,
        revoked_at=revoked_at,
        file_sha256=file_sha256,
    )


def statuses(checks: list) -> dict[str, CheckStatus]:
    return {c.name: c.status for c in checks}


# --- verify by certificate number ---------------------------------------------


def test_known_active_record_verifies(key: Ed25519PrivateKey) -> None:
    outcome = evaluate(VerificationInput(VerificationMethod.ID, CERT_NUMBER, record=registry(key)))

    assert outcome.result is VerificationResult.VERIFIED
    by_name = statuses(outcome.checks)
    assert by_name[CHECK_REGISTRY_LOOKUP] is CheckStatus.PASS
    assert by_name[CHECK_REVOCATION] is CheckStatus.PASS
    assert by_name[CHECK_RECORD_SIGNATURE] is CheckStatus.PASS
    # Nothing was scanned, so there is no QR signature to judge.
    assert by_name[CHECK_QR_SIGNATURE] is CheckStatus.SKIPPED


def test_unknown_number_goes_to_manual_review() -> None:
    outcome = evaluate(VerificationInput(VerificationMethod.ID, "TST9999", record=None))

    assert outcome.result is VerificationResult.MANUAL_REVIEW
    by_name = statuses(outcome.checks)
    assert by_name[CHECK_REGISTRY_LOOKUP] is CheckStatus.FAIL
    assert by_name[CHECK_REVOCATION] is CheckStatus.SKIPPED
    assert by_name[CHECK_RECORD_SIGNATURE] is CheckStatus.SKIPPED
    assert by_name[CHECK_QR_SIGNATURE] is CheckStatus.SKIPPED


def test_revoked_record_is_revoked(key: Ed25519PrivateKey) -> None:
    revoked_at = datetime(2025, 3, 4, tzinfo=UTC)
    outcome = evaluate(
        VerificationInput(
            VerificationMethod.ID,
            CERT_NUMBER,
            record=registry(key, status="revoked", revoked_at=revoked_at),
        )
    )

    assert outcome.result is VerificationResult.REVOKED
    revocation = next(c for c in outcome.checks if c.name == CHECK_REVOCATION)
    assert revocation.status is CheckStatus.FAIL
    assert "2025-03-04" in revocation.detail


def test_revoked_without_a_date_still_reads_cleanly(key: Ed25519PrivateKey) -> None:
    outcome = evaluate(
        VerificationInput(
            VerificationMethod.ID, CERT_NUMBER, record=registry(key, status="revoked")
        )
    )

    assert outcome.result is VerificationResult.REVOKED
    assert "revoked this certificate." in next(
        c.detail for c in outcome.checks if c.name == CHECK_REVOCATION
    )


def test_altered_registry_row_is_a_mismatch(key: Ed25519PrivateKey) -> None:
    # The stored signature belongs to a different record: the row was changed
    # after it was issued.
    tampered = registry(key, signed=record(cert_number=OTHER_NUMBER))

    outcome = evaluate(VerificationInput(VerificationMethod.ID, CERT_NUMBER, record=tampered))

    assert outcome.result is VerificationResult.MISMATCH
    assert statuses(outcome.checks)[CHECK_RECORD_SIGNATURE] is CheckStatus.FAIL


# --- verify by QR -------------------------------------------------------------


def test_genuine_qr_verifies(key: Ed25519PrivateKey) -> None:
    stored = registry(key)
    qr = QrPayload(CERT_NUMBER, "TST", stored.signature)

    outcome = evaluate(VerificationInput(VerificationMethod.QR, CERT_NUMBER, stored, qr))

    assert outcome.result is VerificationResult.VERIFIED
    assert statuses(outcome.checks)[CHECK_QR_SIGNATURE] is CheckStatus.PASS


def test_qr_signature_from_another_certificate_is_a_mismatch(key: Ed25519PrivateKey) -> None:
    # A real QR whose number was swapped for another certificate's number.
    other_signature = sign_record(key, record(cert_number=OTHER_NUMBER))
    qr = QrPayload(CERT_NUMBER, "TST", other_signature)

    outcome = evaluate(VerificationInput(VerificationMethod.QR, CERT_NUMBER, registry(key), qr))

    assert outcome.result is VerificationResult.MISMATCH
    qr_check = next(c for c in outcome.checks if c.name == CHECK_QR_SIGNATURE)
    assert qr_check.status is CheckStatus.FAIL
    assert "does not match" in qr_check.detail


def test_qr_signed_by_another_key_is_a_mismatch(key: Ed25519PrivateKey) -> None:
    impostor = Ed25519PrivateKey.generate()
    qr = QrPayload(CERT_NUMBER, "TST", sign_record(impostor, record()))

    outcome = evaluate(VerificationInput(VerificationMethod.QR, CERT_NUMBER, registry(key), qr))

    assert outcome.result is VerificationResult.MISMATCH
    assert statuses(outcome.checks)[CHECK_QR_SIGNATURE] is CheckStatus.FAIL


def test_qr_naming_a_different_institution_is_a_mismatch(key: Ed25519PrivateKey) -> None:
    stored = registry(key)
    qr = QrPayload(CERT_NUMBER, "OTH", stored.signature)

    outcome = evaluate(VerificationInput(VerificationMethod.QR, CERT_NUMBER, stored, qr))

    assert outcome.result is VerificationResult.MISMATCH
    detail = next(c.detail for c in outcome.checks if c.name == CHECK_QR_SIGNATURE)
    assert "OTH" in detail and "TST" in detail


def test_qr_for_an_unknown_number_goes_to_manual_review() -> None:
    qr = QrPayload("TST9999", "TST", "c2lnbmF0dXJl")

    outcome = evaluate(VerificationInput(VerificationMethod.QR, "TST9999", None, qr))

    assert outcome.result is VerificationResult.MANUAL_REVIEW
    by_name = statuses(outcome.checks)
    assert by_name[CHECK_REGISTRY_LOOKUP] is CheckStatus.FAIL
    # Without a record there is nothing to check the signature against; that is
    # not evidence against the document.
    assert by_name[CHECK_QR_SIGNATURE] is CheckStatus.SKIPPED


def test_revocation_wins_over_a_bad_qr_signature(key: Ed25519PrivateKey) -> None:
    stored = registry(key, status="revoked", revoked_at=datetime(2025, 1, 1, tzinfo=UTC))
    qr = QrPayload(CERT_NUMBER, "TST", sign_record(key, record(cert_number=OTHER_NUMBER)))

    outcome = evaluate(VerificationInput(VerificationMethod.QR, CERT_NUMBER, stored, qr))

    assert outcome.result is VerificationResult.REVOKED


# --- shape of the evidence ----------------------------------------------------


def test_checks_are_stable_and_serializable(key: Ed25519PrivateKey) -> None:
    outcome = evaluate(VerificationInput(VerificationMethod.ID, CERT_NUMBER, registry(key)))

    # The upload-only checks are present and skipped on the by-number path, so
    # the result page always lists the same evidence in the same order.
    assert [c.name for c in outcome.checks] == [
        CHECK_REGISTRY_LOOKUP,
        CHECK_REVOCATION,
        CHECK_RECORD_SIGNATURE,
        CHECK_QR_SIGNATURE,
        CHECK_FILE_HASH,
        CHECK_FIELD_MATCH,
    ]
    for item in outcome.checks_as_dicts():
        assert set(item) == {"name", "status", "detail"}
        assert all(isinstance(v, str) for v in item.values())
        assert item["detail"].endswith(".")


def test_no_result_ever_says_fake(key: Ed25519PrivateKey) -> None:
    cases = [
        VerificationInput(VerificationMethod.ID, CERT_NUMBER, registry(key)),
        VerificationInput(VerificationMethod.ID, "TST9999", None),
        VerificationInput(VerificationMethod.ID, CERT_NUMBER, registry(key, status="revoked")),
        VerificationInput(
            VerificationMethod.QR,
            CERT_NUMBER,
            registry(key),
            QrPayload(CERT_NUMBER, "TST", sign_record(key, record(cert_number=OTHER_NUMBER))),
        ),
    ]
    for case in cases:
        outcome = evaluate(case)
        assert outcome.result.value in {"VERIFIED", "MISMATCH", "REVOKED", "MANUAL_REVIEW"}
        words = " ".join(c.detail for c in outcome.checks).lower()
        assert "fake" not in words and "forged" not in words and "fraud" not in words
