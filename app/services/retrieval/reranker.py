from __future__ import annotations

import math
from typing import Any, Protocol


class EmbeddingProvider(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x ** 2 for x in a))
    norm_b = math.sqrt(sum(x ** 2 for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def rerank(
    question: str,
    tables: list[dict[str, Any]],
    provider: EmbeddingProvider | None = None,
    enabled: bool = False,
) -> list[dict[str, Any]]:
    if not enabled or provider is None:
        return list(tables)

    descriptors = [t.get("descriptor") or t["name"] for t in tables]
    texts = [question] + descriptors
    vectors = provider.embed_texts(texts)
    question_vec, *table_vecs = vectors

    scored = sorted(
        zip(tables, table_vecs),
        key=lambda pair: _cosine(question_vec, pair[1]),
        reverse=True,
    )
    return [t for t, _ in scored]
