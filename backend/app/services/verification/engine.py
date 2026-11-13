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

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.services.qr import QrPayload
from app.services.signing import CertificateRecord, verify_record

# Mirrors models.CertificateStatus.REVOKED, kept as a literal so the engine
# imports nothing that touches the database.
STATUS_REVOKED = "revoked"

CHECK_REGISTRY_LOOKUP = "registry_lookup"
CHECK_REVOCATION = "revocation"
CHECK_RECORD_SIGNATURE = "record_signature"
CHECK_QR_SIGNATURE = "qr_signature"


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

    @property
    def is_revoked(self) -> bool:
        return self.status == STATUS_REVOKED


@dataclass(frozen=True, slots=True)
class VerificationInput:
    method: VerificationMethod
    cert_number: str
    record: RegistryRecord | None = None
    qr: QrPayload | None = None


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
    if data.method != VerificationMethod.QR or data.qr is None:
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


# --- decision -----------------------------------------------------------------


def _decide(data: VerificationInput, checks: list[Check]) -> VerificationResult:
    """Decision rules from the project spec, first match wins. The upload-only
    rules (file hash, field conflicts) are not reachable yet."""
    status = {c.name: c.status for c in checks}

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
    # Rules 4 and 7: signature good (or no QR to check) and nothing conflicts.
    return VerificationResult.VERIFIED


def evaluate(data: VerificationInput) -> VerificationOutcome:
    """Run every applicable check and decide. The checks come back in a stable
    order so the result page always lists them the same way."""
    checks = [
        _registry_lookup(data),
        _revocation(data),
        _record_signature(data),
        _qr_signature(data),
    ]
    return VerificationOutcome(result=_decide(data, checks), checks=checks)
