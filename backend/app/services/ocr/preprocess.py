"""Image preparation before OCR (OpenCV).

Pure functions over numpy arrays: no files, no settings, no engine. Each step
is separately testable and separately skippable, because every one of them can
make a clean image worse — a scan of our own freshly rendered PDF needs almost
none of this, while a phone photo needs all of it.

Order matters. Perspective is corrected first, while the page outline is still
findable; deskew then fixes the residual rotation; thresholding comes last, so
the earlier steps work on continuous tones rather than on hard black and white.
"""

from __future__ import annotations

import cv2
import numpy as np

# Deskew refuses corrections beyond this: a larger estimate means the angle
# finder locked onto something that is not the text baseline, and rotating by
# it would make the page worse.
MAX_DESKEW_DEGREES = 15.0

# Below this the angle is noise and rotating costs a resample for nothing.
MIN_DESKEW_DEGREES = 0.1

# A detected quadrilateral must cover at least this fraction of the image to be
# treated as the page outline, so a photo of a certificate on a desk is
# cropped but a stray rectangle inside the layout is not.
MIN_PAGE_AREA_RATIO = 0.35


def to_grayscale(image: np.ndarray) -> np.ndarray:
    """Single-channel uint8. Already-gray input is returned unchanged."""
    if image.ndim == 2:
        return image
    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def denoise(image: np.ndarray, *, strength: int = 7) -> np.ndarray:
    """Remove sensor and compression noise while keeping glyph edges.

    Non-local means rather than a blur: JPEG artefacts around text are exactly
    what a Gaussian would smear into the strokes.
    """
    gray = to_grayscale(image)
    return cv2.fastNlMeansDenoising(
        gray, None, h=strength, templateWindowSize=7, searchWindowSize=21
    )


