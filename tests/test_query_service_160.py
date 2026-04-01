"""Tests for KnowledgeQueryService refactor — task #160.

AC coverage:
- AC1: _search_chunks(prompt, top_k) — delegates to retriever when set, else embed+search
- AC2: query() uses _search_chunks() — retriever is exercised when configured
- AC3: query_for_context() uses _search_chunks(); top_k and scopes forwarded to retriever
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from owlbear_knowledge.query_service import KnowledgeQueryService
from owlbear_knowledge.retrieval import RetrievalResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_graph() -> MagicMock:
    graph = MagicMock()
    graph.get_document_id_for_chunk.return_value = "doc1"
    graph.get_document.return_value = MagicMock(
        title="Title", content="content " * 50, scope="global"
    )
    graph.list_entities_for_document.return_value = []
    return graph


def _make_service(
    *,
    retriever: object | None = None,
    scopes: list[str] | None = None,
    threshold: float = 0.3,
) -> KnowledgeQueryService:
    vector_store = MagicMock()
    vector_store.search_similar.return_value = [("doc1", 0.8)]
    embedder = MagicMock()
    embedder.embed.return_value = [[0.1] * 10]
    return KnowledgeQueryService(
        vector_store=vector_store,
        graph_store=_make_graph(),
        embedding_provider=embedder,
        scopes=scopes,
        similarity_threshold=threshold,
        retriever=retriever,
    )


def _fake_retriever(chunks: list[tuple[str, float]] | None = None) -> MagicMock:
    retriever = MagicMock()
    retriever.retrieve.return_value = RetrievalResult(
        chunks=chunks if chunks is not None else [("doc1", 0.9)],
        expansion_text="",
        entities_found=0,
    )
    return retriever


# ---------------------------------------------------------------------------
# AC1 — _search_chunks(prompt, top_k) method
# ---------------------------------------------------------------------------


class TestFromAC_SearchChunksDelegation:

    # ---------------------------------------------------------------- Happy

    def test_search_chunks_method_exists(self) -> None:
        """_search_chunks must be a callable attribute on KnowledgeQueryService."""
        svc = _make_service()
        assert hasattr(svc, "_search_chunks"), "_search_chunks not found on KnowledgeQueryService"
        assert callable(svc._search_chunks)

    def test_search_chunks_no_retriever_calls_embed_with_prompt(self) -> None:
        """Without retriever, _search_chunks embeds the exact prompt string."""
        svc = _make_service()
        svc._search_chunks("my specific query", 5)
        svc._embedder.embed.assert_called_once_with(["my specific query"])

    def test_search_chunks_no_retriever_calls_vector_store(self) -> None:
        """Without retriever, _search_chunks calls vector_store.search_similar."""
        svc = _make_service()
        svc._search_chunks("q", 5)
        svc._vectors.search_similar.assert_called_once()

    def test_search_chunks_no_retriever_returns_id_score_pairs(self) -> None:
        """Without retriever, _search_chunks returns (str, float) pairs from vector_store."""
        svc = _make_service()
        result = svc._search_chunks("q", 3)
        assert isinstance(result, list), "_search_chunks must return a list"
        assert len(result) > 0
        chunk_id, score = result[0]
        assert isinstance(chunk_id, str)
        assert isinstance(score, float)

    def test_search_chunks_with_retriever_calls_retrieve(self) -> None:
        """With retriever set, _search_chunks calls retriever.retrieve."""
        retriever = _fake_retriever()
        svc = _make_service(retriever=retriever)
        svc._search_chunks("hello", 4)
        retriever.retrieve.assert_called_once()

    def test_search_chunks_with_retriever_forwards_prompt(self) -> None:
        """_search_chunks forwards the prompt string to retriever.retrieve."""
        retriever = _fake_retriever()
        svc = _make_service(retriever=retriever)
        svc._search_chunks("important prompt", 5)
        call_args = retriever.retrieve.call_args
        all_args = list(call_args.args) + list(call_args.kwargs.values())
        assert "important prompt" in all_args

    def test_search_chunks_with_retriever_forwards_top_k(self) -> None:
        """_search_chunks forwards top_k to retriever.retrieve as positional or keyword arg."""
        retriever = _fake_retriever()
        svc = _make_service(retriever=retriever)
        svc._search_chunks("q", 7)
        call_args = retriever.retrieve.call_args
        all_values = list(call_args.args) + list(call_args.kwargs.values())
        assert 7 in all_values, f"top_k=7 not found in retrieve call args: {call_args}"

    def test_search_chunks_with_retriever_forwards_scopes(self) -> None:
        """_search_chunks forwards self._scopes list to retriever.retrieve."""
        retriever = _fake_retriever()
        svc = _make_service(retriever=retriever, scopes=["scope-a", "scope-b"])
        svc._search_chunks("q", 5)
        call_args = retriever.retrieve.call_args
        all_values = list(call_args.args) + list(call_args.kwargs.values())
        assert ["scope-a", "scope-b"] in all_values, (
            f"scopes=['scope-a','scope-b'] not found in retrieve call: {call_args}"
        )

    # ----------------------------------------------------------------- Edge

    def test_search_chunks_with_retriever_passes_none_scopes_not_empty_list(self) -> None:
        """When scopes=None, retriever.retrieve must receive None (not an empty list)."""
        retriever = _fake_retriever()
        svc = _make_service(retriever=retriever, scopes=None)
        svc._search_chunks("q", 5)
        call_args = retriever.retrieve.call_args
        all_values = list(call_args.args) + list(call_args.kwargs.values())
        assert None in all_values, f"None scopes must pass None to retriever, got: {call_args}"

    def test_search_chunks_with_retriever_does_not_call_embed(self) -> None:
        """With retriever set, _search_chunks must not call embedder.embed."""
        retriever = _fake_retriever()
        svc = _make_service(retriever=retriever)
        svc._search_chunks("q", 5)
        svc._embedder.embed.assert_not_called()

    def test_search_chunks_with_retriever_returns_retrieval_chunks(self) -> None:
        """_search_chunks returns the exact chunks list from RetrievalResult."""
        retriever = _fake_retriever(chunks=[("chunk-x", 0.95), ("chunk-y", 0.7)])
        svc = _make_service(retriever=retriever)
        result = svc._search_chunks("q", 5)
        assert result == [("chunk-x", 0.95), ("chunk-y", 0.7)], (
            f"Expected retriever chunks, got: {result}"
        )


# ---------------------------------------------------------------------------
# AC2 — query() uses _search_chunks() as its vector-search path
# ---------------------------------------------------------------------------


class TestFromAC_QueryUsesSearchChunks:

    @pytest.mark.asyncio(loop_scope="function")
    async def test_query_with_retriever_calls_retrieve_not_embed(self) -> None:
        """query() must call retriever.retrieve when retriever is configured."""
        retriever = _fake_retriever()
        svc = _make_service(retriever=retriever)
        await svc.query("test prompt", top_k=3)
        retriever.retrieve.assert_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_query_with_retriever_does_not_call_embedder_embed(self) -> None:
        """query() with retriever must not call embedder.embed directly — retriever embedding is authoritative."""
        retriever = _fake_retriever()
        svc = _make_service(retriever=retriever)
        await svc.query("test prompt", top_k=3)
        svc._embedder.embed.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_query_with_retriever_forwards_top_k_to_retrieve(self) -> None:
        """query(top_k=N) must forward N to the retriever path."""
        retriever = _fake_retriever()
        svc = _make_service(retriever=retriever)
        await svc.query("test", top_k=8)
        call_args = retriever.retrieve.call_args
        all_values = list(call_args.args) + list(call_args.kwargs.values())
        assert 8 in all_values, f"top_k=8 not forwarded to retrieve: {call_args}"


# ---------------------------------------------------------------------------
# AC3 — query_for_context() uses _search_chunks(), forwards top_k + scopes
# ---------------------------------------------------------------------------


class TestFromAC_QueryForContextUsesSearchChunks:

    def test_query_for_context_forwards_top_k_to_retriever(self) -> None:
        """query_for_context(top_k=N) must forward N to retriever.retrieve."""
        retriever = _fake_retriever(chunks=[])
        svc = _make_service(retriever=retriever)
        svc.query_for_context("question", top_k=9)
        call_args = retriever.retrieve.call_args
        all_values = list(call_args.args) + list(call_args.kwargs.values())
        assert 9 in all_values, (
            f"top_k=9 not found in retriever.retrieve call; got: {call_args}"
        )

    def test_query_for_context_forwards_scopes_to_retriever(self) -> None:
        """query_for_context() must forward self._scopes to retriever.retrieve."""
        retriever = _fake_retriever(chunks=[])
        svc = _make_service(retriever=retriever, scopes=["scope-x", "scope-y"])
        svc.query_for_context("question")
        call_args = retriever.retrieve.call_args
        all_values = list(call_args.args) + list(call_args.kwargs.values())
        assert ["scope-x", "scope-y"] in all_values, (
            f"scopes=['scope-x','scope-y'] not found in retriever.retrieve call; got: {call_args}"
        )


# ---------------------------------------------------------------------------
# Builder-discovered edge cases
# ---------------------------------------------------------------------------


class TestBuilderDiscovered:

    def test_search_chunks_no_retriever_with_scopes_passes_scopes_to_vector_store(self) -> None:
        """_search_chunks without retriever should forward scopes to search_similar."""
        svc = _make_service(scopes=["global"])
        svc._search_chunks("q", 5)
        call_kwargs = svc._vectors.search_similar.call_args.kwargs
        assert call_kwargs.get("scopes") == ["global"], (
            f"scopes not forwarded to search_similar: {call_kwargs}"
        )

    def test_search_chunks_no_retriever_empty_embeddings_returns_empty_list(self) -> None:
        """_search_chunks returns [] when embedder provides no vectors."""
        svc = _make_service()
        svc._embedder.embed.return_value = []
        result = svc._search_chunks("q", 5)
        assert result == []

    def test_query_for_context_returns_none_when_no_retriever(self) -> None:
        """query_for_context returns None immediately when retriever is not set."""
        svc = _make_service(retriever=None)
        assert svc.query_for_context("question") is None

    def test_query_for_context_formats_output_correctly(self) -> None:
        """query_for_context returns 'Relevant knowledge:\\n\\n- title: content' format."""
        retriever = _fake_retriever()
        svc = _make_service(retriever=retriever)
        result = svc.query_for_context("q")
        assert result is not None
        assert result.startswith("Relevant knowledge:\n\n")
        assert "- Title:" in result

    def test_query_for_context_truncates_output_to_max_tokens(self) -> None:
        """query_for_context truncates output to max_tokens words when exceeded."""
        retriever = _fake_retriever()
        svc = _make_service(retriever=retriever)
        result = svc.query_for_context("q", max_tokens=5)
        assert result is not None
        assert len(result.split()) == 5

    def test_query_for_context_returns_none_when_all_docs_unresolvable(self) -> None:
        """query_for_context returns None when all chunks map to missing documents."""
        retriever = _fake_retriever()
        svc = _make_service(retriever=retriever)
        svc._graph.get_document.return_value = None
        result = svc.query_for_context("q")
        assert result is None

    @pytest.mark.asyncio(loop_scope="function")
    async def test_query_returns_empty_list_when_retriever_returns_no_chunks(self) -> None:
        """query() returns [] when the retriever returns an empty chunks list."""
        retriever = _fake_retriever(chunks=[])
        svc = _make_service(retriever=retriever)
        result = await svc.query("q")
        assert result == []
