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
    CHECK_DOCUMENT_CONTENT,
    CHECK_FIELD_MATCH,
    CHECK_FILE_HASH,
    CHECK_QR_SIGNATURE,
    CHECK_REGISTRY_LOOKUP,
    Check,
    CheckStatus,
    ExtractedFieldValue,
    FieldState,
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
        "issue_date": "2024-07-15",
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
    """A disagreement OCR is unsure about is never a mismatch.

    At 10% it is not a reading at all: the field counts as not read, which is
    listed for the verifier but does not stand in the way of a document that
    otherwise identifies itself.
    """
    outcome = evaluate(upload_input(key, upload(cgpa="9.90", confidence=0.10)))
    assert outcome.result is not VerificationResult.MISMATCH
    cgpa = next(c for c in outcome.checks if c.name == f"{CHECK_FIELD_MATCH}.cgpa")
    assert cgpa.state is FieldState.NOT_READ
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


def test_a_field_that_could_not_be_read_does_not_block_a_verdict(
    key: Ed25519PrivateKey,
) -> None:
    """A page whose roll number was lost to a shadow still identifies itself
    by its number, and nothing on it disagrees. The unread field is reported,
    not held against the document."""
    outcome = evaluate(upload_input(key, upload(roll_number=None)))
    assert outcome.result is VerificationResult.VERIFIED
    roll = next(c for c in outcome.checks if c.name == f"{CHECK_FIELD_MATCH}.roll_number")
    assert roll.state is FieldState.NOT_READ
    assert roll.status is CheckStatus.UNCERTAIN
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


# --- the QR-first rule --------------------------------------------------------
#
# The rule the merged "Verify document" path rests on: a valid signature plus
# nothing that confidently contradicts the registry is VERIFIED, whatever the
# OCR managed to read. These pin all four of its corners.


def qr_input(key: Ed25519PrivateKey, evidence: UploadEvidence, **kwargs) -> VerificationInput:
    """An upload carrying a genuine QR for `record()`."""
    kwargs.setdefault("qr", QrPayload(CERT_NUMBER, "TST", sign_record(key, record())))
    return upload_input(key, evidence, **kwargs)


def test_a_valid_qr_verifies_when_a_field_could_not_be_read(key: Ed25519PrivateKey) -> None:
    """A photograph that lost the CGPA to a shadow is still VERIFIED: the
    signature is proof, and an unread field is not a disagreement."""
    outcome = evaluate(qr_input(key, upload(cgpa=None)))
    assert outcome.result is VerificationResult.VERIFIED
    check = statuses(outcome.checks)[f"{CHECK_FIELD_MATCH}.cgpa"]
    assert check is CheckStatus.UNCERTAIN


def test_an_unread_field_is_reported_against_the_registry_value(key: Ed25519PrivateKey) -> None:
    """ "Not checked" has to say what it was not checked against, or the
    verifier is left to guess what the document should have said."""
    outcome = evaluate(qr_input(key, upload(cgpa=None)))
    detail = next(c.detail for c in outcome.checks if c.name == f"{CHECK_FIELD_MATCH}.cgpa")
    assert "8.50" in detail
    assert "not checked" in detail


def test_a_valid_qr_does_not_verify_when_nothing_at_all_was_read(key: Ed25519PrivateKey) -> None:
    """Changed deliberately: this used to be VERIFIED.

    An unrecognised layout compares no fields, so a valid signature was the
    whole verdict — which told the verifier their document was fine when
    nothing about *it* had been checked. The signature still proves the
    record; the document is now reported as unconfirmed instead.
    """
    evidence = UploadEvidence(sha256=OTHER_SHA, template=None, fields={}, has_text=False)
    outcome = evaluate(qr_input(key, evidence))
    assert outcome.result is VerificationResult.MANUAL_REVIEW
    status = statuses(outcome.checks)
    assert status[CHECK_QR_SIGNATURE] is CheckStatus.PASS
    assert status[CHECK_FIELD_MATCH] is CheckStatus.UNCERTAIN
    assert status[CHECK_DOCUMENT_CONTENT] is CheckStatus.UNCERTAIN


def test_a_confident_conflict_beats_a_valid_qr(key: Ed25519PrivateKey) -> None:
    """The point of reading the print at all: an edited document keeps its
    original QR, so the signature cannot be the last word."""
    outcome = evaluate(qr_input(key, upload(student_name="SOMEONE ELSE", confidence=0.99)))
    assert outcome.result is VerificationResult.MISMATCH


