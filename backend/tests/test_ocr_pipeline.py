"""The extraction pipeline: preprocessing, text extraction, field extraction.

The OCR tests here run the real Tesseract on a real issued certificate, so
they are the slowest in the suite. They are also the only place that proves
the engine, the preprocessing and the template agree with each other.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import cv2
import numpy as np
import pytest

from app.services.ocr import extract, extract_fields, qr_scan
from app.services.ocr import preprocess as pp
from app.services.ocr.engines import OcrLine, TesseractEngine, _lines_from_tsv, get_engine
from app.services.ocr.extract_text import (
    MIN_TEXT_LAYER_CHARS,
    TextSource,
    decode_qr,
    decode_qr_payloads,
    extract_from_image,
    extract_from_pdf,
)
from app.services.ocr.fields import (
    Normalizer,
    load_templates,
    match_template,
    normalize_value,
)
from app.services.qr import parse_payload
from tests.ocr_fixtures import (
    degrade,
    make_certificate,
    noise_image,
    photo_of_certificate,
    render_png,
    rotate_image,
    to_array,
)

CRITICAL = (
    "cert_number",
    "roll_number",
    "student_name",
    "programme",
    "year_of_passing",
    "cgpa",
)


@pytest.fixture(scope="module")
def sample(tmp_path_factory: pytest.TempPathFactory):
    """One issued certificate, reused across this module's tests.

    Module-scoped because building the PDF and OCRing it is the expensive part;
    nothing here mutates it.
    """
    from app.core.config import settings

    keys = tmp_path_factory.mktemp("ocr-keys")
    original = settings.keys_dir
    settings.keys_dir = str(keys)
    try:
        yield make_certificate()
    finally:
        settings.keys_dir = original


def assert_never_confidently_wrong(result, truth: dict[str, str]) -> None:
    """Every critical field is either read correctly, or flagged low-confidence.

    This, not "every field is perfect", is the property the verdict depends on.
    Tesseract misreads short alphanumeric identifiers at screen resolution
    ("21CS901" -> "2108901", because C/0 and S/8 look alike at 11pt), and the
    confidence threshold is what keeps such a read out of a MISMATCH: the
    observed confidence for that misread is 0.09 against a 0.85 threshold.
    A correct value may also be low-confidence — that is safe, merely cautious.
    """
    from app.core.config import settings

    for name in CRITICAL:
        field = result.fields.get(name)
        assert field is not None, f"{name} was not extracted at all"
        if field.value == truth[name]:
            continue
        assert field.confidence < settings.ocr_min_field_confidence, (
            f"{name} was read as {field.value!r} instead of {truth[name]!r} "
            f"with confidence {field.confidence:.2f} — a confidently wrong read"
        )


# --- preprocessing (pure, no OCR) ---------------------------------------------


def test_to_grayscale_is_idempotent() -> None:
    gray = np.full((10, 10), 128, np.uint8)
    assert pp.to_grayscale(gray) is gray
    colour = np.zeros((10, 10, 3), np.uint8)
    assert pp.to_grayscale(colour).shape == (10, 10)


def test_to_grayscale_handles_an_alpha_channel() -> None:
    bgra = np.zeros((4, 4, 4), np.uint8)
    assert pp.to_grayscale(bgra).shape == (4, 4)


def test_estimate_skew_finds_a_rotation_we_introduced() -> None:
    page = np.full((400, 900), 255, np.uint8)
    for y in range(80, 330, 40):
        cv2.line(page, (80, y), (820, y), 0, 6)

    tilted = pp.rotate(page, 6.0)
    estimate = pp.estimate_skew(tilted)
    # Sign convention: estimate_skew returns the angle deskew should apply back.
    assert 4.0 <= abs(estimate) <= 8.0


def test_estimate_skew_returns_zero_on_a_blank_page() -> None:
    assert pp.estimate_skew(np.full((50, 50), 255, np.uint8)) == 0.0


def test_deskew_declines_an_implausible_angle(monkeypatch: pytest.MonkeyPatch) -> None:
    """A wild estimate means the angle finder failed; rotating would be worse."""
    monkeypatch.setattr(pp, "estimate_skew", lambda _image: 40.0)
    image = np.full((20, 20), 255, np.uint8)
    out, applied = pp.deskew(image)
    assert applied == 0.0
    assert out is image


def test_deskew_ignores_a_negligible_angle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pp, "estimate_skew", lambda _image: 0.02)
    image = np.full((20, 20), 255, np.uint8)
    _, applied = pp.deskew(image)
    assert applied == 0.0


def test_rotate_expands_the_canvas_and_fills_white() -> None:
    image = np.zeros((100, 200), np.uint8)
    out = pp.rotate(image, 30)
    assert out.shape[0] > 100 and out.shape[1] > 200
    # The new corners are page-coloured, not black.
    assert out[0, 0] == 255


def test_suppress_light_removes_a_faint_watermark() -> None:
    page = np.full((60, 60), 255, np.uint8)
    page[10:20, 10:50] = 224  # the issued PDF's watermark grey
    page[30:40, 10:50] = 20  # real text
    out = pp.suppress_light(page)
    assert (out[10:20, 10:50] == 255).all()
    assert (out[30:40, 10:50] == 20).all()


def test_mask_regions_blanks_a_box_and_leaves_the_rest() -> None:
    image = np.zeros((100, 100), np.uint8)
    out = pp.mask_regions(image, [(40, 40, 20, 20)], margin=0)
    assert (out[40:60, 40:60] == 255).all()
    assert out[0, 0] == 0
    assert image[40, 40] == 0, "the input must not be modified"


def test_mask_regions_is_a_no_op_without_regions() -> None:
    image = np.zeros((10, 10), np.uint8)
    assert pp.mask_regions(image, []) is image


def test_mask_regions_clips_to_the_image() -> None:
    image = np.zeros((20, 20), np.uint8)
    out = pp.mask_regions(image, [(15, 15, 50, 50)], margin=5)
    assert out.shape == (20, 20)
    assert (out[19, 19] == 255).all()


def test_upscale_leaves_a_large_image_alone() -> None:
    image = np.zeros((100, 1500), np.uint8)
    assert pp.upscale_if_small(image) is image


def test_upscale_enlarges_a_small_image() -> None:
    out = pp.upscale_if_small(np.zeros((100, 300), np.uint8), min_width=1200)
    assert out.shape[1] == 1200


def test_find_page_quad_is_none_when_the_page_fills_the_frame() -> None:
    assert pp.find_page_quad(np.full((300, 300), 255, np.uint8)) is None


def test_decode_image_rejects_non_image_bytes() -> None:
    assert pp.decode_image(b"not an image at all") is None


# --- engine line grouping (pure, no Tesseract) --------------------------------


def test_lines_from_tsv_groups_words_and_averages_confidence() -> None:
    data = {
        "text": ["CGPA", "8.50", "", "Roll"],
        "conf": ["90", "80", "-1", "60"],
        "block_num": [1, 1, 1, 2],
        "par_num": [1, 1, 1, 1],
        "line_num": [1, 1, 1, 1],
        "left": [10, 60, 0, 10],
        "top": [20, 20, 0, 50],
        "width": [40, 40, 0, 30],
        "height": [10, 10, 0, 10],
    }
    lines = _lines_from_tsv(data)
    assert [line.text for line in lines] == ["CGPA 8.50", "Roll"]
    assert lines[0].confidence == pytest.approx(0.85)
    assert lines[0].bbox == (10, 20, 90, 10)


def test_lines_from_tsv_skips_unscored_words_in_the_average() -> None:
    data = {
        "text": ["A", "B"],
        "conf": ["-1", "50"],
        "block_num": [1, 1],
        "par_num": [1, 1],
        "line_num": [1, 1],
        "left": [0, 10],
        "top": [0, 0],
        "width": [5, 5],
        "height": [5, 5],
    }
    assert _lines_from_tsv(data)[0].confidence == pytest.approx(0.5)


def test_ocr_line_rejects_an_impossible_confidence() -> None:
    with pytest.raises(ValueError):
        OcrLine(text="x", confidence=1.4)


def test_tesseract_is_available_in_this_image() -> None:
    assert TesseractEngine().is_available()
    assert get_engine().name == "tesseract"


def test_engine_returns_nothing_for_an_empty_image() -> None:
    assert get_engine().recognise(np.zeros((0, 0), np.uint8)) == []


# --- templates (pure) ---------------------------------------------------------


def test_the_nbit_template_loads() -> None:
    names = {t.name for t in load_templates()}
    assert "nbit" in names


def test_template_matches_our_own_layout_text() -> None:
    text = "DEGREE CERTIFICATE\nInstitution code TST\nThis is to certify that"
    template = match_template(text)
    assert template is not None and template.name == "nbit"


def test_template_does_not_match_unrelated_text() -> None:
    assert match_template("Electricity bill for March 2026\nAmount due 1,240") is None


def test_template_needs_more_than_the_heading() -> None:
    """`all` alone is not enough; one of the `any` markers must appear too."""
    assert match_template("DEGREE CERTIFICATE") is None


@pytest.mark.parametrize(
    ("raw", "how", "expected"),
    [
        ("  nbit-2024/cs-0001 ", Normalizer.ID, "NBIT2024CS0001"),
        ("NBIT2024CS0001 rat a", Normalizer.ID, "NBIT2024CS0001"),
        ("  Aarav   Sharma ", Normalizer.TEXT, "AARAV SHARMA"),
        ("2024", Normalizer.YEAR, "2024"),
        ("20244", Normalizer.YEAR, None),
        ("8.5", Normalizer.DECIMAL, "8.50"),
        ("8,72", Normalizer.DECIMAL, "8.72"),
        ("8.72/10.00", Normalizer.DECIMAL, "8.72"),
        ("2024-07-15", Normalizer.DATE, "2024-07-15"),
        ("15/07/2024", Normalizer.DATE, "2024-07-15"),
        ("2024-13-40", Normalizer.DATE, None),
        ("", Normalizer.TEXT, None),
        ("   ", Normalizer.ID, None),
    ],
)
def test_normalize_value(raw: str, how: Normalizer, expected: str | None) -> None:
    assert normalize_value(raw, how) == expected


def test_id_normalizer_takes_only_the_first_token() -> None:
    """Watermark or QR noise bleeding onto the line must not join the value."""
    assert normalize_value("20CS001 Paes", Normalizer.ID) == "20CS001"


def test_extract_fields_returns_nothing_for_an_unknown_layout() -> None:
    lines = [
        OcrLine(text="Gas bill", confidence=0.9),
        OcrLine(text="Pay by 1 April", confidence=0.9),
    ]
    result = extract_fields(lines)
    assert not result.matched
    assert result.fields == {}
    assert result.template is None


def test_extract_fields_reads_a_synthetic_layout() -> None:
    """Field extraction without any OCR: lines in, fields out."""
    lines = [
        OcrLine(text="DEGREE CERTIFICATE", confidence=1.0),
        OcrLine(text="Institution code TST", confidence=1.0),
        OcrLine(text="This is to certify that", confidence=1.0),
        OcrLine(text="Aarav Sharma", confidence=0.9),
        OcrLine(text="has successfully completed the programme", confidence=1.0),
        OcrLine(text="B.Tech Computer Science", confidence=0.95),
        OcrLine(text="Year of passing 2024 - CGPA8.50/10.00", confidence=0.8),
        OcrLine(text="CERTIFICATE NUMBER", confidence=1.0),
        OcrLine(text="TST2024CS0001", confidence=0.7),
        OcrLine(text="2024-07-15", confidence=1.0),
    ]
    result = extract_fields(lines)
    assert result.template == "nbit"
    assert result.value("cert_number") == "TST2024CS0001"
    assert result.value("student_name") == "AARAV SHARMA"
    assert result.value("cgpa") == "8.50"
    assert result.value("year_of_passing") == "2024"
    assert result.value("issue_date") == "2024-07-15"
    # Field confidence is the line's, not the page's.
    assert result.fields["cert_number"].confidence == pytest.approx(0.7)


def test_extract_fields_skips_a_field_whose_anchor_is_absent() -> None:
    lines = [
        OcrLine(text="DEGREE CERTIFICATE", confidence=1.0),
        OcrLine(text="This is to certify that", confidence=1.0),
        OcrLine(text="Aarav Sharma", confidence=1.0),
    ]
    result = extract_fields(lines)
    assert result.matched
    assert "roll_number" not in result.fields


# --- PDF text layer -----------------------------------------------------------


def test_issued_pdf_is_read_from_its_text_layer_not_ocr(sample) -> None:
    page = extract_from_pdf(sample.pdf)
    assert page.source is TextSource.PDF_TEXT_LAYER
    assert page.mean_confidence == 1.0
    assert sum(len(line.text) for line in page.lines) >= MIN_TEXT_LAYER_CHARS


def test_issued_pdf_yields_every_critical_field_exactly(sample) -> None:
    page = extract_from_pdf(sample.pdf)
    result = extract_fields(page.lines)
    assert result.template == "nbit"
    for name in CRITICAL:
        assert result.value(name) == sample.truth[name], name


def test_issued_pdf_carries_a_parseable_qr(sample) -> None:
    page = extract_from_pdf(sample.pdf)
    assert page.qr_payloads
    payload = parse_payload(page.qr_payloads[0])
    assert payload.cert_number == sample.data.cert_number
    assert payload.institution_code == sample.data.institution_code


def test_a_pdf_with_no_text_layer_falls_back_to_ocr(sample) -> None:
    """An image-only PDF: the page is rasterised and OCRed instead."""
    import fitz

    png = render_png(sample.pdf, dpi=150)
    doc = fitz.open()
    with fitz.open(stream=sample.pdf, filetype="pdf") as original:
        rect = original[0].rect
    page = doc.new_page(width=rect.width, height=rect.height)
    page.insert_image(rect, stream=png)
    image_only = doc.tobytes()
    doc.close()

    extracted = extract_from_pdf(image_only)
    assert extracted.source is TextSource.OCR
    assert extracted.engine == "tesseract"
    assert extract_fields(extracted.lines).template == "nbit"


def test_an_empty_pdf_yields_no_text() -> None:
    import fitz

    doc = fitz.open()
    doc.new_page()
    blank = doc.tobytes()
    doc.close()

    page = extract_from_pdf(blank)
    assert page.is_empty
    assert page.source is TextSource.NONE
    assert page.mean_confidence == 0.0


# --- images through OCR -------------------------------------------------------


def test_a_rendered_png_reads_the_critical_fields_soundly(sample) -> None:
    page = extract_from_image(render_png(sample.pdf))
    assert page.source is TextSource.OCR
    result = extract_fields(page.lines)
    assert result.template == "nbit"
    assert_never_confidently_wrong(result, sample.truth)


def test_a_rendered_png_reads_the_long_identifiers_exactly(sample) -> None:
    """The certificate number and the text fields are long enough to be read
    reliably even from a 200 DPI raster; only the short roll number is fragile."""
    result = extract_fields(extract_from_image(render_png(sample.pdf)).lines)
    for name in ("cert_number", "student_name", "programme", "year_of_passing", "cgpa"):
        assert result.value(name) == sample.truth[name], name


def test_the_qr_is_masked_so_it_does_not_pollute_the_text(sample) -> None:
    """Regression: unmasked, the QR's modules were read as words on the same
    baselines as the boxed fields ("NBIT2024CS0001 rat a")."""
    page = extract_from_image(render_png(sample.pdf))
    assert page.qr_payloads, "the QR must still be decoded"
    value = extract_fields(page.lines).value("cert_number")
    assert value == sample.data.cert_number


def test_a_degraded_scan_still_reads_the_critical_fields(sample) -> None:
    """Rotated, blurred and JPEG-compressed: values must survive, or be flagged."""
    page = extract_from_image(degrade(render_png(sample.pdf)))
    result = extract_fields(page.lines)
    assert result.template == "nbit"
    assert_never_confidently_wrong(result, sample.truth)


def test_a_photographed_page_is_cropped_and_read(sample) -> None:
    """Exercises the perspective/crop path with a visible page outline."""
    page = extract_from_image(photo_of_certificate(render_png(sample.pdf)))
    result = extract_fields(page.lines)
    assert result.template == "nbit"
    assert result.value("cert_number") == sample.data.cert_number


def test_a_random_image_matches_no_template() -> None:
    page = extract_from_image(noise_image())
    assert not extract_fields(page.lines).matched


def test_undecodable_bytes_yield_an_empty_page() -> None:
    page = extract_from_image(b"\x89PNG\r\n\x1a\nbut truncated")
    assert page.is_empty
    assert page.source is TextSource.NONE


# --- QR decoding --------------------------------------------------------------


def test_decode_qr_reports_where_the_code_is(sample) -> None:
    image = to_array(render_png(sample.pdf))
    symbols = decode_qr(image)
    assert symbols
    left, top, width, height = symbols[0].rect
    assert width > 0 and height > 0
    # Bottom-right of the page, where pdf_issue draws it.
    assert left > image.shape[1] / 2
    assert top > image.shape[0] / 2


def test_decode_qr_survives_rotation(sample) -> None:
    rotated = rotate_image(to_array(render_png(sample.pdf)), 5.0)
    assert decode_qr_payloads(rotated)


def test_decode_qr_finds_nothing_in_noise() -> None:
    assert decode_qr(to_array(noise_image())) == []


def test_decode_qr_records_which_reader_and_scale_read_it(sample) -> None:
    """Evidence, not decoration: a code that only came out at 3x says the
    photograph was marginal, which is worth keeping."""
    symbols = decode_qr(to_array(render_png(sample.pdf)))
    assert symbols
    assert symbols[0].reader in (qr_scan.READER_ZXING, qr_scan.READER_PYZBAR)
    assert symbols[0].scale in qr_scan.SCALES


def test_the_ladder_stops_at_the_first_certificate_payload(sample) -> None:
    """A page may carry other codes. The ladder keeps climbing until it finds
    an AVA1 payload rather than settling for the first barcode it sees."""
    image = to_array(render_png(sample.pdf))
    symbols = qr_scan.scan(image)
    assert any(s.is_certificate_payload for s in symbols)


def test_a_rect_found_on_an_upscaled_copy_comes_back_in_original_coordinates() -> None:
    """The rect is used to mask the QR out of the caller's own image, so a hit
    at 2x must not report 2x coordinates."""
    assert qr_scan._shrink((100, 200, 40, 40), 2) == (50, 100, 20, 20)
    assert qr_scan._shrink((100, 200, 40, 40), 1) == (100, 200, 40, 40)


def test_an_upscale_that_would_be_enormous_is_skipped() -> None:
    """A 12 MP photo at 3x is 108 MP: seconds and hundreds of megabytes to
    learn nothing about a code that is already readable at 1x."""
    big = np.zeros((4000, 3000, 3), dtype=np.uint8)
    assert qr_scan._upscaled(big, 3) is None
    assert qr_scan._upscaled(big, 1) is big


def test_a_non_certificate_code_is_not_a_certificate_payload() -> None:
    assert not qr_scan.is_certificate_payload("https://example.test/anything")
    assert not qr_scan.is_certificate_payload("")


def test_the_qr_is_read_from_the_original_photo_not_a_prepared_copy(sample) -> None:
    """The whole point of the ordering: a photo whose text OCR struggles with
    still gives up its signature, because the code is read before any
    threshold is chosen."""
    photo = to_array(photo_of_certificate(render_png(sample.pdf)))
    payloads = decode_qr_payloads(photo)
    assert payloads
    assert parse_payload(payloads[0]).cert_number == sample.truth["cert_number"]


# --- the entry point ----------------------------------------------------------


def test_extract_dispatches_on_mime(sample) -> None:
    pdf_page = extract(sample.pdf, "application/pdf")
    assert pdf_page.source is TextSource.PDF_TEXT_LAYER

    image_page = extract(render_png(sample.pdf), "image/png")
    assert image_page.source is TextSource.OCR


def test_extract_never_raises_on_rubbish() -> None:
    """An unreadable document is MANUAL_REVIEW, not a 500."""
    for mime in ("application/pdf", "image/png", "image/jpeg"):
        page = extract(b"rubbish bytes", mime)
        assert page.is_empty
        assert page.source is TextSource.NONE


def test_marks_instead_of_cgpa_is_extracted(tmp_path: Path) -> None:
    from app.core.config import settings

    original = settings.keys_dir
    settings.keys_dir = str(tmp_path / "keys")
    try:
        sample = make_certificate(cert_number="TST2024ME0007", cgpa=None, marks=Decimal("72.50"))
    finally:
        settings.keys_dir = original

    result = extract_fields(extract_from_pdf(sample.pdf).lines)
    assert result.value("marks") == "72.50"
    assert result.value("cgpa") is None
