from __future__ import annotations

import httpx
import pytest
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
)

from app.core.providers.base import TextGenerationProvider
from app.services.query_pipeline import (
    EMPTY_RESPONSE,
    PARSE_ERROR,
    TIMEOUT,
    UNSAFE_SQL,
    VALIDATION_ERROR,
    run_pipeline,
)


def _engine_with_schema():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    metadata = MetaData()
    Table(
        "customers",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(255)),
    )
    Table(
        "orders",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("customer_id", Integer, ForeignKey("customers.id")),
        Column("status", String(50)),
    )
    metadata.create_all(engine)
    return engine


class _ScriptedProvider(TextGenerationProvider):
    def __init__(self, responses: list) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, str | None]] = []

    def generate(self, prompt: str, system: str | None = None) -> str:
        self.calls.append((prompt, system))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def test_succeeds_on_third_attempt_after_two_failures() -> None:
    provider = _ScriptedProvider(
        [
            "<sql>DROP TABLE orders</sql>",
            "I cannot help with that.",
            "<sql>SELECT id, status FROM orders</sql>",
        ]
    )
    engine = _engine_with_schema()

    result = run_pipeline("show me orders", engine, provider)

    assert result.success is True
    assert result.result is not None
    assert result.result.query == "SELECT id, status FROM orders"
    assert result.retry_count == 2
    assert len(provider.calls) == 3
    assert "non-read-only" in provider.calls[1][0]
    assert "could not be parsed" in provider.calls[2][0]


def test_returns_error_after_exhausting_retries() -> None:
    provider = _ScriptedProvider(
        ["nope", "still nope", "no sql here either"]
    )
    engine = _engine_with_schema()

    result = run_pipeline("orders", engine, provider)

    assert result.success is False
    assert result.error is not None
    assert result.error.retry_count == 3
    assert result.error.error == PARSE_ERROR
    assert result.retry_count == 3


def test_classifies_empty_response() -> None:
    provider = _ScriptedProvider(["", "   ", ""])
    engine = _engine_with_schema()

    result = run_pipeline("orders", engine, provider)

    assert result.success is False
    assert result.error.error == EMPTY_RESPONSE


def test_classifies_validation_error_for_mutating_sql() -> None:
    provider = _ScriptedProvider(
        ["<sql>DELETE FROM orders</sql>"] * 3
    )
    engine = _engine_with_schema()

    result = run_pipeline("orders", engine, provider, max_retries=3)

    assert result.success is False
    assert result.error.error == VALIDATION_ERROR


def test_classifies_timeout() -> None:
    provider = _ScriptedProvider(
        [httpx.TimeoutException("slow"), httpx.TimeoutException("slow"), httpx.TimeoutException("slow")]
    )
    engine = _engine_with_schema()

    result = run_pipeline("orders", engine, provider)

    assert result.success is False
    assert result.error.error == TIMEOUT


def test_success_includes_selected_tables() -> None:
    provider = _ScriptedProvider(
        ["<sql>SELECT id FROM orders</sql>"]
    )
    engine = _engine_with_schema()

    result = run_pipeline("show orders for each customer", engine, provider)

    assert result.success is True
    assert "orders" in result.result.tables_used
    assert "customers" in result.result.tables_used
    assert result.retry_count == 0


def test_retries_and_recovers_from_unsafe_sql() -> None:
    provider = _ScriptedProvider(
        [
            "<sql>SELECT * INTO copy_orders FROM orders</sql>",
            "<sql>SELECT id FROM orders</sql>",
        ]
    )
    engine = _engine_with_schema()

    result = run_pipeline("orders", engine, provider)

    assert result.success is True
    assert result.result.query == "SELECT id FROM orders"
    assert result.retry_count == 1
    assert "rejected as unsafe" in provider.calls[1][0]


def test_returns_unsafe_sql_error_after_exhausting_retries() -> None:
    provider = _ScriptedProvider(
        ["<sql>SELECT * INTO copy_orders FROM orders</sql>"] * 3
    )
    engine = _engine_with_schema()

    result = run_pipeline("orders", engine, provider, max_retries=3)

    assert result.success is False
    assert result.error.error == UNSAFE_SQL


def test_dry_run_attaches_explain_plan() -> None:
    provider = _ScriptedProvider(["<sql>SELECT id FROM orders</sql>"])
    engine = _engine_with_schema()

    result = run_pipeline("orders", engine, provider, dry_run=True)

    assert result.success is True
    assert result.result.explain_plan
    assert isinstance(result.result.explain_plan, list)


def test_explain_plan_absent_when_dry_run_disabled() -> None:
    provider = _ScriptedProvider(["<sql>SELECT id FROM orders</sql>"])
    engine = _engine_with_schema()

    result = run_pipeline("orders", engine, provider)

    assert result.success is True
    assert result.result.explain_plan is None


def test_logs_attempt_details(caplog: pytest.LogCaptureFixture) -> None:
    provider = _ScriptedProvider(
        ["nope", "<sql>SELECT id FROM orders</sql>"]
    )
    engine = _engine_with_schema()

    with caplog.at_level("WARNING", logger="app.services.query_pipeline"):
        result = run_pipeline("orders", engine, provider)

    assert result.success is True
    failed_records = [r for r in caplog.records if r.message == "pipeline attempt failed"]
    assert len(failed_records) == 1
    record = failed_records[0]
    assert record.attempt == 1
    assert record.failure_type == PARSE_ERROR
    assert "orders" in record.selected_tables
    assert record.raw_response == "nope"
