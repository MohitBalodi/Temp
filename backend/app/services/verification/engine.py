"""The verification rule engine.

Pure functions: no database, no network, no clock. Everything a decision needs
arrives in `VerificationInput`, so every rule path is unit-testable on its own.

Results are VERIFIED / MISMATCH / REVOKED / MANUAL_REVIEW — never "fake" or
"forged". Absence of evidence is not fraud: an unknown number, an unreadable
document or a missing field all go to MANUAL_REVIEW, not to an accusation.

Only the checks that need no uploaded file live here so far (registry_lookup,
revocation, record_signature, qr_signature). file_hash and field_match join
them with the upload pipeline (Tier 2).
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from app.services.normalize import format_decimal, ids_match, normalize_id, normalize_text
from app.services.qr import QrPayload
from app.services.signing import CertificateRecord, verify_record

# Mirrors models.CertificateStatus.REVOKED, kept as a literal so the engine
# imports nothing that touches the database.
STATUS_REVOKED = "revoked"

CHECK_REGISTRY_LOOKUP = "registry_lookup"
CHECK_REVOCATION = "revocation"
CHECK_RECORD_SIGNATURE = "record_signature"
CHECK_QR_SIGNATURE = "qr_signature"
CHECK_FILE_HASH = "file_hash"
CHECK_FIELD_MATCH = "field_match"

# The fields a verdict may turn on (project spec, "Critical fields"). The grade
# is one logical field with two possible carriers, so cgpa and marks are
# compared only when the registry record actually holds that one.
CRITICAL_FIELDS = (
    "cert_number",
    "student_name",
    "roll_number",
    "programme",
    "year_of_passing",
    "cgpa",
    "marks",
)

# Identifiers tolerate OCR character confusions on both sides; everything else
# is compared exactly after normalization. Fuzzy name matching is item 7.
_ID_FIELDS = frozenset({"cert_number", "roll_number"})
_TEXT_FIELDS = frozenset({"student_name", "programme"})

# `Check.detail` is read by a verifier, so it names fields the way the page
# does rather than the way the schema does.
_FIELD_LABELS = {
    "cert_number": "The certificate number",
    "student_name": "The student name",
    "roll_number": "The roll number",
    "programme": "The programme",
    "year_of_passing": "The year of passing",
    "cgpa": "The CGPA",
    "marks": "The marks",
}


def _label(name: str) -> str:
    return _FIELD_LABELS.get(name, name)


class VerificationMethod(StrEnum):
    ID = "id"
    QR = "qr"
    UPLOAD = "upload"


class VerificationResult(StrEnum):
    VERIFIED = "VERIFIED"
    MISMATCH = "MISMATCH"
    REVOKED = "REVOKED"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class CheckStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    SKIPPED = "skipped"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True, slots=True)
class Check:
    """One piece of evidence behind the result. Stored in `verifications.checks`
    and shown to the verifier as-is, so `detail` is written for a human."""

    name: str
    status: CheckStatus
    detail: str

    def as_dict(self) -> dict[str, str]:
        return {"name": self.name, "status": self.status.value, "detail": self.detail}


@dataclass(frozen=True, slots=True)
class RegistryRecord:
    """What the registry holds for a certificate, as facts the engine can check."""

    record: CertificateRecord
    signature: str
    public_key_pem: str
    status: str
    revoked_at: datetime | None = None
    # SHA-256 of the PDF the institution issued, when one was stored.
    file_sha256: str | None = None

    @property
    def is_revoked(self) -> bool:
        return self.status == STATUS_REVOKED

    def field_value(self, name: str) -> str | None:
        """The record's value for a critical field, in comparable string form.

        Mirrors what field extraction produces, so the two can be compared
        without either side knowing about the other's representation.
        """
        raw = getattr(self.record, name, None)
        if raw is None:
            return None
        if name in _ID_FIELDS:
            return normalize_id(str(raw))
        if name in _TEXT_FIELDS:
            return normalize_text(str(raw))
        if name == "year_of_passing":
            return str(int(raw))
        if name in {"cgpa", "marks"}:
            return format_decimal(raw if isinstance(raw, Decimal) else Decimal(str(raw)))
        return str(raw)


@dataclass(frozen=True, slots=True)
class ExtractedFieldValue:
    """One field read off an uploaded document, with the recogniser's
    confidence in it. `value` is already normalized for comparison."""

    value: str | None
    confidence: float


@dataclass(frozen=True, slots=True)
class UploadEvidence:
    """What an uploaded document contributed.

    `template` is None when the layout was not recognised, which is a reason
    for MANUAL_REVIEW and never for MISMATCH.
    """

    sha256: str
    template: str | None = None
    fields: dict[str, ExtractedFieldValue] = field(default_factory=dict)
    has_text: bool = False


@dataclass(frozen=True, slots=True)
class Thresholds:
    """Tunables, passed in rather than read from config, so the engine stays
    pure and every rule path is testable at a chosen threshold."""

    # Below this an extracted field is uncertain: it can send a result to
    # MANUAL_REVIEW but must never produce a MISMATCH.
    min_field_confidence: float = 0.85


@dataclass(frozen=True, slots=True)
class VerificationInput:
    method: VerificationMethod
    cert_number: str
    record: RegistryRecord | None = None
    qr: QrPayload | None = None
    upload: UploadEvidence | None = None
    thresholds: Thresholds = Thresholds()


@dataclass(frozen=True, slots=True)
class VerificationOutcome:
    result: VerificationResult
    checks: list[Check]

    def checks_as_dicts(self) -> list[dict[str, str]]:
        return [c.as_dict() for c in self.checks]


# --- individual checks --------------------------------------------------------


def _registry_lookup(data: VerificationInput) -> Check:
    if data.record is None:
        return Check(
            CHECK_REGISTRY_LOOKUP,
            CheckStatus.FAIL,
            f"No certificate numbered {data.cert_number} is in the registry.",
        )
    return Check(
        CHECK_REGISTRY_LOOKUP,
        CheckStatus.PASS,
        f"Certificate {data.record.record.cert_number} is registered to "
        f"{data.record.record.institution_code}.",
    )


def _revocation(data: VerificationInput) -> Check:
    if data.record is None:
        return Check(CHECK_REVOCATION, CheckStatus.SKIPPED, "No registry record to check.")
    if data.record.is_revoked:
        when = data.record.revoked_at
        detail = "The institution revoked this certificate"
        detail += f" on {when.date().isoformat()}." if when else "."
        return Check(CHECK_REVOCATION, CheckStatus.FAIL, detail)
    return Check(CHECK_REVOCATION, CheckStatus.PASS, "The certificate is not revoked.")


def _record_signature(data: VerificationInput) -> Check:
    """Re-check the signature stored with the record against the institution's
    public key: proof the registry row has not been altered since it was issued."""
    if data.record is None:
        return Check(CHECK_RECORD_SIGNATURE, CheckStatus.SKIPPED, "No registry record to check.")
    valid = verify_record(data.record.public_key_pem, data.record.record, data.record.signature)
    if valid:
        return Check(
            CHECK_RECORD_SIGNATURE,
            CheckStatus.PASS,
            f"The stored record matches the signature issued by "
            f"{data.record.record.institution_code}.",
        )
    return Check(
        CHECK_RECORD_SIGNATURE,
        CheckStatus.FAIL,
        "The stored record does not match its issuing signature.",
    )


def _qr_signature(data: VerificationInput) -> Check:
    # Keyed on whether a payload is present, not on the method: a QR decoded
    # from an uploaded page carries exactly the same signature as a scanned
    # one and must be checked the same way.
    if data.qr is None:
        return Check(CHECK_QR_SIGNATURE, CheckStatus.SKIPPED, "No QR code was presented.")
    if data.record is None:
        return Check(
            CHECK_QR_SIGNATURE,
            CheckStatus.SKIPPED,
            "No registry record to check the QR signature against.",
        )
    if data.qr.institution_code != data.record.record.institution_code:
        return Check(
            CHECK_QR_SIGNATURE,
            CheckStatus.FAIL,
            f"The QR names institution {data.qr.institution_code}, but this certificate is "
            f"registered to {data.record.record.institution_code}.",
        )
    valid = verify_record(data.record.public_key_pem, data.record.record, data.qr.signature)
    if valid:
        return Check(
            CHECK_QR_SIGNATURE,
            CheckStatus.PASS,
            f"The QR signature matches the registry record and the public key of "
            f"{data.record.record.institution_code}.",
        )
    return Check(
        CHECK_QR_SIGNATURE,
        CheckStatus.FAIL,
        "The QR signature does not match this certificate's registry record.",
    )


def _file_hash(data: VerificationInput) -> Check:
    """Compare the uploaded bytes with the issued PDF's stored hash.

    An exact match is the strongest evidence available: the verifier holds the
    very file the institution issued. A mismatch is *not* evidence against the
    document — a scan, a re-save or a print-to-PDF all change the bytes — so a
    difference is reported as uncertain, not failed, and the decision is left
    to the field comparison.
    """
    if data.upload is None:
        return Check(CHECK_FILE_HASH, CheckStatus.SKIPPED, "No file was uploaded.")
    if data.record is None:
        return Check(CHECK_FILE_HASH, CheckStatus.SKIPPED, "No registry record to compare against.")
    if not data.record.file_sha256:
        return Check(
            CHECK_FILE_HASH,
            CheckStatus.SKIPPED,
            "The registry has no stored file hash for this certificate.",
        )
    if data.upload.sha256 == data.record.file_sha256:
        return Check(
            CHECK_FILE_HASH,
            CheckStatus.PASS,
            "The uploaded file is byte-for-byte the certificate this institution issued.",
        )
    return Check(
        CHECK_FILE_HASH,
        CheckStatus.UNCERTAIN,
        "The uploaded file is not the original issued PDF. That is expected for a "
        "scan or a re-saved copy, so the printed details are compared instead.",
    )


def _compare_field(
    name: str, extracted: ExtractedFieldValue, expected: str, threshold: float
) -> Check:
    """One field_match entry."""
    check_name = f"{CHECK_FIELD_MATCH}.{name}"
    found = extracted.value

    label = _label(name)

    if found is None:
        return Check(
            check_name,
            CheckStatus.UNCERTAIN,
            f"{label} could not be read from the document.",
        )

    agrees = ids_match(found, expected) if name in _ID_FIELDS else found == expected
    if agrees:
        return Check(check_name, CheckStatus.PASS, f"{label} matches the registry: {expected}.")

    if extracted.confidence < threshold:
        return Check(
            check_name,
            CheckStatus.UNCERTAIN,
            f"{label} was read as {found!r} but the registry has {expected!r}. The reading "
            f"is only {extracted.confidence:.0%} confident, below the {threshold:.0%} "
            "threshold, so it is not treated as a conflict.",
        )

    return Check(
        check_name,
        CheckStatus.FAIL,
        f"{label} on the document is {found!r}, but the registry has {expected!r} "
        f"(read with {extracted.confidence:.0%} confidence).",
    )


def _field_match(data: VerificationInput) -> list[Check]:
    """One check per critical field the registry holds.

    Returns a single skipped/uncertain entry when there is nothing to compare,
    so the evidence list always says something about field matching.
    """
    if data.upload is None:
        return [Check(CHECK_FIELD_MATCH, CheckStatus.SKIPPED, "No document was uploaded.")]
    if data.record is None:
        return [
            Check(CHECK_FIELD_MATCH, CheckStatus.SKIPPED, "No registry record to compare against.")
        ]
    if data.upload.template is None:
        return [
            Check(
                CHECK_FIELD_MATCH,
                CheckStatus.UNCERTAIN,
                "The document's layout was not recognised, so no fields could be compared.",
            )
        ]

    threshold = data.thresholds.min_field_confidence
    checks: list[Check] = []
    for name in CRITICAL_FIELDS:
        expected = data.record.field_value(name)
        if expected is None:
            # The registry does not carry this field (e.g. marks when the
            # record uses cgpa), so there is nothing to compare.
            continue
        extracted = data.upload.fields.get(name)
        if extracted is None:
            checks.append(
                Check(
                    f"{CHECK_FIELD_MATCH}.{name}",
                    CheckStatus.UNCERTAIN,
                    f"{_label(name)} was not found on the document.",
                )
            )
            continue
        checks.append(_compare_field(name, extracted, expected, threshold))

    if not checks:
        return [
            Check(
                CHECK_FIELD_MATCH,
                CheckStatus.UNCERTAIN,
                "No critical field could be compared.",
            )
        ]
    return checks


# --- decision -----------------------------------------------------------------


def _decide(data: VerificationInput, checks: list[Check]) -> VerificationResult:
    """Decision rules from the project spec, first match wins."""
    status = {c.name: c.status for c in checks}
    field_checks = [c for c in checks if c.name.startswith(CHECK_FIELD_MATCH)]
    conflicting = [c for c in field_checks if c.status is CheckStatus.FAIL]
    uncertain = [c for c in field_checks if c.status is CheckStatus.UNCERTAIN]
    compared = [c for c in field_checks if c.status is CheckStatus.PASS]

    if data.record is None:
        # Rule 6: nothing to compare against. Not a verdict on the document.
        return VerificationResult.MANUAL_REVIEW
    if data.record.is_revoked:
        # Rule 1: a revoked record wins over everything else.
        return VerificationResult.REVOKED
    if status[CHECK_QR_SIGNATURE] is CheckStatus.FAIL:
        # Rule 2: QR present, signature does not verify.
        return VerificationResult.MISMATCH
    if status[CHECK_RECORD_SIGNATURE] is CheckStatus.FAIL:
        # Not in the spec's list: the row itself no longer matches the signature
        # the institution issued, so the registry copy cannot be trusted.
        return VerificationResult.MISMATCH
    if status[CHECK_FILE_HASH] is CheckStatus.PASS:
        # Rule 3: the verifier holds the exact file the institution issued.
        return VerificationResult.VERIFIED
    if status[CHECK_QR_SIGNATURE] is CheckStatus.PASS and not conflicting:
        # Rule 4. "All extracted critical fields match" is read as "nothing
        # conflicts": a valid Ed25519 signature over the record is
        # cryptographic proof, and a field OCR could not read confidently must
        # not be allowed to weaken it. A genuine *conflict* still falls through
        # to rule 5, which is what catches an altered document carrying its
        # original QR.
        return VerificationResult.VERIFIED
    if conflicting:
        # Rule 5: a critical field disagrees, read confidently enough to mean it.
        return VerificationResult.MISMATCH
    if data.upload is not None and (uncertain or not compared):
        # Rule 6: unknown layout, unreadable field, or a reading too weak to
        # act on. Absence of evidence is not fraud.
        return VerificationResult.MANUAL_REVIEW
    if data.upload is not None and compared:
        # Rule 7: every critical field the registry holds was read and agrees.
        return VerificationResult.VERIFIED
    # No upload: a signature-only or number-only verification with nothing wrong.
    return VerificationResult.VERIFIED


def evaluate(data: VerificationInput) -> VerificationOutcome:
    """Run every applicable check and decide. The checks come back in a stable
    order so the result page always lists them the same way."""
    checks = [
        _registry_lookup(data),
        _revocation(data),
        _record_signature(data),
        _qr_signature(data),
        _file_hash(data),
        *_field_match(data),
    ]
    return VerificationOutcome(result=_decide(data, checks), checks=checks)
