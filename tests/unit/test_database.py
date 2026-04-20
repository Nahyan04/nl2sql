from app.config import get_settings
from app.core.database import get_engine


def test_get_engine_uses_configured_database_url(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")

    get_settings.cache_clear()
    get_engine.cache_clear()

    engine = get_engine()

    assert engine.url.render_as_string(hide_password=False) == "sqlite+pysqlite:///:memory:"

    engine.dispose()
    get_engine.cache_clear()
    get_settings.cache_clear()
