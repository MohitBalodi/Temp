"""The QR payload carried by an issued certificate.

Format (see the project spec, "Signing & QR"):

    AVA1|<cert_number>|<institution_code>|<signature>

Deliberately short: it holds no personal data. A verifier parses the payload,
looks the record up by number and re-checks the signature against the
institution's public key, so the QR itself is not the source of truth.
"""

import io
import re
from dataclasses import dataclass

import qrcode
from qrcode.constants import ERROR_CORRECT_M

from app.services.normalize import normalize_id

PREFIX = "AVA1"
SEPARATOR = "|"
_PART_COUNT = 4
# base64url without padding — the signature can never contain the separator.
_SIGNATURE = re.compile(r"^[A-Za-z0-9_-]+$")


class QrPayloadError(ValueError):
    """The text is not a well-formed AVA1 payload."""


@dataclass(frozen=True, slots=True)
class QrPayload:
    """A parsed payload. IDs come out in normalized form."""

    cert_number: str
    institution_code: str
    signature: str

    def encode(self) -> str:
        return build_payload(self.cert_number, self.institution_code, self.signature)


def build_payload(cert_number: str, institution_code: str, signature: str) -> str:
    """Render the payload for a certificate. IDs are normalized, so the payload
    of a record always matches what is stored."""
    number = normalize_id(cert_number)
    code = normalize_id(institution_code)
    signature = signature.strip()
    if not number:
        raise QrPayloadError("cert_number is empty after normalization.")
    if not code:
        raise QrPayloadError("institution_code is empty after normalization.")
    if not _SIGNATURE.match(signature):
        raise QrPayloadError("signature is not base64url text.")
    return SEPARATOR.join((PREFIX, number, code, signature))


def parse_payload(text: str) -> QrPayload:
    """Parse a scanned payload. Raises `QrPayloadError` on anything malformed."""
    if not isinstance(text, str) or not text.strip():
        raise QrPayloadError("Payload is empty.")

    parts = text.strip().split(SEPARATOR)
    if len(parts) != _PART_COUNT:
        raise QrPayloadError(
            f"Payload must have {_PART_COUNT} parts separated by '{SEPARATOR}', got {len(parts)}."
        )

    prefix, number, code, signature = (p.strip() for p in parts)
    if prefix.upper() != PREFIX:
        raise QrPayloadError(f"Unknown payload prefix {prefix!r}; expected {PREFIX}.")

    # Reuse build_payload's validation, then return the normalized pieces.
    build_payload(number, code, signature)
    return QrPayload(
        cert_number=normalize_id(number),
        institution_code=normalize_id(code),
        signature=signature,
    )


def qr_png(data: str, *, box_size: int = 4, border: int = 2) -> bytes:
    """PNG bytes of the QR code for `data`."""
    code = qrcode.QRCode(error_correction=ERROR_CORRECT_M, box_size=box_size, border=border)
    code.add_data(data)
    code.make(fit=True)
    buffer = io.BytesIO()
    code.make_image(fill_color="black", back_color="white").save(buffer, format="PNG")
    return buffer.getvalue()
