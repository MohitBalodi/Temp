"""Field normalization. Pure functions, no I/O.

Used both when storing/signing registry records and (later) when comparing
OCR-extracted fields, so equivalent inputs always produce identical values.

OCR confusions (O↔0, I/l↔1, S↔5, B↔8) are handled by `collapse_confusables`,
which is for *comparing* IDs, not for storing them. It is applied to both
sides of a comparison, never used to rewrite a value: the pairs are ambiguous
in both directions, so rewriting one side would corrupt a correct reading
("NBIT" would become "N81T") while collapsing both makes the two agree.
"""

import re
import unicodedata
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

_WHITESPACE = re.compile(r"\s+")
_NON_ALNUM = re.compile(r"[^0-9A-Z]")
_TWO_PLACES = Decimal("0.01")


def clean_text(value: str) -> str:
    """Trim and collapse internal whitespace; keep case. Used for display/storage."""
    return _WHITESPACE.sub(" ", unicodedata.normalize("NFC", value)).strip()


def normalize_text(value: str) -> str:
    """Trim, collapse spaces, uppercase. Used for names and programmes."""
    return clean_text(value).upper()


def normalize_id(value: str) -> str:
    """Uppercase and strip everything except A–Z/0–9. For cert/roll numbers and codes."""
    return _NON_ALNUM.sub("", normalize_text(value))


# Characters OCR confuses in identifiers, each mapped to one representative.
# Applied to both sides of a comparison — see the module docstring.
_CONFUSABLES = str.maketrans({"O": "0", "Q": "0", "D": "0", "I": "1", "L": "1", "S": "5", "B": "8"})


def collapse_confusables(value: str) -> str:
    """Collapse OCR-confusable characters in an identifier to one form.

    For comparison only. `collapse_confusables("NBIT2024CS0001")` and
    `collapse_confusables("N81T2024C50001")` are equal, so a recogniser that
    read B as 8 and S as 5 still matches the registry — without either stored
    value being altered.
    """
    return normalize_id(value).translate(_CONFUSABLES)


def ids_match(left: str, right: str) -> bool:
    """Whether two identifiers are the same, tolerating OCR confusables."""
    return collapse_confusables(left) == collapse_confusables(right)


def normalize_decimal(value: Decimal | float | int | str | None) -> Decimal | None:
    """Round to two decimals (half-up). `None` / empty string stay `None`."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        # str() first so floats like 8.1 don't carry binary noise into Decimal.
        return Decimal(str(value).strip()).quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise ValueError(f"not a number: {value!r}") from exc


def format_decimal(value: Decimal | float | int | str | None) -> str | None:
    """Canonical string form of a grade: always two decimals, e.g. '8.50'."""
    d = normalize_decimal(value)
    return None if d is None else f"{d:.2f}"


def normalize_year(value: int | str) -> int:
    return int(str(value).strip())


def format_date(value: date) -> str:
    return value.isoformat()
