from app.services.retrieval.reranker import rerank


class _MockEmbeddingProvider:
    """Returns fixed vectors so tests control cosine similarity outcomes."""

    def __init__(self, vectors: dict[str, list[float]]):
        self._vectors = vectors

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._vectors[t] for t in texts]


def _make_tables(names: list[str]) -> list[dict]:
    return [{"name": name, "descriptor": name} for name in names]


def test_rerank_disabled_returns_original_order() -> None:
    tables = _make_tables(["products", "orders", "customers"])
    result = rerank("show purchases", tables, provider=None, enabled=False)
    assert [r["name"] for r in result] == ["products", "orders", "customers"]


def test_rerank_no_provider_returns_original_order() -> None:
    tables = _make_tables(["products", "orders"])
    result = rerank("show orders", tables, provider=None, enabled=True)
    assert [r["name"] for r in result] == ["products", "orders"]


def test_rerank_with_provider_sorts_by_cosine_similarity() -> None:
    # question vector is close to "orders", far from "products"
    provider = _MockEmbeddingProvider(
        {
            "what are the purchases": [1.0, 0.0, 0.0],
            "orders": [0.95, 0.1, 0.0],
            "products": [0.0, 0.0, 1.0],
        }
    )
    tables = _make_tables(["products", "orders"])
    result = rerank("what are the purchases", tables, provider=provider, enabled=True)
    assert result[0]["name"] == "orders"


def test_rerank_purchases_resolves_toward_orders_with_embeddings() -> None:
    # simulates semantic "purchases" ≈ "orders" embedding signal
    provider = _MockEmbeddingProvider(
        {
            "purchases": [1.0, 0.0, 0.0],
            "orders": [0.9, 0.2, 0.0],
            "customers": [0.0, 1.0, 0.0],
            "products": [0.0, 0.0, 1.0],
        }
    )
    tables = _make_tables(["customers", "products", "orders"])
    result = rerank("purchases", tables, provider=provider, enabled=True)
    result_names = [r["name"] for r in result]
    assert result_names.index("orders") < result_names.index("products")


def test_rerank_preserves_all_tables() -> None:
    provider = _MockEmbeddingProvider(
        {
            "q": [1.0, 0.0],
            "a": [1.0, 0.0],
            "b": [0.0, 1.0],
            "c": [0.5, 0.5],
        }
    )
    tables = _make_tables(["a", "b", "c"])
    result = rerank("q", tables, provider=provider, enabled=True)
    assert len(result) == 3
    assert {r["name"] for r in result} == {"a", "b", "c"}


def test_rerank_uses_descriptor_field_for_embedding() -> None:
    # descriptor differs from name — provider must receive descriptor text
    provider = _MockEmbeddingProvider(
        {
            "q": [1.0, 0.0],
            "orders(id, status)": [0.9, 0.1],
            "products(id, title)": [0.0, 1.0],
        }
    )
    tables = [
        {"name": "products", "descriptor": "products(id, title)"},
        {"name": "orders", "descriptor": "orders(id, status)"},
    ]
    result = rerank("q", tables, provider=provider, enabled=True)
    assert result[0]["name"] == "orders"
