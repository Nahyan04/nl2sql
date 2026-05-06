from __future__ import annotations

import re

from pydantic import ValidationError

from app.models.query_response import SQLQueryResult


_SQL_TAG = re.compile(r"<sql>(.*?)</sql>", re.IGNORECASE | re.DOTALL)
_FENCED = re.compile(r"```(?:sql)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)
# plain-text fallback only fires when SELECT/WITH starts a line, otherwise the
# regex would happily latch onto the word "with" inside arbitrary prose
_PLAIN_SQL = re.compile(
    r"^[ \t]*(?:WITH|SELECT)\b.*", re.IGNORECASE | re.DOTALL | re.MULTILINE
)


def _candidates(raw: str) -> list[str]:
    tagged = [m.strip() for m in _SQL_TAG.findall(raw) if m.strip()]
    if tagged:
        return tagged

    fenced = [m.strip() for m in _FENCED.findall(raw) if m.strip()]
    if fenced:
        return fenced

    plain = _PLAIN_SQL.search(raw)
    if plain:
        return [plain.group(0).strip()]
    return []


def parse_response(raw: str) -> SQLQueryResult | None:
    if not raw or not raw.strip():
        return None

    for candidate in _candidates(raw):
        sql = candidate.rstrip(";").strip()
        if not sql:
            continue
        try:
            return SQLQueryResult(query=sql)
        except ValidationError:
            continue
    return None
