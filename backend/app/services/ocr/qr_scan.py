"""Reading the signed QR off a page, before anything else touches the image.

The QR is the strongest evidence a photographed certificate carries. It holds
the institution's Ed25519 signature, so it is checked by cryptography rather
than by comparing characters, and its error correction survives blur, shadow
and a phone's JPEG compression far better than the 7 pt grey labels beside it.
That makes the order matter: the code is read from the image **as uploaded**,
before `preprocess` gets a chance to threshold, deskew or crop away the pixels
the decoder needs.

Two readers and three scales, tried in order, stopping at the first valid AVA1
payload:

    zxing-cpp at 1x, 2x, 3x   then   pyzbar at 1x, 2x, 3x

Measured on `samples/photos` (12 phone photos of two printed certificates):
zxing-cpp read 11 of 12 at the photo's own resolution and all 12 once a 2x
upscale was allowed, in 1-43 ms. pyzbar read 2 of 12 at 1x, 10 of 12 at 2x,
and never read sample3 at any scale, taking 12-242 ms. So zxing-cpp goes
first, and pyzbar stays as a fallback rather than being replaced: it is
already a dependency, and the two libraries do not fail on the same images.

Upscaling helps because both readers need a minimum number of pixels per QR
module; cubic interpolation does not add information, but it does give the
binarizer and the perspective-correction step more to work with.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

import cv2
import numpy as np

from app.services.qr import QrPayloadError, parse_payload

logger = logging.getLogger(__name__)

READER_ZXING = "zxing"
READER_PYZBAR = "pyzbar"

# Tried in this order. 1x first: a photo of a whole certificate usually has
# enough modules already, and a hit there costs milliseconds.
SCALES = (1, 2, 3)

# An upscale producing more pixels than this is skipped. A 12 MP phone photo
# at 3x is 108 MP, which costs seconds and hundreds of megabytes to learn
# nothing — a code photographed that large is readable at 1x.
MAX_SCALED_PIXELS = 40_000_000


@dataclass(frozen=True, slots=True)
class QrSymbol:
    """A decoded QR, where it sits, and what found it.

    `rect` is `(left, top, width, height)` in the coordinates of the image
    that was handed in — not of the upscaled copy it may have been found on —
    so the caller can mask the code out of its own image whatever scale won.
    """

    payload: str
    rect: tuple[int, int, int, int]
    reader: str = ""
    scale: int = 1

    @property
    def is_certificate_payload(self) -> bool:
        return is_certificate_payload(self.payload)


def is_certificate_payload(text: str) -> bool:
    """Whether this text is a well-formed AVA1 certificate payload.

    The ladder stops at the first one of these rather than at the first code
    of any kind, because a page may also carry a library sticker or a printer
    barcode, and climbing one more rung is cheap compared with losing the
    signature.
    """
    try:
        parse_payload(text)
    except QrPayloadError:
        return False
    return True


def _upscaled(image: np.ndarray, scale: int) -> np.ndarray | None:
    """`image` enlarged by `scale`, or None when that is too big to be worth it."""
    if scale == 1:
        return image
    height, width = image.shape[:2]
    if height * width * scale * scale > MAX_SCALED_PIXELS:
        return None
    return cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)


def _shrink(rect: tuple[int, int, int, int], scale: int) -> tuple[int, int, int, int]:
    """A rect found on an upscaled copy, back in the original's coordinates."""
    if scale == 1:
        return rect
    left, top, width, height = rect
    return (left // scale, top // scale, width // scale, height // scale)


def _read_zxing(image: np.ndarray) -> list[tuple[str, tuple[int, int, int, int]]]:
    import zxingcpp

    found = []
    for barcode in zxingcpp.read_barcodes(image, formats=zxingcpp.BarcodeFormat.QRCode):
        if not barcode.text:
            continue
        position = barcode.position
        corners = (
            position.top_left,
            position.top_right,
            position.bottom_right,
            position.bottom_left,
        )
        xs = [point.x for point in corners]
        ys = [point.y for point in corners]
        # zxing reports the four corners of the (possibly rotated) code; the
        # axis-aligned box around them is what masking needs.
        found.append((barcode.text, (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))))
    return found


def _read_pyzbar(image: np.ndarray) -> list[tuple[str, tuple[int, int, int, int]]]:
    from pyzbar.pyzbar import ZBarSymbol
    from pyzbar.pyzbar import decode as zbar_decode

    found = []
    for symbol in zbar_decode(image, symbols=[ZBarSymbol.QRCODE]):
        try:
            payload = symbol.data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        rect = symbol.rect
        found.append((payload, (rect.left, rect.top, rect.width, rect.height)))
    return found


_Found = list[tuple[str, tuple[int, int, int, int]]]
_Reader = Callable[[np.ndarray], _Found]

# Order matters: zxing-cpp first, on measurement (see the module docstring).
_READERS: tuple[tuple[str, _Reader], ...] = (
    (READER_ZXING, _read_zxing),
    (READER_PYZBAR, _read_pyzbar),
)


def scan(image: np.ndarray) -> list[QrSymbol]:
    """Every QR found by the first attempt that reads a certificate payload.

    Failures are swallowed: a document with no readable QR is an ordinary
    case, not an error. If no attempt yields an AVA1 payload, the first codes
    found by any attempt are returned instead — a non-certificate code is
    still worth masking out before OCR, and `upload_verification` decides what
    to make of it.
    """
    fallback: list[QrSymbol] = []

    for reader, read in _READERS:
        for scale in SCALES:
            scaled = _upscaled(image, scale)
            if scaled is None:
                continue
            try:
                found = read(scaled)
            except Exception:  # pragma: no cover - both readers are permissive
                logger.debug("%s failed at %dx", reader, scale, exc_info=True)
                continue
            if not found:
                continue
            symbols = [
                QrSymbol(payload=payload, rect=_shrink(rect, scale), reader=reader, scale=scale)
                for payload, rect in found
            ]
            if any(symbol.is_certificate_payload for symbol in symbols):
                logger.info("QR read by %s at %dx", reader, scale)
                return symbols
            if not fallback:
                fallback = symbols

    return fallback


def payloads(image: np.ndarray) -> list[str]:
    """Just the payload text, for callers that do not care where the code was."""
    return [symbol.payload for symbol in scan(image)]


__all__ = [
    "MAX_SCALED_PIXELS",
    "READER_PYZBAR",
    "READER_ZXING",
    "SCALES",
    "QrSymbol",
    "is_certificate_payload",
    "payloads",
    "scan",
]
