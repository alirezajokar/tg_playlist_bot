"""Text normalisation shared by ingestion and search.

Both the stored data and the user's query go through the same functions, so
`ebi`, `Ebi`, `ي/ی`, `ك/ک`, Persian/Arabic digits, ZWNJ and diacritics all compare equal.
"""
from __future__ import annotations

import re
import unicodedata

_CHAR_MAP = str.maketrans(
    {
        "ي": "ی", "ى": "ی", "ك": "ک", "ة": "ه", "ە": "ه",
        "أ": "ا", "إ": "ا", "ٱ": "ا", "ـ": None,
        **{c: str(i) for i, c in enumerate("۰۱۲۳۴۵۶۷۸۹")},
        **{c: str(i) for i, c in enumerate("٠١٢٣٤٥٦٧٨٩")},
    }
)
_ZWNJ = "‌‍"
_NON_WORD = re.compile(r"[\W_]+")
_HASHTAG = re.compile(r"#([\w‌]+)")


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").casefold()
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")  # accents, harakat
    return text.translate(_CHAR_MAP)


def norm(text: str) -> str:
    """Lower-cased words separated by single spaces (punctuation, `_`, ZWNJ -> space)."""
    text = _fold(text)
    for ch in _ZWNJ:
        text = text.replace(ch, " ")
    return _NON_WORD.sub(" ", text).strip()


def norm_tag(tag: str) -> str:
    """Normalised hashtag without '#'. Underscore is kept; ZWNJ becomes underscore."""
    text = _fold(tag.lstrip("#"))
    for ch in _ZWNJ:
        text = text.replace(ch, "_")
    return text.strip("_")


def pad(normalized: str) -> str:
    """Leading space so `LIKE '% word%'` matches at word starts, including the first word."""
    return " " + normalized


def extract_hashtags(text: str) -> list[str]:
    seen: dict[str, None] = {}
    for match in _HASHTAG.finditer(text or ""):
        tag = norm_tag(match.group(1))
        if tag:
            seen.setdefault(tag)
    return list(seen)
