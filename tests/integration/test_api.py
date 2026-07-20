from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.core.providers.base import TextGenerationProvider


class _FakeTextProvider(TextGenerationProvider):
    def __init__(self, response: str) -> None:
        self.response = response

    def generate(self, prompt: str, system: str | None = None) -> str:
        return self.response


@pytest.fixture
def client(sqlite_engine, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("EMBEDDING_ENABLED", "false")
    main.get_settings.cache_clear()

    fake_provider = _FakeTextProvider("<sql>SELECT id FROM orders</sql>")
    with (
        patch("app.main.get_engine", return_value=sqlite_engine),
        patch("app.main.OllamaTextProvider", return_value=fake_provider),
        patch("app.main.OllamaEmbeddingProvider"),
    ):
        with TestClient(main.app) as test_client:
            yield test_client

    main.get_settings.cache_clear()


def test_health_check_returns_ok(client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "X-Request-ID" in response.headers


def test_service_info_returns_configuration(client) -> None:
    response = client.get("/info")

    assert response.status_code == 200
    assert response.json()["provider"] == "ollama"


def test_get_schema_returns_seeded_tables(client) -> None:
    response = client.get("/api/v1/schema")

    assert response.status_code == 200
    table_names = [table["name"] for table in response.json()["tables"]]
    assert "customers" in table_names
    assert "orders" in table_names


def test_get_table_schema_404_for_unknown_table(client) -> None:
    response = client.get("/api/v1/schema/does_not_exist")

    assert response.status_code == 404


def test_create_query_happy_path_returns_sql(client) -> None:
    response = client.post("/api/v1/query", json={"question": "show me orders"})

    assert response.status_code == 200
    assert response.json()["query"] == "SELECT id FROM orders"


def test_create_query_rejects_blank_question(client) -> None:
    response = client.post("/api/v1/query", json={"question": "   "})

    assert response.status_code == 400
    assert response.json()["error"] == "EMPTY_QUESTION"


def test_create_query_validation_error_for_missing_field(client) -> None:
    response = client.post("/api/v1/query", json={})

    assert response.status_code == 422
    assert response.json()["error"] == "VALIDATION_ERROR"
