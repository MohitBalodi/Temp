"""Getting text (and any QR payload) out of an uploaded document.

Two paths, chosen by what the file actually contains:

* A PDF with a real text layer — which is what our own issued certificates
  are — is read with PyMuPDF. No OCR, no preprocessing, exact characters,
  confidence 1.0. This is the fast, lossless path and it is tried first.
* An image, or a PDF whose pages are scans, goes through `preprocess` and then
  the OCR engine. Characters are a guess, so every line carries the engine's
  confidence.

Either way the result is the same `ExtractedPage`, so `fields.py` never needs
to know which path produced it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum

import fitz
import numpy as np

from app.services.ocr.engines import OcrEngine, OcrLine, get_engine
from app.services.ocr.preprocess import decode_image, mask_regions, prepare

logger = logging.getLogger(__name__)

# Rendering resolution for a PDF page that has to be OCRed. 300 DPI is what
# Tesseract is tuned for; higher costs time without improving these layouts.
RENDER_DPI = 300

# A page with fewer than this many characters of embedded text is treated as
# image-only. A scanned PDF often carries a handful of stray characters from
# the scanner's own stamp, which is not a text layer.
MIN_TEXT_LAYER_CHARS = 120

# Digital text is exact, so it is not a confidence estimate at all.
TEXT_LAYER_CONFIDENCE = 1.0

MIME_PDF = "application/pdf"


class TextSource(StrEnum):
    """Where the text came from. Surfaced in the evidence, because it changes
    how much the field values can be trusted."""

    PDF_TEXT_LAYER = "pdf_text_layer"
    OCR = "ocr"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class ExtractedPage:
    """Text and QR payloads from the first page of a document."""

    lines: list[OcrLine]
    source: TextSource
    qr_payloads: list[str] = field(default_factory=list)
    engine: str | None = None

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines)

    @property
    def mean_confidence(self) -> float:
        if not self.lines:
            return 0.0
        return sum(line.confidence for line in self.lines) / len(self.lines)

    @property
    def is_empty(self) -> bool:
        return not self.lines


# --- QR -----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class QrSymbol:
    """A decoded QR and where it sits, as (left, top, width, height)."""

    payload: str
    rect: tuple[int, int, int, int]


def decode_qr(image: np.ndarray) -> list[QrSymbol]:
    """Every QR readable from the image, with its position.

    Failures are swallowed: a document with no readable QR is an ordinary
    case, not an error. Decoding is attempted on the image as given and, if
    that finds nothing, on a prepared copy — a low-contrast photo often needs
    the second attempt. Only coordinates from the first (untransformed)
    attempt are reported, since those are the ones that line up with the
    caller's image.
    """
    from pyzbar.pyzbar import ZBarSymbol
    from pyzbar.pyzbar import decode as zbar_decode

    attempts: list[tuple[np.ndarray, bool]] = [(image, True)]
    try:
        attempts.append((prepare(image, binarise=False), False))
    except Exception:  # pragma: no cover - preprocessing is best effort here
        logger.debug("preprocessing for QR decode failed", exc_info=True)

    for candidate, coordinates_valid in attempts:
        try:
            found = zbar_decode(candidate, symbols=[ZBarSymbol.QRCODE])
        except Exception:  # pragma: no cover - zbar is permissive but not total
            logger.debug("zbar decode failed", exc_info=True)
            continue

        symbols: list[QrSymbol] = []
        for symbol in found:
            try:
                payload = symbol.data.decode("utf-8")
            except UnicodeDecodeError:
                continue
            rect = (
                (symbol.rect.left, symbol.rect.top, symbol.rect.width, symbol.rect.height)
                if coordinates_valid
                else (0, 0, 0, 0)
            )
            symbols.append(QrSymbol(payload=payload, rect=rect))
        if symbols:
            return symbols
    return []


def decode_qr_payloads(image: np.ndarray) -> list[str]:
    """Just the payloads, for callers that do not care where the code was."""
    return [symbol.payload for symbol in decode_qr(image)]


# --- PDF ----------------------------------------------------------------------


def _lines_from_pdf_page(page: fitz.Page) -> list[OcrLine]:
    """The page's embedded text, one entry per layout line.

    PyMuPDF's dict output already groups spans into lines in reading order,
    which is exactly the structure label-anchored extraction needs.
    """
    lines: list[OcrLine] = []
    data = page.get_text("dict")
    for block in data.get("blocks", []):
        if block.get("type") != 0:  # 0 = text, 1 = image
            continue
        for line in block.get("lines", []):
            text = "".join(span.get("text", "") for span in line.get("spans", [])).strip()
            if not text:
                continue
            x0, y0, x1, y1 = line.get("bbox", (0, 0, 0, 0))
            lines.append(
                OcrLine(
                    text=" ".join(text.split()),
                    confidence=TEXT_LAYER_CONFIDENCE,
                    bbox=(int(x0), int(y0), int(x1 - x0), int(y1 - y0)),
                )
            )
    return lines


def _render_page(page: fitz.Page, dpi: int = RENDER_DPI) -> np.ndarray:
    """Rasterise a PDF page to a BGR array for OCR and QR decoding."""
    pixmap = page.get_pixmap(dpi=dpi)
    array = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
        pixmap.height, pixmap.width, pixmap.n
    )
    if pixmap.n == 4:
        return array[:, :, [2, 1, 0]].copy()
    if pixmap.n == 3:
        return array[:, :, ::-1].copy()
    return array.copy()


def _qr_from_pdf_page(doc: fitz.Document, page: fitz.Page) -> list[str]:
    """QR payloads on a PDF page.

    The embedded images are tried first — the QR is one of them, at its
    original resolution — and the rendered page only if that finds nothing.
    """
    for xref, *_ in page.get_images(full=True):
        try:
            raw = doc.extract_image(xref)["image"]
        except Exception:  # pragma: no cover - malformed embedded image
            continue
        image = decode_image(raw)
        if image is None:
            continue
        if payloads := decode_qr_payloads(image):
            return payloads
    return decode_qr_payloads(_render_page(page))


def extract_from_pdf(data: bytes, *, engine: OcrEngine | None = None) -> ExtractedPage:
    """Extract from the first page of a PDF, preferring its text layer."""
    with fitz.open(stream=data, filetype="pdf") as doc:
        if doc.page_count == 0:
            return ExtractedPage(lines=[], source=TextSource.NONE)

        page = doc[0]
        qr_payloads = _qr_from_pdf_page(doc, page)
        lines = _lines_from_pdf_page(page)
        embedded_chars = sum(len(line.text) for line in lines)

        if embedded_chars >= MIN_TEXT_LAYER_CHARS:
            return ExtractedPage(
                lines=lines, source=TextSource.PDF_TEXT_LAYER, qr_payloads=qr_payloads
            )

        # Image-only (or near enough): rasterise and OCR.
        logger.info("pdf has %d chars of text layer; falling back to OCR", embedded_chars)
        image = _render_page(page)

    ocr_page = extract_from_image_array(image, engine=engine)
    return ExtractedPage(
        lines=ocr_page.lines,
        source=ocr_page.source,
        qr_payloads=qr_payloads or ocr_page.qr_payloads,
        engine=ocr_page.engine,
    )


# --- images -------------------------------------------------------------------


def extract_from_image_array(
    image: np.ndarray, *, engine: OcrEngine | None = None
) -> ExtractedPage:
    """Preprocess and OCR an image already decoded into an array."""
    ocr = engine or get_engine()
    symbols = decode_qr(image)
    qr_payloads = [s.payload for s in symbols]

    if not ocr.is_available():
        logger.error("no OCR engine available; returning no text")
        return ExtractedPage(lines=[], source=TextSource.NONE, qr_payloads=qr_payloads)

    # Blank the QR before OCR: its modules would otherwise be read as text on
    # the same baselines as the boxed fields beside it.
    regions = [s.rect for s in symbols if s.rect[2] > 0 and s.rect[3] > 0]
    prepared = prepare(mask_regions(image, regions))
    lines = ocr.recognise(prepared)
    return ExtractedPage(
        lines=lines,
        source=TextSource.OCR if lines else TextSource.NONE,
        qr_payloads=qr_payloads,
        engine=ocr.name,
    )


def extract_from_image(data: bytes, *, engine: OcrEngine | None = None) -> ExtractedPage:
    """Extract from image bytes (PNG/JPEG)."""
    image = decode_image(data)
    if image is None:
        logger.warning("could not decode %d bytes as an image", len(data))
        return ExtractedPage(lines=[], source=TextSource.NONE)
    return extract_from_image_array(image, engine=engine)


# --- entry point --------------------------------------------------------------


def extract(data: bytes, mime: str, *, engine: OcrEngine | None = None) -> ExtractedPage:
    """Extract text and QR payloads from an uploaded document.

    Never raises for an unreadable document: an empty `ExtractedPage` is a
    legitimate outcome that the engine turns into MANUAL_REVIEW.
    """
    try:
        if mime == MIME_PDF:
            return extract_from_pdf(data, engine=engine)
        return extract_from_image(data, engine=engine)
    except Exception:
        logger.exception("extraction failed for a %s upload of %d bytes", mime, len(data))
        return ExtractedPage(lines=[], source=TextSource.NONE)
