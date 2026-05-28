"""Embedding generation — protocol + BGE-M3 adapter."""

from __future__ import annotations

import gc
import threading
import time
from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class SparseVector(BaseModel):
    """Sparse vector representation for lexical matching."""

    indices: list[int]
    values: list[float]


class HybridEmbedding(BaseModel):
    """Multi-representation embedding used by hybrid retrieval."""

    dense: list[float]
    sparse: SparseVector | None = None
    colbert: list[list[float]] | None = None


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Interface for batch embedding providers."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""
        ...


class BgeM3EmbeddingProvider:
    """Embedding provider backed by ``FlagEmbedding.BGEM3FlagModel``.

    The model is lazily loaded on first use and can be released via
    :meth:`unload`. :meth:`embed` satisfies :class:`EmbeddingProvider`
    (dense only). :meth:`embed_hybrid` returns full HybridEmbedding objects.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        batch_size: int = 16,
        idle_timeout: float = 600.0,
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self.idle_timeout = float(idle_timeout)
        self._model: object | None = None
        self._last_used: float = 0.0
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def _ensure_model(self) -> object:
        """Lazily create the BGEM3FlagModel instance.

        Raises ImportError with an actionable message when FlagEmbedding
        is not installed.
        """
        with self._lock:
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

    def _reset_timer(self) -> None:
        if self.idle_timeout <= 0:
            return
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self.idle_timeout, self.unload)
            self._timer.daemon = True
            self._timer.start()

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts, returning dense vectors only (1024-d).

        Returns an empty list when *texts* is empty (no model loaded).
        """
        if not texts:
            return []
        model = self._ensure_model()
        self._last_used = time.monotonic()
        self._reset_timer()
        output = model.encode(texts)  # type: ignore[union-attr]
        return [row.tolist() for row in output["dense_vecs"]]

    def embed_hybrid(self, texts: list[str]) -> list[HybridEmbedding]:
        """Embed texts, returning full hybrid embeddings.

        Returns an empty list when *texts* is empty (no model loaded).
        """
        if not texts:
            return []

        model = self._ensure_model()
        self._last_used = time.monotonic()
        self._reset_timer()
        output = model.encode(texts, return_sparse=True, return_colbert_vecs=True)  # type: ignore[union-attr]

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
        """Release the model and reclaim memory."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            self._model = None
        gc.collect()
