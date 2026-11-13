"""The issued certificate PDF (ReportLab).

A4 landscape, one page, with the signed QR payload bottom-right and a diagonal
"SPECIMEN" watermark — this is a prototype and every certificate it issues is
synthetic.

The PDF is built once, when the certificate is created or imported: its
SHA-256 goes into `certificates.file_sha256` and the stored file is what
`GET /certificates/{id}/pdf` serves. Nothing regenerates it, so the stored hash
always matches the bytes a verifier downloads.
"""

import io
import os
import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from app.core.config import settings
from app.services.normalize import format_decimal
from app.services.qr import build_payload, qr_png

PAGE_SIZE = landscape(A4)  # 297 x 210 mm
WATERMARK_TEXT = "SPECIMEN — NOT A REAL DOCUMENT"
FOOTER_TEXT = "Prototype issuance — synthetic data, not a real academic document."
QR_SIZE = 34 * mm


@dataclass(frozen=True, slots=True)
class CertificatePdfData:
    """Everything printed on the certificate. No DB or ORM types."""

    cert_number: str
    institution_name: str
    institution_code: str
    student_name: str
    roll_number: str
    programme: str
    year_of_passing: int
    issue_date: date
    signature: str
    cgpa: Decimal | None = None
    marks: Decimal | None = None

    @property
    def grade_line(self) -> str:
        if self.cgpa is not None:
            return f"CGPA {format_decimal(self.cgpa)} / 10.00"
        if self.marks is not None:
            return f"Marks {format_decimal(self.marks)}%"
        return "Grade not recorded"


def _draw_watermark(pdf: canvas.Canvas, width: float, height: float) -> None:
    pdf.saveState()
    pdf.setFillGray(0.88)
    pdf.setFont("Helvetica-Bold", 38)
    pdf.translate(width / 2, height / 2)
    pdf.rotate(26)
    pdf.drawCentredString(0, 0, WATERMARK_TEXT)
    pdf.restoreState()


def _draw_border(pdf: canvas.Canvas, width: float, height: float) -> None:
    pdf.saveState()
    pdf.setStrokeGray(0.25)
    pdf.setLineWidth(2)
    pdf.rect(12 * mm, 12 * mm, width - 24 * mm, height - 24 * mm)
    pdf.setLineWidth(0.5)
    pdf.rect(14 * mm, 14 * mm, width - 28 * mm, height - 28 * mm)
    pdf.restoreState()


def _draw_field(pdf: canvas.Canvas, x: float, y: float, label: str, value: str) -> None:
    pdf.setFillGray(0.45)
    pdf.setFont("Helvetica", 8)
    pdf.drawString(x, y, label.upper())
    pdf.setFillGray(0)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(x, y - 6 * mm, value)


def build_certificate_pdf(data: CertificatePdfData) -> bytes:
    """Render the one-page certificate and return the PDF bytes."""
    width, height = PAGE_SIZE
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=PAGE_SIZE)
    pdf.setTitle(f"{data.cert_number} — {data.institution_code}")
    pdf.setAuthor(data.institution_name)
    pdf.setSubject("Prototype academic certificate (synthetic data)")

    _draw_watermark(pdf, width, height)
    _draw_border(pdf, width, height)

    centre = width / 2
    pdf.setFillGray(0)
    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawCentredString(centre, height - 32 * mm, data.institution_name)

    pdf.setFillGray(0.4)
    pdf.setFont("Helvetica", 9)
    pdf.drawCentredString(centre, height - 38 * mm, f"Institution code {data.institution_code}")

    pdf.setStrokeGray(0.7)
    pdf.setLineWidth(0.5)
    pdf.line(centre - 60 * mm, height - 44 * mm, centre + 60 * mm, height - 44 * mm)

    pdf.setFillGray(0.3)
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawCentredString(centre, height - 54 * mm, "DEGREE CERTIFICATE")

    pdf.setFillGray(0)
    pdf.setFont("Helvetica", 12)
    pdf.drawCentredString(centre, height - 74 * mm, "This is to certify that")

    pdf.setFont("Helvetica-Bold", 26)
    pdf.drawCentredString(centre, height - 90 * mm, data.student_name)

    pdf.setFont("Helvetica", 12)
    pdf.drawCentredString(centre, height - 102 * mm, "has successfully completed the programme")

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(centre, height - 116 * mm, data.programme)

    pdf.setFont("Helvetica", 12)
    pdf.drawCentredString(
        centre,
        height - 130 * mm,
        f"Year of passing {data.year_of_passing}    \u00b7    {data.grade_line}",
    )

    _draw_field(pdf, 24 * mm, 58 * mm, "Certificate number", data.cert_number)
    _draw_field(pdf, 24 * mm, 42 * mm, "Roll number", data.roll_number)
    _draw_field(pdf, 24 * mm, 26 * mm, "Date of issue", data.issue_date.isoformat())

    payload = build_payload(data.cert_number, data.institution_code, data.signature)
    qr_x = width - 24 * mm - QR_SIZE
    qr_y = 28 * mm
    pdf.drawImage(
        ImageReader(io.BytesIO(qr_png(payload))),
        qr_x,
        qr_y,
        width=QR_SIZE,
        height=QR_SIZE,
        preserveAspectRatio=True,
        anchor="sw",
        mask="auto",
    )
    pdf.setFillGray(0.4)
    pdf.setFont("Helvetica", 8)
    pdf.drawCentredString(qr_x + QR_SIZE / 2, qr_y - 5 * mm, "Scan to verify")

    pdf.setFillGray(0.45)
    pdf.setFont("Helvetica", 8)
    pdf.drawCentredString(centre, 18 * mm, FOOTER_TEXT)

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


# --- stored file --------------------------------------------------------------


def issued_pdf_path(cert_id: uuid.UUID) -> Path:
    """Where the issued PDF for this certificate lives (one file per record)."""
    return Path(settings.issued_dir) / f"{cert_id}.pdf"


def write_issued_pdf(cert_id: uuid.UUID, pdf: bytes) -> Path:
    """Write the PDF atomically (temp file + rename) so a reader never sees a
    half-written file. Raises `OSError` if the volume is not writable."""
    path = issued_pdf_path(cert_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        tmp.write_bytes(pdf)
        os.replace(tmp, path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise
    return path


def delete_issued_pdf(cert_id: uuid.UUID) -> None:
    """Remove a stored PDF; used to undo writes when the transaction rolls back."""
    issued_pdf_path(cert_id).unlink(missing_ok=True)
