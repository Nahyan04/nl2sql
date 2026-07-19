from __future__ import annotations

import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from app.api.routes import query as query_routes
from app.config import get_settings
from app.core.database import get_engine
from app.core.providers.ollama import OllamaEmbeddingProvider, OllamaTextProvider


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


app = FastAPI(title="nl2sql", lifespan=lifespan)

app.include_router(query_routes.router, prefix="/api/v1")

# TODO: restrict allow_origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
