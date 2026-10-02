"""Tiny query language -> SQL.

    ebi              word (prefix) in artist / title / file name / caption / hashtags
    "shab bokhor"    exact phrase (word-prefix)
    #remix           exact hashtag
    artist:ebi       only in artist   (aliases: a:, singer:, خواننده:)
    title:shab       only in title    (aliases: t:, name:, اسم:)
    tag:remix        same as #remix
    -term, -#tag     exclusion
All clauses are ANDed. Everything is passed as bound parameters.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.textutil import norm, norm_tag, pad

_FIELD_ALIASES = {
    "artist": "artist", "a": "artist", "singer": "artist", "خواننده": "artist",
    "title": "title", "t": "title", "name": "title", "اسم": "title",
    "tag": "tag", "hashtag": "tag", "هشتگ": "tag",
}
_TOKEN = re.compile(r'(-?)((?:[^\s":]+:)?)(?:"([^"]*)"|(\S+))')


@dataclass(frozen=True)
class Clause:
    field: str  # all | artist | title | tag
    value: str  # already normalised
    negate: bool = False


def parse_query(text: str) -> list[Clause]:
    clauses: list[Clause] = []
    for neg, key, quoted, word in _TOKEN.findall(text or ""):
        field = _FIELD_ALIASES.get(key[:-1].casefold()) if key else None
        raw = quoted if quoted else word
        if key and field is None:  # "foo:bar" with unknown key is just text
            raw = key + raw
        if field is None:
            field = "all"
            if not quoted and raw.startswith("#"):
                field = "tag"
        if field == "tag":
            value = norm_tag(raw)
        else:
            value = norm(raw)
        if value:
            clauses.append(Clause(field, value, bool(neg)))
    return clauses


def _like_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


_COLUMNS = {"all": "t.n_all", "artist": "t.n_artist", "title": "t.n_title"}


def build_where(clauses: list[Clause]) -> tuple[str, list[str]]:
    """SQL condition over `tracks AS t` plus its parameters."""
    parts: list[str] = []
    params: list[str] = []
    for c in clauses:
        if c.field == "tag":
            cond = "EXISTS (SELECT 1 FROM track_tags g WHERE g.message_id = t.message_id AND g.tag = ?)"
            params.append(c.value)
        else:
            cond = f"{_COLUMNS[c.field]} LIKE ? ESCAPE '\\'"
            params.append(f"%{_like_escape(pad(c.value))}%")
        parts.append(f"NOT ({cond})" if c.negate else cond)
    return (" AND ".join(parts) or "1"), params
