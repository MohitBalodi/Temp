"""OCR engine interface and the Tesseract implementation.

The pipeline (`extract_text.py`) depends only on `OcrEngine` and `OcrLine`, so a
second engine — PaddleOCR, a cloud OCR, anything — can be added by implementing
the protocol and returning it from `get_engine()`. Nothing else changes.

Pure in the sense that matters for testing: an engine takes a numpy image and
returns lines. No DB, no HTTP, no settings lookups at call time.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class OcrLine:
    """One recognised line of text with the engine's confidence for it.

    `confidence` is 0.0–1.0. `bbox` is (x, y, w, h) in pixels on the image the
    engine was given, or None when the engine does not report geometry.
    """

    text: str
    confidence: float
    bbox: tuple[int, int, int, int] | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence out of range: {self.confidence!r}")


@runtime_checkable
class OcrEngine(Protocol):
    """What the pipeline needs from an OCR engine."""

    name: str

    def is_available(self) -> bool:
        """True when the engine can actually run (binary present, model loaded)."""
        ...

    def recognise(self, image: np.ndarray, *, lang: str = "eng") -> list[OcrLine]:
        """Recognise text in a single-page image, one entry per text line.

        `image` is a numpy array as OpenCV produces it: HxW grayscale or HxWx3
        BGR, dtype uint8. Lines are returned in reading order where the engine
        provides it. An image with no detectable text yields an empty list,
        which is not an error.
        """
        ...


class TesseractEngine:
    """pytesseract-backed engine.

    Confidence comes from Tesseract's own per-word `conf` (0–100, with -1 for
    entries it declines to score). A line's confidence is the mean of its
    scored words, so a line where Tesseract is unsure drags its own score down
    rather than the whole page's.
    """

    name = "tesseract"

    # Tesseract page segmentation: 6 = assume a single uniform block of text.
    # Certificates are laid out as labelled lines, not columns or sparse text,
    # and PSM 6 is markedly steadier on them than the default PSM 3.
    def __init__(self, psm: int = 6, oem: int = 3) -> None:
        self._psm = psm
        self._oem = oem
        self._available: bool | None = None

    def _config(self) -> str:
        return f"--oem {self._oem} --psm {self._psm}"

    def is_available(self) -> bool:
        if self._available is None:
            try:
                import pytesseract

                pytesseract.get_tesseract_version()
                self._available = True
            except Exception:  # pragma: no cover - environment dependent
                logger.warning("tesseract is not available", exc_info=True)
                self._available = False
        return self._available

    def recognise(self, image: np.ndarray, *, lang: str = "eng") -> list[OcrLine]:
        import pytesseract
        from pytesseract import Output

        if image is None or image.size == 0:
            return []

        data = pytesseract.image_to_data(
            image, lang=lang, config=self._config(), output_type=Output.DICT
        )
        return _lines_from_tsv(data)


def _lines_from_tsv(data: dict[str, list]) -> list[OcrLine]:
    """Group pytesseract's per-word output into lines.

    Tesseract numbers every word by (block, paragraph, line); words sharing
    that triple are one line. Kept separate from the engine so it can be
    unit-tested on a plain dict with no Tesseract installed.
    """
    groups: dict[tuple[int, int, int], list[int]] = {}
    order: list[tuple[int, int, int]] = []

    for i, raw in enumerate(data.get("text", [])):
        if not str(raw).strip():
            continue
        key = (
            int(data["block_num"][i]),
            int(data["par_num"][i]),
            int(data["line_num"][i]),
        )
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(i)

    lines: list[OcrLine] = []
    for key in order:
        idxs = groups[key]
        words = [str(data["text"][i]).strip() for i in idxs]
        text = _collapse_spaces(" ".join(w for w in words if w))
        if not text:
            continue

        scored = [float(data["conf"][i]) for i in idxs if float(data["conf"][i]) >= 0]
        confidence = (sum(scored) / len(scored) / 100.0) if scored else 0.0
        # Clamp: Tesseract has been seen to emit conf slightly above 100.
        confidence = max(0.0, min(1.0, confidence))

        lefts = [int(data["left"][i]) for i in idxs]
        tops = [int(data["top"][i]) for i in idxs]
        rights = [int(data["left"][i]) + int(data["width"][i]) for i in idxs]
        bottoms = [int(data["top"][i]) + int(data["height"][i]) for i in idxs]
        bbox = (
            min(lefts),
            min(tops),
            max(rights) - min(lefts),
            max(bottoms) - min(tops),
        )

        lines.append(OcrLine(text=text, confidence=confidence, bbox=bbox))

    return lines


def _collapse_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


_DEFAULT_ENGINE: TesseractEngine | None = None


def get_engine() -> OcrEngine:
    """The engine the pipeline should use.

    One module-level instance, so the availability probe is paid once per
    process. When PaddleOCR is added this is the only function that changes.
    """
    global _DEFAULT_ENGINE
    if _DEFAULT_ENGINE is None:
        _DEFAULT_ENGINE = TesseractEngine()
    return _DEFAULT_ENGINE
