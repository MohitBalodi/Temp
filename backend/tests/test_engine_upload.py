"""The engine's upload rule paths (3, 5, 6, 7), with no DB and no network.

Separate from test_verification_engine.py only to keep that file focused on
the by-number and by-QR paths it already covered.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.services.qr import QrPayload
from app.services.signing import CertificateRecord, public_key_pem, sign_record
from app.services.verification.engine import (
    CHECK_FIELD_MATCH,
    CHECK_FILE_HASH,
    CHECK_REGISTRY_LOOKUP,
    Check,
    CheckStatus,
    ExtractedFieldValue,
    RegistryRecord,
    Thresholds,
    UploadEvidence,
    VerificationInput,
    VerificationMethod,
    VerificationResult,
    evaluate,
)

CERT_NUMBER = "TST2024CS0001"

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
    status: str = "active",
    revoked_at: datetime | None = None,
    file_sha256: str | None = ISSUED_SHA,
) -> RegistryRecord:
    stored = record()
    return RegistryRecord(
        record=stored,
        signature=sign_record(key, stored),
        public_key_pem=public_key_pem(key),
        status=status,
        revoked_at=revoked_at,
        file_sha256=file_sha256,
    )


def statuses(checks: list[Check]) -> dict[str, CheckStatus]:
    return {c.name: c.status for c in checks}


def upload(
    *,
    sha256: str = OTHER_SHA,
    template: str | None = "nbit",
    confidence: float = 1.0,
    has_text: bool = True,
    **overrides: str | None,
) -> UploadEvidence:
    """Extracted evidence agreeing with `record()` unless overridden.

    Pass `field=None` to drop a field, or a value to make it disagree.
    """
    values: dict[str, str | None] = {
        "cert_number": CERT_NUMBER,
        "student_name": "AARAV SHARMA",
        "roll_number": "21CS001",
        "programme": "B.TECH COMPUTER SCIENCE",
        "year_of_passing": "2024",
        "cgpa": "8.50",
    }
    values.update(overrides)
    return UploadEvidence(
        sha256=sha256,
        template=template,
        fields={
            name: ExtractedFieldValue(value=value, confidence=confidence)
            for name, value in values.items()
            if value is not None
        },
        has_text=has_text,
    )


def upload_input(key: Ed25519PrivateKey, evidence: UploadEvidence, **kwargs) -> VerificationInput:
    return VerificationInput(
        method=VerificationMethod.UPLOAD,
        cert_number=CERT_NUMBER,
        record=kwargs.pop("registry_record", registry(key)),
        upload=evidence,
        **kwargs,
    )


# --- rule 3: the file hash ----------------------------------------------------


def test_rule_3_exact_file_hash_verifies(key: Ed25519PrivateKey) -> None:
    """The verifier holds the very bytes the institution issued."""
    outcome = evaluate(upload_input(key, upload(sha256=ISSUED_SHA)))
    assert outcome.result is VerificationResult.VERIFIED
    assert statuses(outcome.checks)[CHECK_FILE_HASH] is CheckStatus.PASS


def test_rule_3_wins_even_when_a_field_was_misread(key: Ed25519PrivateKey) -> None:
    """Identical bytes settle it; OCR cannot overrule a byte-exact match."""
    evidence = upload(sha256=ISSUED_SHA, student_name="SOMEONE ELSE")
    assert evaluate(upload_input(key, evidence)).result is VerificationResult.VERIFIED


def test_a_different_file_hash_is_uncertain_not_a_failure(key: Ed25519PrivateKey) -> None:
    """A scan or a re-save legitimately changes the bytes, so a difference is
    not evidence against the document."""
    outcome = evaluate(upload_input(key, upload(sha256=OTHER_SHA)))
    assert statuses(outcome.checks)[CHECK_FILE_HASH] is CheckStatus.UNCERTAIN
    assert outcome.result is not VerificationResult.MISMATCH


def test_file_hash_is_skipped_when_the_registry_stored_none(key: Ed25519PrivateKey) -> None:
    outcome = evaluate(upload_input(key, upload(), registry_record=registry(key, file_sha256=None)))
    assert statuses(outcome.checks)[CHECK_FILE_HASH] is CheckStatus.SKIPPED


# --- rule 7: everything agrees ------------------------------------------------


def test_rule_7_all_fields_matching_verifies(key: Ed25519PrivateKey) -> None:
    """No QR, bytes differ, but every critical field agrees."""
    outcome = evaluate(upload_input(key, upload()))
    assert outcome.result is VerificationResult.VERIFIED
    field_checks = [c for c in outcome.checks if c.name.startswith(f"{CHECK_FIELD_MATCH}.")]
    assert field_checks
    assert all(c.status is CheckStatus.PASS for c in field_checks)


def test_one_check_per_compared_field(key: Ed25519PrivateKey) -> None:
    names = {c.name for c in evaluate(upload_input(key, upload())).checks}
    for field in ("cert_number", "student_name", "roll_number", "programme", "year_of_passing"):
        assert f"{CHECK_FIELD_MATCH}.{field}" in names


def test_marks_are_not_compared_when_the_record_uses_cgpa(key: Ed25519PrivateKey) -> None:
    """The record holds cgpa and no marks, so no marks check exists at all."""
    outcome = evaluate(upload_input(key, upload()))
    assert f"{CHECK_FIELD_MATCH}.marks" not in statuses(outcome.checks)


# --- rule 5: a confident conflict ---------------------------------------------


def test_rule_5_a_confident_conflict_is_a_mismatch(key: Ed25519PrivateKey) -> None:
    outcome = evaluate(upload_input(key, upload(cgpa="9.90", confidence=0.99)))
    assert outcome.result is VerificationResult.MISMATCH
    conflict = next(c for c in outcome.checks if c.name == f"{CHECK_FIELD_MATCH}.cgpa")
    assert conflict.status is CheckStatus.FAIL
    # The diff is in the evidence, for the result page to show.
    assert "9.90" in conflict.detail and "8.50" in conflict.detail


def test_rule_5_does_not_fire_below_the_confidence_threshold(key: Ed25519PrivateKey) -> None:
    """A disagreement OCR is unsure about is uncertain, never a mismatch."""
    outcome = evaluate(upload_input(key, upload(cgpa="9.90", confidence=0.10)))
    assert outcome.result is VerificationResult.MANUAL_REVIEW
    assert statuses(outcome.checks)[f"{CHECK_FIELD_MATCH}.cgpa"] is CheckStatus.UNCERTAIN


def test_the_confidence_threshold_comes_from_the_input(key: Ed25519PrivateKey) -> None:
    """Same reading, two thresholds, two verdicts — nothing is hardcoded."""
    evidence = upload(cgpa="9.90", confidence=0.80)

    lenient = evaluate(upload_input(key, evidence, thresholds=Thresholds(0.95)))
    assert lenient.result is VerificationResult.MANUAL_REVIEW

    strict = evaluate(upload_input(key, evidence, thresholds=Thresholds(0.50)))
    assert strict.result is VerificationResult.MISMATCH


def test_a_name_must_match_exactly_for_now(key: Ed25519PrivateKey) -> None:
    """Fuzzy name matching is item 7; today a different name conflicts."""
    outcome = evaluate(upload_input(key, upload(student_name="AARAVV SHARMA", confidence=1.0)))
    assert outcome.result is VerificationResult.MISMATCH


# --- rule 6: not enough to go on ----------------------------------------------


def test_rule_6_an_unknown_layout_is_manual_review(key: Ed25519PrivateKey) -> None:
    outcome = evaluate(upload_input(key, upload(template=None)))
    assert outcome.result is VerificationResult.MANUAL_REVIEW
    assert statuses(outcome.checks)[CHECK_FIELD_MATCH] is CheckStatus.UNCERTAIN


def test_rule_6_a_missing_critical_field_is_manual_review(key: Ed25519PrivateKey) -> None:
    outcome = evaluate(upload_input(key, upload(roll_number=None)))
    assert outcome.result is VerificationResult.MANUAL_REVIEW
    assert statuses(outcome.checks)[f"{CHECK_FIELD_MATCH}.roll_number"] is CheckStatus.UNCERTAIN


def test_rule_6_an_unreadable_document_is_manual_review(key: Ed25519PrivateKey) -> None:
    empty = UploadEvidence(sha256=OTHER_SHA, template=None, fields={}, has_text=False)
    assert evaluate(upload_input(key, empty)).result is VerificationResult.MANUAL_REVIEW


def test_an_upload_matching_no_record_is_manual_review() -> None:
    outcome = evaluate(
        VerificationInput(
            method=VerificationMethod.UPLOAD,
            cert_number="",
            record=None,
            upload=upload(template=None),
        )
    )
    assert outcome.result is VerificationResult.MANUAL_REVIEW
    assert statuses(outcome.checks)[CHECK_REGISTRY_LOOKUP] is CheckStatus.FAIL


# --- interaction with the earlier rules ---------------------------------------


def test_rule_1_revocation_still_wins_on_the_upload_path(key: Ed25519PrivateKey) -> None:
    """A byte-perfect copy of a revoked certificate is REVOKED, not VERIFIED."""
    outcome = evaluate(
        upload_input(
            key,
            upload(sha256=ISSUED_SHA),
            registry_record=registry(key, status="revoked", revoked_at=datetime.now(UTC)),
        )
    )
    assert outcome.result is VerificationResult.REVOKED


def test_rule_4_a_valid_qr_survives_an_uncertain_field(key: Ed25519PrivateKey) -> None:
    """A signature is cryptographic proof; a field OCR could not read
    confidently must not be allowed to weaken it."""
    outcome = evaluate(
        upload_input(
            key,
            upload(roll_number="2108901", confidence=0.09),
            qr=QrPayload(CERT_NUMBER, "TST", sign_record(key, record())),
        )
    )
    assert outcome.result is VerificationResult.VERIFIED


def test_rule_4_does_not_rescue_a_confident_conflict(key: Ed25519PrivateKey) -> None:
    """An altered document still carrying its original QR is a MISMATCH: what
    is printed disagrees with what was signed."""
    outcome = evaluate(
        upload_input(
            key,
            upload(cgpa="9.90", confidence=1.0),
            qr=QrPayload(CERT_NUMBER, "TST", sign_record(key, record())),
        )
    )
    assert outcome.result is VerificationResult.MISMATCH


# --- identifier comparison ----------------------------------------------------


def test_identifiers_tolerate_ocr_confusables(key: Ed25519PrivateKey) -> None:
    """S read as 5 in a roll number is not a conflict: both sides collapse."""
    outcome = evaluate(upload_input(key, upload(roll_number="21C5001", confidence=1.0)))
    assert outcome.result is VerificationResult.VERIFIED
    assert statuses(outcome.checks)[f"{CHECK_FIELD_MATCH}.roll_number"] is CheckStatus.PASS


def test_a_genuinely_different_identifier_still_conflicts(key: Ed25519PrivateKey) -> None:
    outcome = evaluate(upload_input(key, upload(roll_number="99XX999", confidence=1.0)))
    assert outcome.result is VerificationResult.MISMATCH


def test_identifier_separators_are_ignored(key: Ed25519PrivateKey) -> None:
    outcome = evaluate(upload_input(key, upload(cert_number="TST-2024/CS-0001", confidence=1.0)))
    assert statuses(outcome.checks)[f"{CHECK_FIELD_MATCH}.cert_number"] is CheckStatus.PASS


# --- language -----------------------------------------------------------------


def test_no_upload_result_ever_accuses(key: Ed25519PrivateKey) -> None:
    cases = [
        upload(sha256=ISSUED_SHA),
        upload(cgpa="9.90", confidence=1.0),
        upload(template=None),
        upload(roll_number=None),
        UploadEvidence(sha256=OTHER_SHA, template=None, fields={}),
    ]
    for evidence in cases:
        outcome = evaluate(upload_input(key, evidence))
        text = " ".join(c.detail for c in outcome.checks).lower()
        for word in ("fake", "forged", "fraud", "tamper", "criminal"):
            assert word not in text, f"{word!r} in evidence for {evidence}"


def test_every_check_detail_is_a_sentence(key: Ed25519PrivateKey) -> None:
    for item in evaluate(upload_input(key, upload())).checks_as_dicts():
        assert set(item) == {"name", "status", "detail"}
        assert item["detail"].endswith(".")
