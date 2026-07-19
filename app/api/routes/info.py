from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/info")
def service_info(request: Request) -> dict[str, str]:
    settings = request.app.state.settings
    engine = request.app.state.engine

    return {
        "version": request.app.version,
        "provider": settings.llm_provider,
        "model": settings.llm_model,
        "retrieval_mode": settings.retrieval_mode,
        "database_host": engine.url.host or "",
    }
