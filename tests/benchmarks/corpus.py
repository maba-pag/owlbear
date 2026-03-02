"""Corpus loading utilities for IR benchmarks.

Downloads BEIR datasets and caches them locally so subsequent runs
skip the network entirely.

Task: #377
"""

from __future__ import annotations

from pathlib import Path

_DEFAULT_CACHE_DIR = Path(__file__).parent / ".cache"


def load_nfcorpus(
    cache_dir: Path | None = None,
) -> tuple[dict[str, str], dict[str, str], dict[str, dict[str, int]]]:
    """Download and return the NFCorpus dataset from BEIR.

    Data is cached to ``tests/benchmarks/.cache/nfcorpus/`` after first
    download.  Subsequent calls load from cache without network access.

    Args:
        cache_dir: Override the default cache directory.

    Returns:
        A 3-tuple of ``(corpus, queries, qrels)`` where:

        - **corpus** maps document IDs to document text.
        - **queries** maps query IDs to query text.
        - **qrels** maps query IDs to dicts of ``{doc_id: relevance_score}``.
    """
    import pytest

    beir_util = pytest.importorskip(
        "beir.util",
        reason="beir required — install with: uv pip install 'owlbear[benchmark]'",
    )
    from beir.datasets.data_loader import GenericDataLoader

    cache = cache_dir or _DEFAULT_CACHE_DIR
    cache.mkdir(parents=True, exist_ok=True)

    data_path = cache / "nfcorpus"

    # Download only when the corpus file is not yet cached.
    if not (data_path / "corpus.jsonl").exists():
        url = (
            "https://public.ukp.informatik.tu-darmstadt.de/"
            "thakur/BEIR/datasets/nfcorpus.zip"
        )
        extracted = beir_util.download_and_unzip(url, str(cache))
        data_path = Path(extracted)

    raw_corpus, queries, qrels = GenericDataLoader(
        data_folder=str(data_path),
    ).load(split="test")

    # BEIR corpus: {doc_id: {"title": str, "text": str}} → {doc_id: str}
    corpus: dict[str, str] = {}
    for doc_id, doc in raw_corpus.items():
        title = doc.get("title", "")
        text = doc.get("text", "")
        corpus[doc_id] = f"{title}\n{text}".strip() if title else text

    return corpus, queries, qrels
