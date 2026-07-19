from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.services.schema_introspector import introspect_schema

router = APIRouter()


@router.get("/schema")
def get_schema(request: Request) -> dict[str, Any]:
    return introspect_schema(request.app.state.engine)


@router.get("/schema/{table_name}")
def get_table_schema(table_name: str, request: Request) -> dict[str, Any]:
    schema = introspect_schema(request.app.state.engine)

    for table in schema["tables"]:
        if table["name"] == table_name:
            return table

    raise HTTPException(status_code=404, detail=f"table '{table_name}' not found")
