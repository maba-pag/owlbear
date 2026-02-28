"""Reranking — protocol + BGE reranker adapter.

Standalone module with no dependency on other knowledge submodules
(graph, schema, vectors).  Provides a :class:`RerankerProvider` protocol
and a :class:`BGERerankerProvider` backed by ``FlagEmbedding.FlagReranker``.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

DEFAULT_RERANKER_MODEL: str = "BAAI/bge-reranker-v2-m3"
"""Default cross-encoder reranker model name."""


@runtime_checkable
class RerankerProvider(Protocol):
    """Interface for passage rerankers.

    Implementations accept a query string and a list of passage strings,
    returning ``(index, score)`` pairs sorted by descending relevance score.
    """

    def rerank(self, query: str, passages: list[str]) -> list[tuple[int, float]]:
        """Return ``(index, score)`` pairs sorted by descending score."""
        ...


class BGERerankerProvider:
    """Reranker backed by ``FlagEmbedding.FlagReranker`` (cross-encoder).

    The underlying model is lazily initialized on the first call to
    :meth:`rerank` to avoid import cost and model loading at construction
    time.
    """

    def __init__(self, model_name: str = DEFAULT_RERANKER_MODEL) -> None:
        self.model_name = model_name
        self._model: object | None = None

    # -- internal helpers ---------------------------------------------------

    def _ensure_model(self) -> object:
        """Lazily create the ``FlagReranker`` instance."""
        if self._model is None:
            from FlagEmbedding import FlagReranker  # noqa: PLC0415

            self._model = FlagReranker(self.model_name)
        return self._model

    # -- public API ---------------------------------------------------------

    def rerank(self, query: str, passages: list[str]) -> list[tuple[int, float]]:
        """Rerank *passages* for *query*.

        Returns ``(index, score)`` pairs sorted by descending score.
        Returns an empty list when *passages* is empty (no model loaded).
        """
        if not passages:
            return []

        model = self._ensure_model()
        pairs = [[query, p] for p in passages]
        scores = model.compute_score(pairs)  # type: ignore[union-attr]

        # FlagReranker returns a bare float for a single pair.
        if isinstance(scores, float):
            scores = [scores]

        indexed = [(i, float(s)) for i, s in enumerate(scores)]
        indexed.sort(key=lambda x: x[1], reverse=True)
        return indexed
