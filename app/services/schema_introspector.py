from __future__ import annotations

from typing import Any

from sqlalchemy import inspect
from sqlalchemy.engine import Connection, Engine


def introspect_schema(bind: Engine | Connection, schema: str | None = None) -> dict[str, Any]:
    inspector = inspect(bind)
    schema_name = schema or inspector.default_schema_name
    table_names = sorted(inspector.get_table_names(schema=schema))

    tables = [build_table_metadata(inspector, table_name, schema) for table_name in table_names]

    return {
        "schema": schema_name,
        "tables": tables,
    }


def build_table_metadata(inspector: Any, table_name: str, schema: str | None) -> dict[str, Any]:
    primary_key = inspector.get_pk_constraint(table_name, schema=schema) or {}
    primary_key_columns = list(primary_key.get("constrained_columns") or [])

    columns = []
    for column in inspector.get_columns(table_name, schema=schema):
        columns.append(
            {
                "name": column["name"],
                "type": str(column["type"]),
                "nullable": bool(column.get("nullable", True)),
            }
        )

    foreign_keys = []
    for foreign_key in inspector.get_foreign_keys(table_name, schema=schema):
        foreign_keys.append(
            {
                "name": foreign_key.get("name"),
                "columns": list(foreign_key.get("constrained_columns") or []),
                "referred_schema": foreign_key.get("referred_schema"),
                "referred_table": foreign_key.get("referred_table"),
                "referred_columns": list(foreign_key.get("referred_columns") or []),
            }
        )

    return {
        "name": table_name,
        "columns": columns,
        "primary_key": primary_key_columns,
        "foreign_keys": foreign_keys,
    }
