from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy.engine import Connection, Engine

from app.core.prompt_builder import build_system_prompt, build_user_prompt
from app.core.providers.base import EmbeddingProvider, TextGenerationProvider
from app.models.query_response import ErrorResponse, SQLQueryResult
from app.services.response_parser import parse_response
from app.services.retrieval.lexical import retrieve
from app.services.retrieval.reranker import rerank
from app.services.schema_introspector import introspect_schema
from app.services.schema_serializer import serialize_schema

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RAW_LOG_LIMIT = 500

PARSE_ERROR = "PARSE_ERROR"
VALIDATION_ERROR = "VALIDATION_ERROR"
TIMEOUT = "TIMEOUT"
EMPTY_RESPONSE = "EMPTY_RESPONSE"

# Mirrors response_parser candidate extraction. If any of these match, the
# provider produced something SQL-shaped that the parser still rejected — i.e.
# a validation failure, not a parse miss.
_HAS_SQL_SHAPE = re.compile(
    r"<sql>|```|^[ \t]*(?:SELECT|WITH)\b",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass
class PipelineResult:
    success: bool
    result: SQLQueryResult | None = None
    error: ErrorResponse | None = None
    retry_count: int = 0


def _classify_raw(raw: str) -> str:
    if not raw or not raw.strip():
        return EMPTY_RESPONSE
    if _HAS_SQL_SHAPE.search(raw):
        return VALIDATION_ERROR
    return PARSE_ERROR


def _retry_feedback(failure_type: str) -> str:
    if failure_type == VALIDATION_ERROR:
        return (
            "Previous attempt produced a non-read-only query. "
            "Generate ONLY a SELECT or WITH query inside <sql>...</sql> tags."
        )
    if failure_type == EMPTY_RESPONSE:
        return (
            "Previous attempt returned no content. "
            "Output your SQL strictly inside <sql>...</sql> tags."
        )
    if failure_type == TIMEOUT:
        return (
            "Previous attempt timed out. "
            "Keep the SQL concise and output it inside <sql>...</sql> tags."
        )
    return (
        "Previous attempt could not be parsed. "
        "Output your SQL strictly inside <sql>...</sql> tags."
    )


def run_pipeline(
    question: str,
    bind: Engine | Connection,
    text_provider: TextGenerationProvider,
    *,
    embedding_provider: EmbeddingProvider | None = None,
    embedding_enabled: bool = False,
    aliases: dict[str, list[str]] | None = None,
    top_n_tables: int = 5,
    char_budget: int = 4000,
    schema: str | None = None,
    max_retries: int = MAX_RETRIES,
) -> PipelineResult:
    full_schema = introspect_schema(bind, schema=schema)
    selected = retrieve(question, full_schema, aliases=aliases, top_n=top_n_tables)
    selected = rerank(
        question,
        selected,
        provider=embedding_provider,
        enabled=embedding_enabled,
    )
    schema_context = serialize_schema(selected, char_budget=char_budget)
    table_names = [t["name"] for t in selected]

    system_prompt = build_system_prompt()
    base_user_prompt = build_user_prompt(question, schema_context)
    user_prompt = base_user_prompt

    last_failure_type = PARSE_ERROR
    last_detail = ""

    for attempt in range(1, max_retries + 1):
        try:
            raw = text_provider.generate(user_prompt, system=system_prompt)
        except httpx.TimeoutException as exc:
            last_failure_type = TIMEOUT
            last_detail = str(exc)
            logger.warning(
                "pipeline attempt failed",
                extra={
                    "attempt": attempt,
                    "failure_type": TIMEOUT,
                    "selected_tables": table_names,
                    "raw_response": "",
                },
            )
            user_prompt = base_user_prompt + "\n\n" + _retry_feedback(TIMEOUT)
            continue

        parsed = parse_response(raw) if isinstance(raw, str) else None
        if parsed is not None:
            parsed = parsed.model_copy(update={"tables_used": table_names})
            logger.info(
                "pipeline attempt succeeded",
                extra={
                    "attempt": attempt,
                    "selected_tables": table_names,
                },
            )
            return PipelineResult(
                success=True,
                result=parsed,
                retry_count=attempt - 1,
            )

        raw_text = raw if isinstance(raw, str) else ""
        last_failure_type = _classify_raw(raw_text)
        last_detail = raw_text[:RAW_LOG_LIMIT]
        logger.warning(
            "pipeline attempt failed",
            extra={
                "attempt": attempt,
                "failure_type": last_failure_type,
                "selected_tables": table_names,
                "raw_response": last_detail,
            },
        )
        user_prompt = base_user_prompt + "\n\n" + _retry_feedback(last_failure_type)

    return PipelineResult(
        success=False,
        error=ErrorResponse(
            error=last_failure_type,
            detail=last_detail,
            retry_count=max_retries,
        ),
        retry_count=max_retries,
    )
