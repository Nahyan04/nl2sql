from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy import text

router = APIRouter()


@router.get("/health")
def health_check(request: Request) -> dict[str, str]:
    engine = request.app.state.engine
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok"}
