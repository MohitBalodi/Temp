"""OCR: text extraction, image preprocessing and field extraction.

Public surface for the rest of the app. Callers import from here rather than
from the concrete engine, so swapping the engine stays a one-file change.
"""

from app.services.ocr.engines import OcrEngine, OcrLine, TesseractEngine, get_engine
from app.services.ocr.extract_text import ExtractedPage, TextSource, extract
from app.services.ocr.fields import ExtractedField, ExtractionResult, extract_fields

__all__ = [
    "ExtractedField",
    "ExtractedPage",
    "ExtractionResult",
    "OcrEngine",
    "OcrLine",
    "TesseractEngine",
    "TextSource",
    "extract",
    "extract_fields",
    "get_engine",
]
