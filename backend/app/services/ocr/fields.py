"""Label-anchored field extraction, driven by the YAML templates.

Pure except for reading the template files once: given lines, it returns
fields. That keeps it testable without OCR, a database or a document.

Two deliberate properties:

* An unknown layout yields no fields. `MANUAL_REVIEW` is the honest outcome
  for a document we cannot read, and inventing partial fields from a layout we
  do not recognise would turn "unreadable" into "mismatch".
* Values are never rewritten to "fix" OCR confusions. The O/0, I/1, S/5, B/8
  pairs are ambiguous in both directions, so rewriting would corrupt correct
  readings; `normalize.collapse_confusables` instead collapses *both* sides at
  comparison time. What this module reports is what the document said.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.services.normalize import (
    clean_text,
    normalize_decimal,
    normalize_id,
    normalize_text,
)
from app.services.ocr.engines import OcrLine

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent / "templates"


class Normalizer(StrEnum):
    ID = "id"
    TEXT = "text"
    YEAR = "year"
    DECIMAL = "decimal"
    DATE = "date"


@dataclass(frozen=True, slots=True)
class FieldRule:
    """How to find one field. Exactly one of `anchor` or `pattern` is set."""

    name: str
    normalize: Normalizer
    anchor: str | None = None
    value_position: str = "next_line"
    pattern: re.Pattern[str] | None = None


@dataclass(frozen=True, slots=True)
class Template:
    name: str
    description: str
    require_all: tuple[str, ...]
    require_any: tuple[str, ...]
    rules: tuple[FieldRule, ...]

    def matches(self, text: str) -> bool:
        haystack = text.casefold()
        if not all(token.casefold() in haystack for token in self.require_all):
            return False
        # No `any` markers configured means "nothing further to require".
        return not self.require_any or any(
            token.casefold() in haystack for token in self.require_any
        )


@dataclass(frozen=True, slots=True)
class ExtractedField:
    """One field read off a document.

    `raw` is what the document said; `value` is that normalized for comparison.
    `confidence` is the confidence of the line(s) the value came from, so a
    field read off a blurred line is uncertain even when the page as a whole
    was legible.
    """

    name: str
    value: str | None
    raw: str
    confidence: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "raw": self.raw,
            "confidence": round(self.confidence, 4),
        }


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    template: str | None
    fields: dict[str, ExtractedField]

    @property
    def matched(self) -> bool:
        return self.template is not None

    def value(self, name: str) -> str | None:
        found = self.fields.get(name)
        return found.value if found else None

    def as_dict(self) -> dict[str, Any]:
        return {
            "template": self.template,
            "fields": {name: f.as_dict() for name, f in self.fields.items()},
        }


# --- template loading ---------------------------------------------------------


def _rule_from_yaml(name: str, spec: dict[str, Any]) -> FieldRule:
    normalize = Normalizer(spec.get("normalize", "text"))
    if "pattern" in spec:
        return FieldRule(name=name, normalize=normalize, pattern=re.compile(spec["pattern"]))
    if "anchor" not in spec:
        raise ValueError(f"field {name!r} needs either 'anchor' or 'pattern'")
    return FieldRule(
        name=name,
        normalize=normalize,
        anchor=spec["anchor"],
        value_position=spec.get("value", "next_line"),
    )


def _template_from_yaml(data: dict[str, Any]) -> Template:
    match = data.get("match") or {}
    fields = data.get("fields") or {}
    return Template(
        name=data["name"],
        description=(data.get("description") or "").strip(),
        require_all=tuple(match.get("all") or ()),
        require_any=tuple(match.get("any") or ()),
        rules=tuple(_rule_from_yaml(name, spec) for name, spec in fields.items()),
    )


@lru_cache
def load_templates(directory: str | None = None) -> tuple[Template, ...]:
    """Every template in the directory, loaded once per process."""
    root = Path(directory) if directory else TEMPLATE_DIR
    templates: list[Template] = []
    for path in sorted(root.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            templates.append(_template_from_yaml(data))
        except Exception:
            logger.exception("skipping unreadable OCR template %s", path)
    return tuple(templates)


def match_template(text: str, templates: tuple[Template, ...] | None = None) -> Template | None:
    """The first template whose markers are all present, or None."""
    for template in templates or load_templates():
        if template.matches(text):
            return template
    return None


# --- value normalization ------------------------------------------------------


def _normalize_year(raw: str) -> str | None:
    digits = re.sub(r"[^0-9]", "", raw)
    if len(digits) != 4:
        return None
    return digits


def _normalize_date(raw: str) -> str | None:
    """ISO date, if the text contains one. Our own layout prints YYYY-MM-DD."""
    cleaned = clean_text(raw)
    match = re.search(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", cleaned)
    if match:
        year, month, day = (int(g) for g in match.groups())
    else:
        match = re.search(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})", cleaned)
        if not match:
            return None
        day, month, year = (int(g) for g in match.groups())
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _normalize_decimal(raw: str) -> str | None:
    cleaned = clean_text(raw).replace(",", ".")
    match = re.search(r"\d+(?:\.\d+)?", cleaned)
    if not match:
        return None
    try:
        value = normalize_decimal(Decimal(match.group(0)))
    except (ValueError, ArithmeticError):
        return None
    return None if value is None else f"{value:.2f}"


def normalize_value(raw: str, how: Normalizer) -> str | None:
    """Normalize a raw field value for comparison, or None if unusable."""
    text = clean_text(raw)
    if not text:
        return None

    match how:
        case Normalizer.ID:
            # First whitespace token only. OCR of our own certificates picks up
            # the diagonal watermark as trailing words on the same line
            # ("NBIT2024CS0001 rat a"), and an identifier never contains a space.
            value = normalize_id(text.split()[0]) if text.split() else ""
            return value or None
        case Normalizer.TEXT:
            # Uppercased, like the registry side (`normalize_text`): the
            # comparison is case-insensitive, and both sides must land in the
            # same form or every name and programme would conflict. The
            # document's own casing is preserved on `ExtractedField.raw`, which
            # is what the result page displays.
            return normalize_text(text) or None
        case Normalizer.YEAR:
            return _normalize_year(text)
        case Normalizer.DECIMAL:
            return _normalize_decimal(text)
        case Normalizer.DATE:
            return _normalize_date(text)
    return None


# --- extraction ---------------------------------------------------------------


def _find_anchor(lines: list[OcrLine], anchor: str) -> int | None:
    """Index of the first line containing the anchor, case-insensitively."""
    needle = anchor.casefold()
    for index, line in enumerate(lines):
        if needle in line.text.casefold():
            return index
    return None


def _apply_anchor_rule(lines: list[OcrLine], rule: FieldRule) -> tuple[str, float] | None:
    assert rule.anchor is not None
    index = _find_anchor(lines, rule.anchor)
    if index is None:
        return None

    if rule.value_position == "same_line":
        line = lines[index]
        # Everything after the anchor text on that line.
        position = line.text.casefold().find(rule.anchor.casefold())
        raw = line.text[position + len(rule.anchor) :].strip(" :•-\t")
        return (raw, line.confidence) if raw else None

    # next_line: the following non-empty line is the value.
    for line in lines[index + 1 :]:
        if line.text.strip():
            return line.text, line.confidence
    return None


def _apply_pattern_rule(lines: list[OcrLine], rule: FieldRule) -> tuple[str, float] | None:
    assert rule.pattern is not None
    for line in lines:
        match = rule.pattern.search(line.text)
        if match:
            captured = match.group(1) if match.groups() else match.group(0)
            return captured, line.confidence
    return None


def extract_fields(
    lines: list[OcrLine], *, templates: tuple[Template, ...] | None = None
) -> ExtractionResult:
    """Read the critical fields off a document's lines.

    An unrecognised layout returns `ExtractionResult(template=None, fields={})`
    rather than a best guess.
    """
    text = "\n".join(line.text for line in lines)
    template = match_template(text, templates)
    if template is None:
        logger.info("no OCR template matched a document of %d lines", len(lines))
        return ExtractionResult(template=None, fields={})

    fields: dict[str, ExtractedField] = {}
    for rule in template.rules:
        found = (
            _apply_anchor_rule(lines, rule)
            if rule.anchor is not None
            else _apply_pattern_rule(lines, rule)
        )
        if found is None:
            continue
        raw, confidence = found
        value = normalize_value(raw, rule.normalize)
        if value is None:
            continue
        fields[rule.name] = ExtractedField(
            name=rule.name, value=value, raw=clean_text(raw), confidence=confidence
        )

    return ExtractionResult(template=template.name, fields=fields)
