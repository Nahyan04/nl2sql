from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.models.query_response import ErrorResponse, QueryRequest, SQLQueryResult
from app.services.query_pipeline import run_pipeline

router = APIRouter()


@router.post(
    "/query",
    response_model=SQLQueryResult,
    responses={422: {"model": ErrorResponse}},
)
def create_query(body: QueryRequest, request: Request) -> SQLQueryResult | JSONResponse:
    if not body.question.strip():
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(error="EMPTY_QUESTION", detail="question must not be blank").model_dump(),
        )

    settings = request.app.state.settings
    result = run_pipeline(
        question=body.question,
        bind=request.app.state.engine,
        text_provider=request.app.state.text_provider,
        embedding_provider=request.app.state.embedding_provider,
        embedding_enabled=settings.embedding_enabled,
        aliases=request.app.state.aliases,
        top_n_tables=body.top_n_tables,
        dry_run=body.dry_run,
    )

    if result.success:
        return result.result

    return JSONResponse(
        status_code=422,
        content=result.error.model_dump(),
    )
