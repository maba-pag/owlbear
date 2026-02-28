"""Embedding generation — protocol + BGE-M3 adapter.

Standalone module with no dependency on other knowledge submodules
(graph, schema).
"""

from __future__ import annotations

import gc
from typing import Protocol, runtime_checkable

from owlbear.memory.knowledge.protocol import HybridEmbedding, SparseVector


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Interface for batch embedding providers."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""
        ...


class BgeM3EmbeddingProvider:
    """Embedding provider backed by ``FlagEmbedding.BGEM3FlagModel``.

    Produces dense (1024-d), sparse (lexical weights), and ColBERT
    multi-vector embeddings.  The model is lazily loaded on first use
    (~3 GB RAM) and can be released via :meth:`unload`.

    :meth:`embed` satisfies the :class:`EmbeddingProvider` protocol
    (dense only).  :meth:`embed_hybrid` returns full
    :class:`~owlbear.memory.knowledge.protocol.HybridEmbedding` objects.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        batch_size: int = 16,
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self._model: object | None = None

    # -- internal helpers ---------------------------------------------------

    def _ensure_model(self) -> object:
        """Lazily create the ``BGEM3FlagModel`` instance.

        Raises :class:`ImportError` with an actionable message when the
        ``FlagEmbedding`` package is not installed.
        """
        if self._model is None:
            try:
                from FlagEmbedding import BGEM3FlagModel  # noqa: PLC0415
            except ImportError:
                msg = (
                    "FlagEmbedding is required for BgeM3EmbeddingProvider. "
                    "Install it with: uv pip install FlagEmbedding"
                )
                raise ImportError(msg) from None

            self._model = BGEM3FlagModel(
                self.model_name,
                use_fp16=True,
                devices=["cpu"],
                batch_size=self.batch_size,
            )
        return self._model

    # -- public API ---------------------------------------------------------

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts, returning dense vectors only (1024-d).

        Returns an empty list when *texts* is empty (no model loaded).
        """
        if not texts:
            return []

        model = self._ensure_model()
        output = model.encode(texts)  # type: ignore[union-attr]
        return [row.tolist() for row in output["dense_vecs"]]

    def embed_hybrid(self, texts: list[str]) -> list[HybridEmbedding]:
        """Embed texts, returning full hybrid embeddings.

        Each :class:`~owlbear.memory.knowledge.protocol.HybridEmbedding`
        contains dense, sparse, and ColBERT representations.

        Returns an empty list when *texts* is empty (no model loaded).
        """
        if not texts:
            return []

        model = self._ensure_model()
        output = model.encode(texts)  # type: ignore[union-attr]

        results: list[HybridEmbedding] = []
        for i in range(len(texts)):
            dense = output["dense_vecs"][i].tolist()

            lex = output["lexical_weights"][i]
            sparse = SparseVector(
                indices=[int(k) for k in lex],
                values=list(lex.values()),
            )

            colbert = output["colbert_vecs"][i].tolist()

            results.append(HybridEmbedding(dense=dense, sparse=sparse, colbert=colbert))
        return results

    def unload(self) -> None:
        """Release the model and reclaim memory (~3 GB)."""
        self._model = None
        gc.collect()
