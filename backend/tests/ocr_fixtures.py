"""Document fixtures built inside the test run.

Everything here is generated from the project's own issuance code, so the
inputs under test are the real artefact rather than a checked-in sample that
could drift from it. There is no separate test-certificate generator — that is
explicitly out of scope in CLAUDE.md.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import cv2
import fitz
import numpy as np

from app.services.normalize import normalize_id, normalize_text
from app.services.pdf_issue import CertificatePdfData, build_certificate_pdf
from app.services.signing import CertificateRecord, load_or_create_private_key, sign_record

DEFAULT_CODE = "TST"


@dataclass(frozen=True, slots=True)
class SampleCertificate:
    """A certificate and the PDF bytes issued for it."""

    data: CertificatePdfData
    pdf: bytes

    @property
    def truth(self) -> dict[str, str]:
        """The field values a perfect extraction would produce.

        In *comparison* form, which is what `ExtractedField.value` holds:
        identifiers normalized, text uppercased, grades to two decimals. The
        document's own casing lives on `ExtractedField.raw`.
        """
        values = {
            "cert_number": normalize_id(self.data.cert_number),
            "roll_number": normalize_id(self.data.roll_number),
            "student_name": normalize_text(self.data.student_name),
            "programme": normalize_text(self.data.programme),
            "institution_code": normalize_id(self.data.institution_code),
            "year_of_passing": str(self.data.year_of_passing),
            "issue_date": self.data.issue_date.isoformat(),
        }
        if self.data.cgpa is not None:
            values["cgpa"] = f"{self.data.cgpa:.2f}"
        if self.data.marks is not None:
            values["marks"] = f"{self.data.marks:.2f}"
        return values


def make_certificate(
    *,
    cert_number: str = "TST2024CS0001",
    institution_code: str = DEFAULT_CODE,
    institution_name: str = "Test Institute (fictional)",
    student_name: str = "Aarav Sharma",
    roll_number: str = "21CS901",
    programme: str = "B.Tech Computer Science",
    year_of_passing: int = 2024,
    cgpa: Decimal | None = Decimal("8.50"),
    marks: Decimal | None = None,
    issue_date: date = date(2024, 7, 15),
) -> SampleCertificate:
    """Issue a certificate PDF exactly as the application would.

    The QR carries a real Ed25519 signature over the canonical record, so the
    signature checks in the verification engine are exercised for real.
    """
    key = load_or_create_private_key(institution_code)
    record = CertificateRecord(
        cert_number=cert_number,
        institution_code=institution_code,
        student_name=student_name,
        roll_number=roll_number,
        programme=programme,
        year_of_passing=year_of_passing,
        cgpa=cgpa,
        marks=marks,
        issue_date=issue_date,
    )
    signature = sign_record(key, record)

    data = CertificatePdfData(
        cert_number=cert_number,
        institution_name=institution_name,
        institution_code=institution_code,
        student_name=student_name,
        roll_number=roll_number,
        programme=programme,
        year_of_passing=year_of_passing,
        issue_date=issue_date,
        signature=signature,
        cgpa=cgpa,
        marks=marks,
    )
    return SampleCertificate(data=data, pdf=build_certificate_pdf(data))


# --- rendering and degradation ------------------------------------------------


def render_png(pdf: bytes, *, dpi: int = 200, page: int = 0) -> bytes:
    """Rasterise a PDF page to PNG, as scanning or screenshotting it would."""
    with fitz.open(stream=pdf, filetype="pdf") as doc:
        return doc[page].get_pixmap(dpi=dpi).tobytes("png")


def to_array(image_bytes: bytes) -> np.ndarray:
    array = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    assert array is not None, "fixture image did not decode"
    return array


def rotate_image(image: np.ndarray, degrees: float) -> np.ndarray:
    """Rotate about the centre on a white background, keeping the canvas size."""
    height, width = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), degrees, 1.0)
    return cv2.warpAffine(
        image,
        matrix,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )


def degrade(png: bytes, *, degrees: float = 5.0, blur: int = 3, jpeg_quality: int = 60) -> bytes:
    """A photographed-and-emailed version of a page: skewed, soft, recompressed.

    Returns JPEG bytes, so the lossy compression is part of what is tested.
    """
    image = to_array(png)
    if degrees:
        image = rotate_image(image, degrees)
    if blur:
        image = cv2.GaussianBlur(image, (blur, blur), 0)
    ok, encoded = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality])
    assert ok, "fixture JPEG encoding failed"
    return encoded.tobytes()


def to_jpeg(png: bytes, *, quality: int = 90) -> bytes:
    ok, encoded = cv2.imencode(".jpg", to_array(png), [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    assert ok
    return encoded.tobytes()


def noise_image(*, width: int = 900, height: int = 640, seed: int = 7) -> bytes:
    """A random non-certificate image: no template, no text worth reading."""
    rng = np.random.default_rng(seed)
    array = rng.integers(0, 256, size=(height, width, 3), dtype=np.uint8)
    ok, encoded = cv2.imencode(".png", array)
    assert ok
    return encoded.tobytes()


def photo_of_certificate(png: bytes, *, margin: int = 90) -> bytes:
    """The page photographed on a darker surface, so a page outline exists.

    Exercises the perspective/crop path, which is skipped when the document
    already fills the frame.
    """
    page = to_array(png)
    height, width = page.shape[:2]
    canvas = np.full((height + margin * 2, width + margin * 2, 3), 70, dtype=np.uint8)
    canvas[margin : margin + height, margin : margin + width] = page
    ok, encoded = cv2.imencode(".png", canvas)
    assert ok
    return encoded.tobytes()


# --- tampering ----------------------------------------------------------------


def edit_pdf_text(pdf: bytes, old: str, new: str, *, fontsize: float = 11) -> bytes:
    """Replace a string on page 1 for real, leaving the QR untouched.

    This is what an altered document looks like: the printed value no longer
    agrees with the signed record, while the QR still carries the original
    signature over the original values.

    Uses a redaction annotation, which *removes* the old glyphs from the
    content stream. Merely drawing a white rectangle over them would not:
    PyMuPDF — and so our PDF text-layer path — still extracts the text
    underneath such a box. `cover_pdf_text` does that on purpose, for the test
    that documents the limitation.
    """
    with fitz.open(stream=pdf, filetype="pdf") as doc:
        page = doc[0]
        hits = page.search_for(old)
        assert hits, f"{old!r} not found on the page"
        rect = hits[0]

        page.add_redact_annot(rect, fill=(1, 1, 1))
        page.apply_redactions()
        page.insert_text(
            fitz.Point(rect.x0, rect.y1 - fontsize * 0.22),
            new,
            fontname="Helvetica-Bold",
            fontsize=fontsize,
            color=(0, 0, 0),
        )
        out = io.BytesIO()
        doc.save(out)
        return out.getvalue()


def cover_pdf_text(pdf: bytes, old: str, new: str, *, fontsize: float = 11) -> bytes:
    """Draw a white box over a value and print a different one on top.

    The original glyphs stay in the content stream, so a text-layer reader
    still sees the original value while a human sees the new one. Used by the
    test that pins this known limitation.
    """
    with fitz.open(stream=pdf, filetype="pdf") as doc:
        page = doc[0]
        hits = page.search_for(old)
        assert hits, f"{old!r} not found on the page"
        rect = hits[0]

        page.draw_rect(rect, color=None, fill=(1, 1, 1), overlay=True)
        page.insert_text(
            fitz.Point(rect.x0, rect.y1 - fontsize * 0.22),
            new,
            fontname="Helvetica-Bold",
            fontsize=fontsize,
            color=(0, 0, 0),
            overlay=True,
        )
        out = io.BytesIO()
        doc.save(out)
        return out.getvalue()
