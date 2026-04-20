from app.config import get_settings


def test_get_settings_reads_expected_environment_values(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("LLM_MODEL", "qwen2.5:7b")
    monkeypatch.setenv("EMBEDDING_ENABLED", "true")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "ollama")
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("RETRIEVAL_MODE", "hybrid")

    get_settings.cache_clear()
    settings = get_settings()

    assert settings.database_url == "postgresql://postgres:postgres@localhost:5432/postgres"
    assert settings.llm_provider == "ollama"
    assert settings.llm_base_url == "http://localhost:11434"
    assert settings.llm_model == "qwen2.5:7b"
    assert settings.embedding_enabled is True
    assert settings.embedding_provider == "ollama"
    assert settings.embedding_model == "nomic-embed-text"
    assert settings.retrieval_mode == "hybrid"

    get_settings.cache_clear()
