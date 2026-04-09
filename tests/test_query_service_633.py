"""Tests for per-query scopes override in KnowledgeQueryService --- task #633.

AC coverage:
- AC1: query() accepts optional scopes: list[str] | None = None parameter
- AC2: _search_chunks() accepts optional scopes: list[str] | None = None parameter
- AC3: When scopes is provided, it overrides self._scopes for that call
- AC4: When scopes is None (default), self._scopes is used (existing behaviour preserved)
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from owlbear_knowledge.query_service import KnowledgeQueryService
from owlbear_knowledge.retrieval import RetrievalResult


def _make_graph() -> MagicMock:
    graph = MagicMock()
    graph.get_document_id_for_chunk.return_value = "doc1"
    graph.get_document.return_value = MagicMock(title="Title", content="content " * 50, scope="global")
    graph.list_entities_for_document.return_value = []
    return graph


def _make_vector_store(chunks=None) -> MagicMock:
    vs = MagicMock()
    vs.search_similar.return_value = chunks if chunks is not None else [("doc1", 0.8)]
    return vs


def _make_embedder() -> MagicMock:
    embedder = MagicMock()
    embedder.embed.return_value = [[0.1] * 10]
    return embedder


def _make_service(
    *,
    retriever=None,
    scopes=None,
    threshold=0.0,
    vector_store=None,
) -> KnowledgeQueryService:
    vs = vector_store if vector_store is not None else _make_vector_store()
    return KnowledgeQueryService(
        vector_store=vs,
        graph_store=_make_graph(),
        embedding_provider=_make_embedder(),
        scopes=scopes,
        similarity_threshold=threshold,
        retriever=retriever,
    )


def _fake_retriever(chunks=None) -> MagicMock:
    retriever = MagicMock()
    retriever.retrieve.return_value = RetrievalResult(
        chunks=chunks if chunks is not None else [("doc1", 0.9)],
        expansion_text="",
        entities_found=0,
    )
    return retriever


class TestFromAC_PerQueryScopesOverride:
    @pytest.mark.asyncio(loop_scope="function")
    async def test_query_accepts_scopes_kwarg_without_raising(self) -> None:
        """AC1: query() must accept a scopes keyword argument without TypeError."""
        svc = _make_service()
        result = await svc.query("test prompt", scopes=["scope-a"])
        assert isinstance(result, list)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_query_accepts_explicit_none_scopes(self) -> None:
        """AC1: query(scopes=None) must be accepted as a valid keyword-only call."""
        svc = _make_service(scopes=["instance-scope"])
        result = await svc.query("test prompt", scopes=None)
        assert isinstance(result, list)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_query_accepts_empty_list_scopes(self) -> None:
        """AC1: query(scopes=[]) must be accepted as a valid call."""
        svc = _make_service()
        result = await svc.query("test prompt", scopes=[])
        assert isinstance(result, list)

    def test_search_chunks_accepts_scopes_kwarg_without_raising(self) -> None:
        """AC2: _search_chunks() must accept a scopes keyword argument without TypeError."""
        svc = _make_service()
        result = svc._search_chunks("test prompt", 5, scopes=["scope-a"])
        assert isinstance(result, list)

    def test_search_chunks_accepts_explicit_none_scopes(self) -> None:
        """AC2: _search_chunks(scopes=None) must be accepted without TypeError."""
        svc = _make_service(scopes=["instance-scope"])
        result = svc._search_chunks("test prompt", 5, scopes=None)
        assert isinstance(result, list)

    def test_search_chunks_accepts_empty_list_scopes(self) -> None:
        """AC2: _search_chunks(scopes=[]) must be accepted as a valid call."""
        svc = _make_service()
        result = svc._search_chunks("test prompt", 5, scopes=[])
        assert isinstance(result, list)

    def test_search_chunks_override_scopes_forwarded_to_vector_store(self) -> None:
        """AC3: _search_chunks(scopes=["override"]) passes override (not self._scopes) to search_similar."""
        vs = _make_vector_store()
        svc = _make_service(scopes=["instance-scope"], vector_store=vs)
        svc._search_chunks("q", 5, scopes=["override"])
        call_kwargs = vs.search_similar.call_args.kwargs
        assert call_kwargs.get("scopes") == ["override"], (
            f"Expected override scopes to reach search_similar, got: {call_kwargs}"
        )

    def test_search_chunks_override_does_not_use_instance_scopes_vector(self) -> None:
        """AC3: Instance scopes must not reach search_similar when override is provided."""
        vs = _make_vector_store()
        svc = _make_service(scopes=["instance-scope"], vector_store=vs)
        svc._search_chunks("q", 5, scopes=["override"])
        call_kwargs = vs.search_similar.call_args.kwargs
        assert call_kwargs.get("scopes") != ["instance-scope"], (
            "Instance scopes must not be forwarded when override is provided"
        )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_query_override_scopes_forwarded_to_vector_store(self) -> None:
        """AC3: query(scopes=["override"]) forwards override to search_similar."""
        vs = _make_vector_store()
        svc = _make_service(scopes=["instance-scope"], vector_store=vs)
        await svc.query("q", scopes=["override"])
        call_kwargs = vs.search_similar.call_args.kwargs
        assert call_kwargs.get("scopes") == ["override"], (
            f"Expected override scopes to reach search_similar, got: {call_kwargs}"
        )

    def test_search_chunks_override_scopes_forwarded_to_retriever(self) -> None:
        """AC3: _search_chunks(scopes=["override"]) passes override scopes to retriever.retrieve."""
        retriever = _fake_retriever()
        svc = _make_service(retriever=retriever, scopes=["instance-scope"])
        svc._search_chunks("q", 5, scopes=["override"])
        call_args = retriever.retrieve.call_args
        all_values = list(call_args.args) + list(call_args.kwargs.values())
        assert ["override"] in all_values, f"Override scopes not found in retriever.retrieve call: {call_args}"

    def test_search_chunks_override_does_not_use_instance_scopes_retriever(self) -> None:
        """AC3: Instance scopes must not reach retriever.retrieve when override is provided."""
        retriever = _fake_retriever()
        svc = _make_service(retriever=retriever, scopes=["instance-scope"])
        svc._search_chunks("q", 5, scopes=["override"])
        call_args = retriever.retrieve.call_args
        all_values = list(call_args.args) + list(call_args.kwargs.values())
        assert ["instance-scope"] not in all_values, "Instance scopes must not be forwarded when override is provided"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_query_override_scopes_forwarded_to_retriever(self) -> None:
        """AC3: query(scopes=["override"]) forwards override scopes to retriever.retrieve."""
        retriever = _fake_retriever()
        svc = _make_service(retriever=retriever, scopes=["instance-scope"])
        await svc.query("q", scopes=["override"])
        call_args = retriever.retrieve.call_args
        all_values = list(call_args.args) + list(call_args.kwargs.values())
        assert ["override"] in all_values, f"Override scopes not in retriever.retrieve: {call_args}"

    def test_search_chunks_none_scopes_uses_instance_scopes_vector(self) -> None:
        """AC4: _search_chunks(scopes=None) falls back to self._scopes for search_similar."""
        vs = _make_vector_store()
        svc = _make_service(scopes=["instance-scope"], vector_store=vs)
        svc._search_chunks("q", 5, scopes=None)
        call_kwargs = vs.search_similar.call_args.kwargs
        assert call_kwargs.get("scopes") == ["instance-scope"], (
            f"Expected self._scopes when scopes=None, got: {call_kwargs}"
        )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_query_none_scopes_uses_instance_scopes_vector(self) -> None:
        """AC4: query(scopes=None) falls back to self._scopes for search_similar."""
        vs = _make_vector_store()
        svc = _make_service(scopes=["instance-scope"], vector_store=vs)
        await svc.query("q", scopes=None)
        call_kwargs = vs.search_similar.call_args.kwargs
        assert call_kwargs.get("scopes") == ["instance-scope"], (
            f"Expected self._scopes when scopes=None in query(), got: {call_kwargs}"
        )

    def test_search_chunks_none_scopes_uses_instance_scopes_retriever(self) -> None:
        """AC4: _search_chunks(scopes=None) falls back to self._scopes for retriever.retrieve."""
        retriever = _fake_retriever()
        svc = _make_service(retriever=retriever, scopes=["instance-scope"])
        svc._search_chunks("q", 5, scopes=None)
        call_args = retriever.retrieve.call_args
        all_values = list(call_args.args) + list(call_args.kwargs.values())
        assert ["instance-scope"] in all_values, f"self._scopes not in retriever.retrieve when scopes=None: {call_args}"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_query_none_scopes_uses_instance_scopes_retriever(self) -> None:
        """AC4: query(scopes=None) falls back to self._scopes for retriever.retrieve."""
        retriever = _fake_retriever()
        svc = _make_service(retriever=retriever, scopes=["instance-scope"])
        await svc.query("q", scopes=None)
        call_args = retriever.retrieve.call_args
        all_values = list(call_args.args) + list(call_args.kwargs.values())
        assert ["instance-scope"] in all_values, (
            f"self._scopes not forwarded to retriever when query(scopes=None): {call_args}"
        )

    def test_search_chunks_empty_list_override_is_not_instance_scopes(self) -> None:
        """Boundary: scopes=[] is distinct from None and must not fall back to self._scopes."""
        vs = _make_vector_store()
        svc = _make_service(scopes=["instance-scope"], vector_store=vs)
        svc._search_chunks("q", 5, scopes=[])
        call_kwargs = vs.search_similar.call_args.kwargs
        assert call_kwargs.get("scopes") != ["instance-scope"], (
            "Empty-list override should not fall back to self._scopes"
        )
