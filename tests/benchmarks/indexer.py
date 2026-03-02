"""Embedding + indexing pipeline for IR benchmarks.

Embeds a corpus using :class:`~owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider`
and indexes the results into an in-memory
:class:`~owlbear.memory.knowledge.qdrant.QdrantVectorStore`.  Embeddings
are cached to disk (pickle) so the expensive model inference (~10 min) is
only paid once.

Task: #378
"""

from __future__ import annotations

import hashlib
import logging
import pickle
from pathlib import Path

from owlbear.memory.knowledge.embeddings import BgeM3EmbeddingProvider
from owlbear.memory.knowledge.protocol import HybridEmbedding
from owlbear.memory.knowledge.qdrant import QdrantVectorStore

logger = logging.getLogger(__name__)

_DEFAULT_CACHE_DIR = Path(__file__).parent / ".cache"
_CACHE_FILENAME = "embeddings.pkl"


def _corpus_hash(corpus: dict[str, str]) -> str:
    """SHA-256 hash of sorted corpus keys for cache invalidation.

    Args:
        corpus: Mapping of document IDs to document text.

    Returns:
        Hex digest string.
    """
    key_str = "\n".join(sorted(corpus.keys()))
    return hashlib.sha256(key_str.encode()).hexdigest()


def embed_and_index(
    corpus: dict[str, str],
    cache_dir: Path | None = None,
) -> QdrantVectorStore:
    """Embed a corpus and load it into an in-memory Qdrant store.

    On the first run, all documents are embedded with
    :meth:`BgeM3EmbeddingProvider.embed_hybrid` (dense + sparse + ColBERT)
    and the results are cached as a pickle file.  Subsequent runs with
    the same corpus keys load from cache, skipping the ~10 min model
    inference step.

    Args:
        corpus: Mapping of ``{doc_id: doc_text}``.
        cache_dir: Directory for the embedding cache file.
            Defaults to ``tests/benchmarks/.cache/``.

    Returns:
        A :class:`QdrantVectorStore` instance (in-memory) populated
        with all corpus embeddings, ready for search.
    """
    cache = cache_dir or _DEFAULT_CACHE_DIR
    cache.mkdir(parents=True, exist_ok=True)
    cache_file = cache / _CACHE_FILENAME

    current_hash = _corpus_hash(corpus)
    doc_ids = list(corpus.keys())
    embeddings: dict[str, HybridEmbedding] | None = None

    # --- try loading from cache -------------------------------------------
    if cache_file.exists():
        with cache_file.open("rb") as f:
            cached = pickle.load(f)  # noqa: S301
        if cached.get("hash") == current_hash:
            n = len(cached["embeddings"])
            logger.info("Cache hit — loading %d embeddings from %s", n, cache_file)
            embeddings = cached["embeddings"]

    # --- embed on cache miss ----------------------------------------------
    if embeddings is None:
        logger.info("Cache miss — embedding %d documents", len(corpus))
        provider = BgeM3EmbeddingProvider()
        texts = list(corpus.values())
        embedded = provider.embed_hybrid(texts)
        provider.unload()
        embeddings = dict(zip(doc_ids, embedded, strict=True))

        # persist cache
        cache_data = {"hash": current_hash, "embeddings": embeddings}
        with cache_file.open("wb") as f:
            pickle.dump(cache_data, f)
        logger.info("Cached embeddings to %s", cache_file)

    # --- populate Qdrant --------------------------------------------------
    store = QdrantVectorStore(location=":memory:")
    for doc_id, emb in embeddings.items():
        store.store_embedding(doc_id, emb, "document")

    logger.info("Indexed %d documents into QdrantVectorStore(:memory:)", len(embeddings))
    return store
