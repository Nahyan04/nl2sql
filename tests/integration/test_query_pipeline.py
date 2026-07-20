from __future__ import annotations

from app.core.providers.base import TextGenerationProvider
from app.services.query_pipeline import run_pipeline


class _FakeTextProvider(TextGenerationProvider):
    def __init__(self, response: str) -> None:
        self.response = response

    def generate(self, prompt: str, system: str | None = None) -> str:
        return self.response


def test_pipeline_returns_valid_sql_against_seeded_data(sqlite_engine) -> None:
    provider = _FakeTextProvider("<sql>SELECT status FROM orders WHERE customer_id = 1</sql>")

    result = run_pipeline("what is the status of orders for customer 1", sqlite_engine, provider)

    assert result.success is True
    assert result.result.query == "SELECT status FROM orders WHERE customer_id = 1"
    assert "orders" in result.result.tables_used


def test_pipeline_dry_run_produces_explain_plan_against_real_data(sqlite_engine) -> None:
    provider = _FakeTextProvider("<sql>SELECT * FROM orders</sql>")

    result = run_pipeline("show all orders", sqlite_engine, provider, dry_run=True)

    assert result.success is True
    assert result.result.explain_plan
