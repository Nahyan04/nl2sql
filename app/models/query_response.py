from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator


# read-only check skips leading whitespace, line comments, and block comments
_READ_ONLY_PREFIX = re.compile(
    r"\A(?:\s+|--[^\n]*\n|/\*.*?\*/)*(select|with)\b",
    re.IGNORECASE | re.DOTALL,
)


class SQLQueryResult(BaseModel):
    query: str
    tables_used: list[str] = Field(default_factory=list)
    explanation: str = ""
    is_valid: bool = True
    explain_plan: list[str] | None = None

    @field_validator("query")
    @classmethod
    def must_be_read_only(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("query must not be empty")
        if not _READ_ONLY_PREFIX.match(stripped):
            raise ValueError("only SELECT or WITH queries are allowed")
        return stripped


class QueryRequest(BaseModel):
    question: str = Field(min_length=1)
    top_n_tables: int = Field(default=8, ge=1, le=50)
    dry_run: bool = False


class ErrorResponse(BaseModel):
    error: str
    detail: str = ""
    retry_count: int = 0
