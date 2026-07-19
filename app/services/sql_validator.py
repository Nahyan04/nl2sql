from __future__ import annotations

from dataclasses import dataclass

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

# GRANT and other syntax the default dialect can't fully parse fall back to a
# generic Command node, so it's blocked rather than allowed through by default.
# Into covers `SELECT ... INTO new_table` — it parses as a plain Select node
# but actually creates a table, so it must be rejected explicitly.
_UNSAFE_NODE_TYPES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Create,
    exp.Alter,
    exp.TruncateTable,
    exp.Command,
    exp.Into,
)


@dataclass
class SQLValidationResult:
    is_safe: bool
    reason: str = ""


def validate_read_only(sql: str) -> SQLValidationResult:
    try:
        # parse() rather than parse_one() so a stacked "SELECT 1; DROP TABLE x;"
        # can't slip through by hiding a second statement after the first
        statements = [statement for statement in sqlglot.parse(sql) if statement is not None]
    except ParseError as exc:
        return SQLValidationResult(is_safe=False, reason=f"could not parse SQL: {exc}")

    if len(statements) != 1:
        return SQLValidationResult(is_safe=False, reason="only a single statement is allowed")

    statement = statements[0]
    # exp.Query covers Select plus set operations (UNION/INTERSECT/EXCEPT),
    # which are legitimate read-only shapes but parse to their own root types
    if not isinstance(statement, exp.Query):
        return SQLValidationResult(is_safe=False, reason="only SELECT or WITH queries are allowed")

    unsafe_node = statement.find(*_UNSAFE_NODE_TYPES)
    if unsafe_node is not None:
        return SQLValidationResult(
            is_safe=False,
            reason=f"query contains a mutating statement: {type(unsafe_node).__name__}",
        )

    return SQLValidationResult(is_safe=True)