def test_an_invalid_qr_signature_is_a_mismatch_however_well_it_reads(
    key: Ed25519PrivateKey,
) -> None:
    """Rule 2 runs before the fields are even considered: a payload signed by
    something other than this institution's key is a MISMATCH even when every
    printed field agrees."""
    other = Ed25519PrivateKey.generate()
    outcome = evaluate(
        upload_input(
            key,
            upload(),
            qr=QrPayload(CERT_NUMBER, "TST", sign_record(other, record())),
        )
    )
    assert outcome.result is VerificationResult.MISMATCH
    assert statuses(outcome.checks)[CHECK_QR_SIGNATURE] is CheckStatus.FAIL


def test_a_low_confidence_conflict_does_not_overturn_a_valid_qr(key: Ed25519PrivateKey) -> None:
    """Only a *confident* reading may contradict a signature: this is not a
    MISMATCH and the field stays uncertain.

    It is no longer VERIFIED either, though — the one field read badly here is
    the student name, so nothing confirms the document belongs to the person
    the record names. That is the unconfirmed bar, not the conflict rule.
    """
    outcome = evaluate(
        qr_input(
            key,
            upload(student_name="SOMEONE ELSE", confidence=0.40),
            thresholds=Thresholds(min_field_confidence=0.85),
        )
    )
    assert outcome.result is not VerificationResult.MISMATCH
    assert outcome.result is VerificationResult.MANUAL_REVIEW
    assert statuses(outcome.checks)[f"{CHECK_FIELD_MATCH}.student_name"] is CheckStatus.UNCERTAIN


# --- the three confidence bands -----------------------------------------------
#
# The rule these pin: VERIFIED means nothing on the page disagrees. A valid
# signature proves what the institution issued; it says nothing about what is
# printed on the paper the verifier is holding.


def test_a_moderately_confident_difference_blocks_a_valid_qr(key: Ed25519PrivateKey) -> None:
    """The bug this fixes: a CGPA printed 9.99 and read at 76% against a
    registry 9.32 used to pass as VERIFIED on the strength of the QR."""
    outcome = evaluate(qr_input(key, upload(cgpa="9.99", confidence=0.76)))
    assert outcome.result is VerificationResult.MANUAL_REVIEW
    cgpa = next(c for c in outcome.checks if c.name == f"{CHECK_FIELD_MATCH}.cgpa")
    assert cgpa.state is FieldState.DIFFERS
    assert cgpa.status is CheckStatus.UNCERTAIN
    assert "9.99" in cgpa.detail and "8.50" in cgpa.detail


def test_a_confident_difference_is_still_a_mismatch(key: Ed25519PrivateKey) -> None:
    outcome = evaluate(qr_input(key, upload(cgpa="9.99", confidence=0.94)))
    assert outcome.result is VerificationResult.MISMATCH
    cgpa = next(c for c in outcome.checks if c.name == f"{CHECK_FIELD_MATCH}.cgpa")
    assert cgpa.state is FieldState.DIFFERS
    assert cgpa.status is CheckStatus.FAIL


def test_everything_read_agrees_and_two_fields_were_not_read(key: Ed25519PrivateKey) -> None:
    """VERIFIED, with the unread fields reported rather than held against it."""
    outcome = evaluate(qr_input(key, upload(roll_number=None, programme=None)))
    assert outcome.result is VerificationResult.VERIFIED
    states = {c.name: c.state for c in outcome.checks if c.state is not None}
    assert states[f"{CHECK_FIELD_MATCH}.roll_number"] is FieldState.NOT_READ
    assert states[f"{CHECK_FIELD_MATCH}.programme"] is FieldState.NOT_READ
    assert states[f"{CHECK_FIELD_MATCH}.cert_number"] is FieldState.MATCHES
    assert not [c for c in outcome.checks if c.state is FieldState.DIFFERS]


def test_the_band_edges_are_the_thresholds_not_approximations(key: Ed25519PrivateKey) -> None:
    """Exactly at a threshold belongs to the stricter band, so a tuned value
    means what it says."""
    thresholds = Thresholds(min_field_confidence=0.85, min_discrepancy_confidence=0.50)
    at_conflict = evaluate(
        qr_input(key, upload(cgpa="9.99", confidence=0.85), thresholds=thresholds)
    )
    assert at_conflict.result is VerificationResult.MISMATCH

    at_discrepancy = evaluate(
        qr_input(key, upload(cgpa="9.99", confidence=0.50), thresholds=thresholds)
    )
    assert at_discrepancy.result is VerificationResult.MANUAL_REVIEW

    below = evaluate(qr_input(key, upload(cgpa="9.99", confidence=0.49), thresholds=thresholds))
    assert below.result is VerificationResult.VERIFIED


