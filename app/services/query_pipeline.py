from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.engine import Connection, Engine

from app.core.prompt_builder import build_system_prompt, build_user_prompt
from app.core.providers.base import EmbeddingProvider, TextGenerationProvider
from app.models.query_response import ErrorResponse, SQLQueryResult
from app.services.response_parser import parse_response
from app.services.retrieval.lexical import retrieve
from app.services.retrieval.reranker import rerank
from app.services.schema_introspector import introspect_schema
from app.services.schema_serializer import serialize_schema

MAX_RETRIES = 3


@dataclass
class PipelineResult:
    success: bool
    result: SQLQueryResult | None = None
    error: ErrorResponse | None = None
    retry_count: int = 0


def _retry_feedback(raw: str | None) -> str:
    if raw is None:
        return (
            "Previous attempt returned no content. "
            "Output your SQL strictly inside <sql>...</sql> tags."
        )
    return (
        "Previous attempt could not be parsed or was not a read-only query. "
        "Output ONLY a SELECT or WITH query inside <sql>...</sql> tags."
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

    last_detail = ""

    for attempt in range(1, max_retries + 1):
        raw = text_provider.generate(user_prompt, system=system_prompt)

        parsed = _try_parse(raw)
        if parsed is not None:
            parsed = parsed.model_copy(update={"tables_used": table_names})
            return PipelineResult(success=True, result=parsed, retry_count=attempt - 1)

        last_detail = (raw or "")[:500]
        user_prompt = base_user_prompt + "\n\n" + _retry_feedback(raw)

    return PipelineResult(
        success=False,
        error=ErrorResponse(
            error="PIPELINE_FAILED",
            detail=last_detail,
            retry_count=max_retries,
        ),
        retry_count=max_retries,
    )


def _try_parse(raw: Any) -> SQLQueryResult | None:
    if raw is None:
        return None
    if not isinstance(raw, str):
        return None
    if not raw.strip():
        return None
    return parse_response(raw)
