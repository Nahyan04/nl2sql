from __future__ import annotations

import re
from typing import Any

_WEIGHT_TABLE_NAME = 3.0
_WEIGHT_ALIAS = 2.0
_WEIGHT_COLUMN_NAME = 1.0


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in re.split(r"[^a-zA-Z0-9]+", text) if t}


def _table_name_score(question_tokens: set[str], table_name: str) -> float:
    return _WEIGHT_TABLE_NAME * len(question_tokens & _tokenize(table_name))


def _column_score(question_tokens: set[str], columns: list[dict[str, Any]]) -> float:
    return sum(
        _WEIGHT_COLUMN_NAME
        for col in columns
        if question_tokens & _tokenize(col["name"])
    )


def _alias_score(question: str, table_name: str, aliases: dict[str, list[str]]) -> float:
    question_lower = question.lower()
    return sum(
        _WEIGHT_ALIAS
        for phrase, tables in aliases.items()
        if table_name in tables and phrase in question_lower
    )


def score_tables(
    question: str,
    schema: dict[str, Any],
    aliases: dict[str, list[str]] | None = None,
) -> list[tuple[str, float]]:
    question_tokens = _tokenize(question)
    aliases = aliases or {}

    scores = [
        (
            table["name"],
            _table_name_score(question_tokens, table["name"])
            + _column_score(question_tokens, table["columns"])
            + _alias_score(question, table["name"], aliases),
        )
        for table in schema["tables"]
    ]

    return sorted(scores, key=lambda x: x[1], reverse=True)


def expand_with_fk_neighbors(
    selected_tables: list[str],
    schema: dict[str, Any],
) -> list[str]:
    table_map = {t["name"]: t for t in schema["tables"]}
    selected_set = set(selected_tables)
    neighbors: set[str] = set()

    for table_name in selected_tables:
        table = table_map.get(table_name)
        if not table:
            continue
        for fk in table.get("foreign_keys", []):
            referred = fk.get("referred_table")
            if referred:
                neighbors.add(referred)

    for table in schema["tables"]:
        if table["name"] in selected_set:
            continue
        for fk in table.get("foreign_keys", []):
            if fk.get("referred_table") in selected_set:
                neighbors.add(table["name"])
                break

    result = list(selected_tables)
    for name in neighbors - selected_set:
        result.append(name)
    return result


def build_table_descriptor(table: dict[str, Any]) -> str:
    col_names = ", ".join(c["name"] for c in table["columns"])
    descriptor = f"{table['name']}({col_names})"

    fk_parts = [
        f"{', '.join(fk['columns'])} → {fk['referred_table']}({', '.join(fk['referred_columns'])})"
        for fk in table.get("foreign_keys", [])
    ]
    if fk_parts:
        descriptor += " | FK: " + ", ".join(fk_parts)

    return descriptor


def retrieve(
    question: str,
    schema: dict[str, Any],
    aliases: dict[str, list[str]] | None = None,
    top_n: int = 5,
) -> list[dict[str, Any]]:
    scores = score_tables(question, schema, aliases)
    top_names = [name for name, _ in scores[:top_n]]
    expanded_names = expand_with_fk_neighbors(top_names, schema)

    table_map = {t["name"]: t for t in schema["tables"]}
    return [
        {**table_map[name], "descriptor": build_table_descriptor(table_map[name])}
        for name in expanded_names
        if name in table_map
    ]
