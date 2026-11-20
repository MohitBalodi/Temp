"""The verification rule engine.

Pure functions: no database, no network, no clock. Everything a decision needs
arrives in `VerificationInput`, so every rule path is unit-testable on its own.

Results are VERIFIED / MISMATCH / REVOKED / MANUAL_REVIEW — never "fake" or
"forged". Absence of evidence is not fraud: an unknown number, an unreadable
document or a missing field all go to MANUAL_REVIEW, not to an accusation.

The checks, in the order `evaluate` returns them: registry_lookup, revocation,
record_signature, qr_signature, file_hash, one field_match.<field> per
compared critical field, and document_content — the last being the conclusion
drawn from the field checks, and the one check a signature cannot answer.
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
# Not in the spec's list of checks: the summary of whether the *document*
# presented could be confirmed against the record, as distinct from whether
# the record is genuine. A signature proves the second, never the first.
CHECK_DOCUMENT_CONTENT = "document_content"

# The fields a verdict may turn on (project spec, "Critical fields"). The grade
# is one logical field with two possible carriers, so cgpa and marks are
# compared only when the registry record actually holds that one.
#
# `issue_date` is compared too, though the spec's list does not name it: it is
# printed on the certificate, it is in the signed record, and a reprint dated
# differently from the issue the institution recorded is exactly the kind of
# difference a verifier should be shown. Leaving it out meant the result page
# said "not checked" beside a value we had in both hands.
CRITICAL_FIELDS = (
    "cert_number",
    "student_name",
    "roll_number",
    "programme",
    "year_of_passing",
    "cgpa",
    "marks",
    "issue_date",
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
    "issue_date": "The date of issue",
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


class FieldState(StrEnum):
    """What the document said about a field, beside whether its check passed.

    `status` answers "is this evidence for or against"; `state` answers "what
    is actually printed there", and the two come apart exactly where it
    matters. A value read at 76% that disagrees with the registry is
    `uncertain` as evidence — it cannot carry a MISMATCH on its own — but it
    *differs*, and a verifier must be shown that rather than a shrug. A value
    nobody could read differs from nothing.
    """

    MATCHES = "matches"
    DIFFERS = "differs"
    NOT_READ = "not_read"


@dataclass(frozen=True, slots=True)
class Check:
    """One piece of evidence behind the result. Stored in `verifications.checks`
    and shown to the verifier as-is, so `detail` is written for a human."""

    name: str
    status: CheckStatus
    detail: str
    # Only field_match entries carry this; the other checks compare nothing.
    state: FieldState | None = None

    def as_dict(self) -> dict[str, str]:
        out = {"name": self.name, "status": self.status.value, "detail": self.detail}
        if self.state is not None:
            out["state"] = self.state.value
        return out


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

    # At or above this, a field that disagrees is a conflict: MISMATCH.
    min_field_confidence: float = 0.85
    # At or above this (but below the one above), a field that disagrees is a
    # *possible* discrepancy: not certain enough to accuse the document, far
    # too clear to call it VERIFIED. Below it, the reading is too unsure to
    # mean anything and the field counts as not read.
    min_discrepancy_confidence: float = 0.50
    # How many critical fields must be read *and* match before an uploaded
    # document's printed content counts as confirmed. The student name must be
    # one of them (see `_document_content`).
    min_matched_fields: int = 3


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
    name: str, extracted: ExtractedFieldValue, expected: str, thresholds: Thresholds
) -> Check:
    """One field_match entry: what the document said, and what to make of it.

    Three bands, because confidence is not a yes/no. A reading that disagrees
    is a conflict only when the recogniser was sure of it; one it was
    moderately sure of is a discrepancy a human should look at; one it was
    unsure of is not a reading at all.
    """
    check_name = f"{CHECK_FIELD_MATCH}.{name}"
    found = extracted.value
    label = _label(name)

    if found is None:
        return Check(
            check_name,
            CheckStatus.UNCERTAIN,
            f"{label} could not be read from the document, so it was not checked against "
            f"the registry's {expected}.",
            state=FieldState.NOT_READ,
        )

    agrees = ids_match(found, expected) if name in _ID_FIELDS else found == expected
    if agrees:
        return Check(
            check_name,
            CheckStatus.PASS,
            f"{label} matches the registry: {expected}.",
            state=FieldState.MATCHES,
        )

    if extracted.confidence >= thresholds.min_field_confidence:
        return Check(
            check_name,
            CheckStatus.FAIL,
            f"{label} on the document is {found!r}, but the registry has {expected!r} "
            f"(read with {extracted.confidence:.0%} confidence).",
            state=FieldState.DIFFERS,
        )

    if extracted.confidence >= thresholds.min_discrepancy_confidence:
        return Check(
            check_name,
            CheckStatus.UNCERTAIN,
            f"{label} on the document reads {found!r}, but the registry has {expected!r}. "
            f"At {extracted.confidence:.0%} confidence that is not certain enough to call a "
            "conflict, so it is a possible discrepancy for a person to look at.",
            state=FieldState.DIFFERS,
        )

    return Check(
        check_name,
        CheckStatus.UNCERTAIN,
        f"{label} could not be read from the document — what was read ({found!r}) is only "
        f"{extracted.confidence:.0%} confident, too unsure to compare against the registry's "
        f"{expected}.",
        state=FieldState.NOT_READ,
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
                    f"{_label(name)} was not found on the document, so it was not checked "
                    f"against the registry's {expected}.",
                    state=FieldState.NOT_READ,
                )
            )
            continue
        checks.append(_compare_field(name, extracted, expected, data.thresholds))

    if not checks:
        return [
            Check(
                CHECK_FIELD_MATCH,
                CheckStatus.UNCERTAIN,
                "No critical field could be compared.",
            )
        ]
    return checks


def _document_content(data: VerificationInput, field_checks: list[Check]) -> Check:
    """Whether the *document* presented can be confirmed against the record.

    This is the check the QR cannot answer. A valid Ed25519 signature proves
    the registry record is genuine and was issued by the institution named in
    it; it says nothing about the sheet of paper in the verifier's hand, which
    may carry a real QR beside printed details that are unreadable, or simply
    not the ones that were signed. Treating the signature as the whole answer
    meant a document whose layout matched nothing at all — every field "not
    checked" — came back VERIFIED on the strength of someone else's record.

    So an uploaded document has to say who it belongs to before it is
    verified: the student name must have been read and matched, at least
    `min_matched_fields` critical fields must match, and nothing may differ.
    Anything less is reported as unconfirmed — `uncertain`, never `fail`,
    because an unreadable document is not a forged one.
    """
    if data.upload is None:
        return Check(CHECK_DOCUMENT_CONTENT, CheckStatus.SKIPPED, "No document was uploaded.")
    if data.record is None:
        return Check(
            CHECK_DOCUMENT_CONTENT,
            CheckStatus.SKIPPED,
            "No registry record to confirm the document's contents against.",
        )
    if data.record.file_sha256 and data.upload.sha256 == data.record.file_sha256:
        return Check(
            CHECK_DOCUMENT_CONTENT,
            CheckStatus.PASS,
            "The uploaded file is the issued certificate itself, so its contents are the "
            "institution's own.",
        )

    need = data.thresholds.min_matched_fields
    compared = [c for c in field_checks if c.state is not None]
    matched = [c for c in compared if c.state is FieldState.MATCHES]
    differing = [c for c in compared if c.state is FieldState.DIFFERS]
    name_matched = any(
        c.name == f"{CHECK_FIELD_MATCH}.student_name" and c.state is FieldState.MATCHES
        for c in compared
    )

    if data.upload.template is None:
        return Check(
            CHECK_DOCUMENT_CONTENT,
            CheckStatus.UNCERTAIN,
            "No known layout matched this document, so none of its printed details could be "
            "checked against the record it points to.",
        )
    if differing:
        said = (
            "A printed detail does not agree"
            if len(differing) == 1
            else f"{len(differing)} printed details do not agree"
        )
        return Check(
            CHECK_DOCUMENT_CONTENT,
            CheckStatus.UNCERTAIN,
            f"{said} with the record, so the document's contents are not confirmed.",
        )
    if not name_matched:
        return Check(
            CHECK_DOCUMENT_CONTENT,
            CheckStatus.UNCERTAIN,
            "The student name could not be read from this document and matched against the "
            "record, so there is nothing to confirm the document belongs to the person named "
            "in the registry.",
        )
    if len(matched) < need:
        return Check(
            CHECK_DOCUMENT_CONTENT,
            CheckStatus.UNCERTAIN,
            f"Only {len(matched)} of the {len(compared)} printed details could be matched "
            f"against the record; at least {need} are needed to confirm the document's "
            "contents.",
        )
    return Check(
        CHECK_DOCUMENT_CONTENT,
        CheckStatus.PASS,
        f"{len(matched)} of the {len(compared)} printed details match the record, including the "
        "student name, and none disagrees.",
    )


# --- decision -----------------------------------------------------------------


def _decide(data: VerificationInput, checks: list[Check]) -> VerificationResult:
    """Decision rules from the project spec, first match wins.

    The one thing to understand here: **VERIFIED requires that nothing
    differs**. A valid signature proves the registry record was issued by the
    institution; it says nothing about what is printed on the paper in front
    of the verifier. So a field that disagrees blocks VERIFIED even when the
    recogniser was only moderately sure of it — confidently, that is a
    MISMATCH; less confidently, it is a MANUAL_REVIEW for a person to settle.
    A field nobody could read is not a disagreement and blocks nothing.

    The same reasoning, taken one step further, is why **a document must also
    confirm itself**: when a file was uploaded and its bytes are not the
    issued PDF, a valid QR identifies the record but `document_content` has to
    confirm the page — otherwise an unreadable document borrows a genuine
    record's verdict. That verdict is MANUAL_REVIEW ("Unconfirmed"), never
    MISMATCH: nothing was found against the document, only nothing for it.
    """
    status = {c.name: c.status for c in checks}
    field_checks = [c for c in checks if c.name.startswith(f"{CHECK_FIELD_MATCH}.")]
    conflicting = [c for c in field_checks if c.status is CheckStatus.FAIL]
    differing = [c for c in field_checks if c.state is FieldState.DIFFERS]
    matched = [c for c in field_checks if c.state is FieldState.MATCHES]
    number_matched = any(c.name == f"{CHECK_FIELD_MATCH}.cert_number" for c in matched)

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
        # Rule 3: the verifier holds the exact file the institution issued, so
        # anything OCR thinks it read off it is a reading error, not evidence.
        return VerificationResult.VERIFIED
    if conflicting:
        # Rule 5: a critical field disagrees, read confidently enough to mean
        # it. This catches an altered document still carrying its original QR,
        # which is why a valid signature is checked *after* this.
        return VerificationResult.MISMATCH
    if differing:
        # A possible discrepancy: too unsure to accuse the document, far too
        # clear to call it verified. A person decides.
        return VerificationResult.MANUAL_REVIEW
    if data.upload is not None:
        # A document was presented, so VERIFIED is a statement about *it*, not
        # only about the record it points to. Two things are required, and the
        # QR can only supply the first:
        #
        #   identified — a valid QR signature, or the certificate number read
        #       off the page and matching, ties this document to this record;
        #   confirmed  — its printed contents agree with that record well
        #       enough to be worth anything (see `_document_content`).
        #
        # A genuine QR beside printed details nobody could read gets the first
        # and not the second: MANUAL_REVIEW, "Unconfirmed".
        identified = status[CHECK_QR_SIGNATURE] is CheckStatus.PASS or number_matched
        if identified and status[CHECK_DOCUMENT_CONTENT] is CheckStatus.PASS:
            return VerificationResult.VERIFIED
        return VerificationResult.MANUAL_REVIEW
    if status[CHECK_QR_SIGNATURE] is CheckStatus.PASS:
        # Rule 4 with no document in play: a scanned QR is a valid signature
        # over the registry record, and there is nothing else to confirm.
        return VerificationResult.VERIFIED
    if matched or not field_checks:
        # No upload: a signature-only or number-only verification, where the
        # number itself was the exact match.
        return VerificationResult.VERIFIED
    return VerificationResult.MANUAL_REVIEW


def evaluate(data: VerificationInput) -> VerificationOutcome:
    """Run every applicable check and decide. The checks come back in a stable
    order so the result page always lists them the same way."""
    field_checks = _field_match(data)
    checks = [
        _registry_lookup(data),
        _revocation(data),
        _record_signature(data),
        _qr_signature(data),
        _file_hash(data),
        *field_checks,
        # Last, because it is the conclusion drawn from the field checks above.
        _document_content(data, field_checks),
    ]
    return VerificationOutcome(result=_decide(data, checks), checks=checks)