def test_the_thresholds_are_configurable(key: Ed25519PrivateKey) -> None:
    """An institution that wants every difference looked at can lower the
    discrepancy band; the engine reads it from the input, never from config."""
    strict = Thresholds(min_field_confidence=0.85, min_discrepancy_confidence=0.10)
    outcome = evaluate(qr_input(key, upload(cgpa="9.99", confidence=0.20), thresholds=strict))
    assert outcome.result is VerificationResult.MANUAL_REVIEW


def test_the_date_of_issue_is_compared_like_any_other_field(key: Ed25519PrivateKey) -> None:
    """It is printed on the certificate and signed into the record, so "not
    checked" was never the right answer for it."""
    agrees = evaluate(qr_input(key, upload()))
    issued = next(c for c in agrees.checks if c.name == f"{CHECK_FIELD_MATCH}.issue_date")
    assert issued.state is FieldState.MATCHES

    differs = evaluate(qr_input(key, upload(issue_date="2023-01-01", confidence=0.95)))
    assert differs.result is VerificationResult.MISMATCH


def test_an_unread_field_never_turns_a_difference_into_a_pass(key: Ed25519PrivateKey) -> None:
    """One field differing is enough, however much else could not be read."""
    outcome = evaluate(
        qr_input(key, upload(cgpa="9.99", confidence=0.70, roll_number=None, programme=None))
    )
    assert outcome.result is VerificationResult.MANUAL_REVIEW


# --- a genuine QR does not verify a document nobody could read ---------------
#
# The hole these close: a page carrying a real signed QR used to be VERIFIED
# whatever was printed beside it, including nothing readable at all. The QR
# proves the *record*; confirming the *document* needs the student name read
# and matched, at least `min_matched_fields` critical fields matching, and
# nothing differing.


def content(checks: list[Check]) -> Check:
    return next(c for c in checks if c.name == CHECK_DOCUMENT_CONTENT)


def test_a_genuine_qr_with_no_layout_matched_is_unconfirmed(key: Ed25519PrivateKey) -> None:
    """The reported bug, in one case: valid NBIT QR, "no known layout
    matched", every field not checked — and a VERIFIED verdict."""
    evidence = UploadEvidence(sha256=OTHER_SHA, template=None, fields={})
    outcome = evaluate(qr_input(key, evidence))

    assert outcome.result is VerificationResult.MANUAL_REVIEW
    check = content(outcome.checks)
    assert check.status is CheckStatus.UNCERTAIN
    assert "no known layout matched" in check.detail.lower()
    # Never an accusation: nothing was found against the document.
    assert outcome.result is not VerificationResult.MISMATCH


def test_a_genuine_qr_with_the_name_and_three_fields_verifies(key: Ed25519PrivateKey) -> None:
    """The bar met exactly: the name, the number and the CGPA, nothing else
    read, nothing differing."""
    evidence = upload(roll_number=None, programme=None, year_of_passing=None, issue_date=None)
    outcome = evaluate(qr_input(key, evidence))

    assert outcome.result is VerificationResult.VERIFIED
    assert content(outcome.checks).status is CheckStatus.PASS
    matched = [c for c in outcome.checks if c.state is FieldState.MATCHES]
    assert len(matched) == 3


def test_a_genuine_qr_with_only_two_fields_is_unconfirmed(key: Ed25519PrivateKey) -> None:
    """One below the bar. The name was read and matched, which is necessary
    and not sufficient."""
    evidence = upload(
        roll_number=None, programme=None, year_of_passing=None, issue_date=None, cgpa=None
    )
    outcome = evaluate(qr_input(key, evidence))

    assert outcome.result is VerificationResult.MANUAL_REVIEW
    check = content(outcome.checks)
    assert check.status is CheckStatus.UNCERTAIN
    assert "2 of the 7" in check.detail


def test_a_genuine_qr_without_the_student_name_is_unconfirmed(key: Ed25519PrivateKey) -> None:
    """Five fields matching is well past the count, and still not enough: the
    one field that says whose certificate this is was not read."""
    evidence = upload(student_name=None, issue_date=None)
    outcome = evaluate(qr_input(key, evidence))

    assert outcome.result is VerificationResult.MANUAL_REVIEW
    assert len([c for c in outcome.checks if c.state is FieldState.MATCHES]) == 5
    check = content(outcome.checks)
    assert check.status is CheckStatus.UNCERTAIN
    assert "student name" in check.detail.lower()


