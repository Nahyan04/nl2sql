from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import health as health_routes
from app.api.routes import info as info_routes
from app.api.routes import query as query_routes
from app.api.routes import schema as schema_routes
from app.config import get_settings
from app.core.database import get_engine
from app.core.logging import RequestIdMiddleware, configure_logging
from app.core.providers.ollama import OllamaEmbeddingProvider, OllamaTextProvider
from app.models.query_response import ErrorResponse

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        settings = get_settings()
    except ValidationError as exc:
        sys.exit(f"configuration error — cannot start:\n{exc}")

    engine = get_engine()
    # Fail fast: verify the database is reachable before accepting traffic
    with engine.connect():
        pass

    app.state.engine = engine
    app.state.settings = settings
    app.state.text_provider = OllamaTextProvider(settings.llm_base_url, settings.llm_model)
    app.state.embedding_provider = (
        OllamaEmbeddingProvider(settings.llm_base_url, settings.embedding_model)
        if settings.embedding_enabled
        else None
    )

    yield

    engine.dispose()


app = FastAPI(title="nl2sql", version="0.1.0", lifespan=lifespan)

app.include_router(query_routes.router, prefix="/api/v1")
app.include_router(schema_routes.router, prefix="/api/v1")
app.include_router(health_routes.router)
app.include_router(info_routes.router)

# TODO: restrict allow_origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIdMiddleware)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(error="VALIDATION_ERROR", detail=str(exc)).model_dump(),
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.error("database error", extra={"path": request.url.path}, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(error="DATABASE_ERROR", detail="a database error occurred").model_dump(),
    )


@app.exception_handler(httpx.HTTPError)
async def provider_exception_handler(request: Request, exc: httpx.HTTPError) -> JSONResponse:
    logger.error("provider error", extra={"path": request.url.path}, exc_info=exc)
    return JSONResponse(
        status_code=502,
        content=ErrorResponse(error="PROVIDER_ERROR", detail="the LLM provider is unreachable").model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled error", extra={"path": request.url.path}, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(error="INTERNAL_ERROR", detail="an unexpected error occurred").model_dump(),
    )
