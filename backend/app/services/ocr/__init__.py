"""OCR: text extraction, image preprocessing and field extraction.

Public surface for the rest of the app. Importing the engine from here keeps
callers off the concrete implementation.
"""

from app.services.ocr.engines import OcrEngine, OcrLine, TesseractEngine, get_engine

__all__ = ["OcrEngine", "OcrLine", "TesseractEngine", "get_engine"]