def test_the_original_pdf_still_verifies_on_its_hash(key: Ed25519PrivateKey) -> None:
    """The exempt path: the bytes *are* the issued certificate, so there is no
    separate document to confirm — whatever OCR made of it."""
    evidence = upload(sha256=ISSUED_SHA, template=None)
    outcome = evaluate(upload_input(key, evidence))

    assert outcome.result is VerificationResult.VERIFIED
    assert statuses(outcome.checks)[CHECK_FILE_HASH] is CheckStatus.PASS
    assert content(outcome.checks).status is CheckStatus.PASS


def test_an_exact_certificate_number_alone_no_longer_verifies(key: Ed25519PrivateKey) -> None:
    """The same hole without a QR: the number read off the page identified the
    record, but nothing confirmed the rest of the document."""
    evidence = upload(
        student_name=None,
        roll_number=None,
        programme=None,
        year_of_passing=None,
        cgpa=None,
        issue_date=None,
    )
    outcome = evaluate(upload_input(key, evidence))

    assert outcome.result is VerificationResult.MANUAL_REVIEW
    assert statuses(outcome.checks)[f"{CHECK_FIELD_MATCH}.cert_number"] is CheckStatus.PASS


def test_the_matched_field_count_comes_from_the_input(key: Ed25519PrivateKey) -> None:
    """Configurable like the confidence bands: the engine reads it from
    `VerificationInput.thresholds`, never from settings."""
    evidence = upload(
        roll_number=None, programme=None, year_of_passing=None, issue_date=None, cgpa=None
    )
    lenient = Thresholds(min_matched_fields=2)
    assert evaluate(qr_input(key, evidence, thresholds=lenient)).result is (
        VerificationResult.VERIFIED
    )

    strict = Thresholds(min_matched_fields=7)
    assert evaluate(qr_input(key, upload(), thresholds=strict)).result is (
        VerificationResult.VERIFIED
    ), "all seven match, so even the strictest bar is met"
    assert evaluate(qr_input(key, upload(cgpa=None), thresholds=strict)).result is (
        VerificationResult.MANUAL_REVIEW
    )


def test_a_scanned_qr_with_no_document_is_unaffected(key: Ed25519PrivateKey) -> None:
    """The new bar is about a document presented. Scanning a QR or typing a
    number presents none, so those paths are untouched and document_content is
    skipped."""
    outcome = evaluate(
        VerificationInput(
            method=VerificationMethod.QR,
            cert_number=CERT_NUMBER,
            record=registry(key),
            qr=QrPayload(CERT_NUMBER, "TST", sign_record(key, record())),
        )
    )
    assert outcome.result is VerificationResult.VERIFIED
    assert content(outcome.checks).status is CheckStatus.SKIPPED


def test_a_revoked_record_still_outranks_the_new_rule(key: Ed25519PrivateKey) -> None:
    evidence = UploadEvidence(sha256=OTHER_SHA, template=None, fields={})
    outcome = evaluate(
        qr_input(
            key,
            evidence,
            registry_record=registry(key, status="revoked", revoked_at=datetime.now(UTC)),
        )
    )
    assert outcome.result is VerificationResult.REVOKED


def test_a_confident_conflict_still_outranks_the_new_rule(key: Ed25519PrivateKey) -> None:
    """An edited document reads as a MISMATCH, not as merely unconfirmed."""
    outcome = evaluate(qr_input(key, upload(cgpa="9.90", confidence=0.99)))
    assert outcome.result is VerificationResult.MISMATCH


def test_a_possible_discrepancy_still_reads_as_one(key: Ed25519PrivateKey) -> None:
    """A field that differs is a discrepancy, not an unconfirmed document: the
    evidence names the disagreement rather than the missing confirmation."""
    outcome = evaluate(qr_input(key, upload(cgpa="9.99", confidence=0.70)))
    assert outcome.result is VerificationResult.MANUAL_REVIEW
    assert "not agree" in content(outcome.checks).detail


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
    """`state` is carried by field_match entries only; every check still has
    the three keys the result page reads."""
    for item in evaluate(upload_input(key, upload())).checks_as_dicts():
        assert {"name", "status", "detail"} <= set(item)
        assert set(item) <= {"name", "status", "detail", "state"}
        assert ("state" in item) == item["name"].startswith("field_match.")
        assert item["detail"].endswith(".")