def estimate_skew(image: np.ndarray) -> float:
    """Text baseline angle in degrees; positive means the page leans clockwise.

    Found from the minimum-area rectangle around the dark pixels, which is
    stable on a page of text lines and cheap compared with a Hough transform.
    Returns 0.0 when there is nothing to measure.
    """
    gray = to_grayscale(image)
    # Invert: text becomes the foreground that minAreaRect should enclose.
    inverted = cv2.bitwise_not(gray)
    _, mask = cv2.threshold(inverted, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

    coords = cv2.findNonZero(mask)
    if coords is None or len(coords) < 50:
        return 0.0

    angle = cv2.minAreaRect(coords)[-1]
    # OpenCV reports 0–90; map onto the nearest axis so a near-upright page
    # does not read as an 89-degree rotation.
    if angle > 45:
        angle -= 90
    return float(angle)


def rotate(image: np.ndarray, angle: float) -> np.ndarray:
    """Rotate about the centre, expanding the canvas so no corner is cut off.

    The new area is filled white, which is the page colour — black padding
    would read as a giant glyph.
    """
    height, width = image.shape[:2]
    centre = (width / 2, height / 2)
    matrix = cv2.getRotationMatrix2D(centre, angle, 1.0)

    radians = np.deg2rad(abs(angle))
    cos, sin = abs(np.cos(radians)), abs(np.sin(radians))
    new_width = int(height * sin + width * cos)
    new_height = int(height * cos + width * sin)
    matrix[0, 2] += new_width / 2 - centre[0]
    matrix[1, 2] += new_height / 2 - centre[1]

    border = 255 if image.ndim == 2 else (255, 255, 255)
    return cv2.warpAffine(
        image,
        matrix,
        (new_width, new_height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=border,
    )


def deskew(image: np.ndarray) -> tuple[np.ndarray, float]:
    """Straighten the page. Returns the image and the angle actually applied."""
    angle = estimate_skew(image)
    if abs(angle) < MIN_DESKEW_DEGREES or abs(angle) > MAX_DESKEW_DEGREES:
        return image, 0.0
    return rotate(image, angle), angle


def find_page_quad(image: np.ndarray) -> np.ndarray | None:
    """The page's four corners, if a convincing outline is present.

    None when the document already fills the frame (a scan or a render), which
    is the common case — there is nothing to correct and a false positive here
    would crop real content away.
    """
    gray = to_grayscale(image)
    height, width = gray.shape[:2]
    image_area = float(height * width)

    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    # Close gaps so a slightly broken border still forms one contour.
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
        area = cv2.contourArea(contour)
        if area < image_area * MIN_PAGE_AREA_RATIO:
            break
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(approx) == 4:
            quad = approx.reshape(4, 2).astype(np.float32)
            # A quad covering nearly the whole frame is the image border, not a
            # page sitting inside a photo; correcting it would be a no-op warp.
            if area > image_area * 0.98:
                return None
            return _order_corners(quad)
    return None


def _order_corners(quad: np.ndarray) -> np.ndarray:
    """Order four points as top-left, top-right, bottom-right, bottom-left."""
    ordered = np.zeros((4, 2), dtype=np.float32)
    total = quad.sum(axis=1)
    ordered[0] = quad[np.argmin(total)]
    ordered[2] = quad[np.argmax(total)]
    diff = np.diff(quad, axis=1).ravel()
    ordered[1] = quad[np.argmin(diff)]
    ordered[3] = quad[np.argmax(diff)]
    return ordered


def correct_perspective(image: np.ndarray) -> tuple[np.ndarray, bool]:
    """Flatten the page onto a rectangle. Returns the image and whether it was
    corrected at all."""
    quad = find_page_quad(image)
    if quad is None:
        return image, False

    top_left, top_right, bottom_right, bottom_left = quad
    width = int(
        max(np.linalg.norm(top_right - top_left), np.linalg.norm(bottom_right - bottom_left))
    )
    height = int(
        max(np.linalg.norm(bottom_left - top_left), np.linalg.norm(bottom_right - top_right))
    )
    if width < 50 or height < 50:
        return image, False

    target = np.array(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype=np.float32
    )
    matrix = cv2.getPerspectiveTransform(quad, target)
    return cv2.warpPerspective(image, matrix, (width, height), flags=cv2.INTER_CUBIC), True


# Pixels at least this light are flattened to white before thresholding. The
# issued certificate carries a diagonal grey watermark at about 224, which Otsu
# keeps and which OCR then reads as words overlapping the real fields
# ("NBIT2024CS0001 rat a"). Genuine text lighter than this is not legible
# anyway, so nothing readable is lost.
LIGHT_CUTOFF = 205


def suppress_light(image: np.ndarray, *, cutoff: int = LIGHT_CUTOFF) -> np.ndarray:
    """Flatten near-white pixels to white, removing faint watermarks."""
    gray = to_grayscale(image)
    out = gray.copy()
    out[out >= cutoff] = 255
    return out


def threshold(image: np.ndarray) -> np.ndarray:
    """Binarise for OCR.

    Otsu over the whole page: our certificates are evenly lit, and adaptive
    thresholding on a clean render tends to carve speckle out of the
    background watermark.
    """
    gray = to_grayscale(image)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    return binary


def upscale_if_small(image: np.ndarray, *, min_width: int = 1200) -> np.ndarray:
    """Tesseract wants roughly 300 DPI; enlarge anything well under it.

    Cubic interpolation, because nearest-neighbour leaves stair-stepped strokes
    that the recogniser reads as broken glyphs.
    """
    height, width = image.shape[:2]
    if width >= min_width:
        return image
    scale = min_width / width
    return cv2.resize(image, (min_width, int(height * scale)), interpolation=cv2.INTER_CUBIC)


def mask_regions(
    image: np.ndarray, regions: list[tuple[int, int, int, int]], *, margin: int = 6
) -> np.ndarray:
    """Paint rectangles white on a copy of the image.

    Used to take the QR code out of the page before OCR. A QR sits in the same
    horizontal band as the certificate's boxed fields, and a page-level
    segmentation reads its modules as glyphs on those baselines — appending
    noise like "rat a" to the value next to it and dragging the line's
    confidence down with it. The payload is decoded separately, so nothing is
    lost by blanking it here.
    """
    if not regions:
        return image

    out = image.copy()
    height, width = out.shape[:2]
    fill = 255 if out.ndim == 2 else (255, 255, 255)
    for left, top, box_width, box_height in regions:
        x0 = max(0, left - margin)
        y0 = max(0, top - margin)
        x1 = min(width, left + box_width + margin)
        y1 = min(height, top + box_height + margin)
        if x1 > x0 and y1 > y0:
            cv2.rectangle(out, (x0, y0), (x1, y1), fill, thickness=-1)
    return out


def decode_image(data: bytes) -> np.ndarray | None:
    """Decode image bytes to BGR, or None if they are not a readable image."""
    buffer = np.frombuffer(data, dtype=np.uint8)
    return cv2.imdecode(buffer, cv2.IMREAD_COLOR)


def prepare(image: np.ndarray, *, binarise: bool = True) -> np.ndarray:
    """The full pipeline, in the order the module docstring describes.

    `binarise=False` stops before thresholding, which is what the QR decoder
    wants: pyzbar reads a grayscale gradient better than a hard-clipped one.
    """
    flattened, _ = correct_perspective(image)
    gray = to_grayscale(flattened)
    cleaned = denoise(gray)
    unwatermarked = suppress_light(cleaned)
    straightened, _ = deskew(unwatermarked)
    enlarged = upscale_if_small(straightened)
    return threshold(enlarged) if binarise else enlarged
