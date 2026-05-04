from __future__ import annotations

from abc import ABC, abstractmethod


class TextGenerationProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system: str | None = None) -> str: ...


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...
