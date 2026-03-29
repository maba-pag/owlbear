"""Embedding generation — stub, not yet implemented (#15)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from owlbear_knowledge.protocol import HybridEmbedding

_NOT_IMPL = "BgeM3EmbeddingProvider not yet extracted from v1"


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Interface for batch embedding providers."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""
        ...


class BgeM3EmbeddingProvider:
    """Stub — raises NotImplementedError until extracted from v1."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        batch_size: int = 16,
        idle_timeout: float = 600.0,
    ) -> None:
        raise NotImplementedError(_NOT_IMPL)

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_hybrid(self, texts: list[str]) -> list[HybridEmbedding]:
        raise NotImplementedError

    def unload(self) -> None:
        raise NotImplementedError
