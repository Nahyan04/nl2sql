"""Model provider adapters live here."""
from __future__ import annotations

from app.core.providers.base import EmbeddingProvider, TextGenerationProvider
from app.core.providers.ollama import OllamaEmbeddingProvider, OllamaTextProvider


def get_text_provider(provider: str, base_url: str, model: str) -> TextGenerationProvider:
    if provider == "ollama":
        return OllamaTextProvider(base_url=base_url, model=model)
    raise ValueError(f"unknown text provider: {provider!r}")


def get_embedding_provider(provider: str, base_url: str, model: str) -> EmbeddingProvider:
    if provider == "ollama":
        return OllamaEmbeddingProvider(base_url=base_url, model=model)
    raise ValueError(f"unknown embedding provider: {provider!r}")
