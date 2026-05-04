from __future__ import annotations

from typing import Any


def serialize_schema(tables: list[dict[str, Any]], char_budget: int = 4000) -> str:
    lines: list[str] = []
    used = 0

    for table in tables:
        line = table.get("descriptor") or table.get("name", "")
        separator = "\n" if lines else ""
        cost = len(separator) + len(line)
        if used + cost > char_budget:
            break
        lines.append(line)
        used += cost

    return "\n".join(lines)
