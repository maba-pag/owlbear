"""Shared fixtures for the benchmark suite.

Provides session-scoped corpus fixtures so that expensive downloads
and data loading happen at most once per ``pytest`` invocation.

Tasks: #377, #378
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.benchmarks.corpus import load_nfcorpus
from tests.benchmarks.indexer import embed_and_index

if TYPE_CHECKING:
    from owlbear.memory.knowledge.qdrant import QdrantVectorStore


@pytest.fixture(scope="session")
def nfcorpus() -> tuple[dict[str, str], dict[str, str], dict[str, dict[str, int]]]:
    """Load NFCorpus dataset, cached across the entire test session.

    Returns:
        A 3-tuple of ``(corpus, queries, qrels)``.
    """
    return load_nfcorpus()


@pytest.fixture(scope="session")
def indexed_store(
    nfcorpus: tuple[dict[str, str], dict[str, str], dict[str, dict[str, int]]],
) -> QdrantVectorStore:
    """Embed all NFCorpus docs and load into an in-memory Qdrant store.

    Uses cached embeddings when available; falls back to
    :func:`~tests.benchmarks.indexer.embed_and_index` for first-run
    embedding (~10 min).  Subsequent runs load from
    ``tests/benchmarks/.cache/embeddings.pkl`` in seconds.

    Returns:
        A populated :class:`QdrantVectorStore` ready for search.
    """
    corpus, _queries, _qrels = nfcorpus
    return embed_and_index(corpus)
