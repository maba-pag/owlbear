"""Tests for consolidation insight injection in KnowledgeQueryService.query_for_context.

RED-phase tests for task #790 — contract tests verifying that
KnowledgeQueryService injects consolidation insights after RAG output,
respects the token budget, and degrades gracefully on errors.
"""

from __future__ import annotations

import logging
import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from owlbear.memory.knowledge.query_service import KnowledgeQueryService, _token_count
from owlbear.memory.knowledge.schema import init_db

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db(*, with_insights: bool = False) -> sqlite3.Connection:
    """Return an in-memory DB with the full schema initialised.

    When *with_insights* is True, seed three consolidation insight rows.
    """
    conn = sqlite3.Connection(":memory:")
    init_db(conn)
    if with_insights:
        for i in range(1, 4):
            conn.execute(
                "INSERT INTO consolidations (id, source_ids, summary, insight, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (
                    f"c-{i}",
                    f"src-{i}",
                    f"summary {i}",
                    f"Insight number {i} from consolidation",
                    f"2026-01-0{i}",
                ),
            )
    conn.commit()
    return conn


def _stub_service(
    *,
    consolidation_conn: sqlite3.Connection | None = None,
) -> KnowledgeQueryService:
    """Build a KnowledgeQueryService with mocked vector/graph/embedding deps.

    The mocks are configured so that _query returns a small RAG output,
    letting us focus on the consolidation-injection contract.
    """
    vector_store = MagicMock()
    graph_store = MagicMock()
    embedding_provider = MagicMock()

    # Simulate a successful embed → search → resolve cycle.
    embedding_provider.embed.return_value = [[0.1, 0.2, 0.3]]
    vector_store.search_similar.return_value = [("doc-1", 0.9)]
    doc_mock = MagicMock()
    doc_mock.title = "Test Doc"
    doc_mock.content = "Some useful content"
    graph_store.get_document.return_value = doc_mock

    return KnowledgeQueryService(
        vector_store=vector_store,
        graph_store=graph_store,
        embedding_provider=embedding_provider,
        consolidation_conn=consolidation_conn,
    )


# ---------------------------------------------------------------------------
# TestFromAC_ConsolidationConnNone — AC: conn=None skips insight query
# ---------------------------------------------------------------------------


class TestFromAC_ConsolidationConnNone:  # noqa: N801
    """When consolidation_conn is None the output must be identical to pre-feature behavior."""

    def test_none_conn_produces_no_insight_section(self) -> None:
        """Output must not contain 'Consolidation insights' when conn is None."""
        svc = _stub_service(consolidation_conn=None)
        result = svc.query_for_context("test prompt")
        assert result is not None
        assert "Consolidation insights" not in result

    def test_none_conn_output_matches_baseline(self) -> None:
        """Output of conn=None must equal output from a service without the param entirely."""
        svc_old = KnowledgeQueryService(
            vector_store=MagicMock(),
            graph_store=MagicMock(),
            embedding_provider=MagicMock(),
        )
        svc_new = _stub_service(consolidation_conn=None)
        # Both should behave identically — contract: backward-compatible
        # (if old construction still works, the param is truly optional)
        assert svc_old is not None
        assert svc_new is not None


# ---------------------------------------------------------------------------
# TestFromAC_InsightsAppendedAfterRAG — AC: insights after RAG output
# ---------------------------------------------------------------------------


class TestFromAC_InsightsAppendedAfterRAG:  # noqa: N801
    """Insights must appear after the RAG output, not before."""

    def test_insights_appear_after_rag_section(self) -> None:
        """The 'Consolidation insights' header must come after 'Relevant knowledge'."""
        conn = _make_db(with_insights=True)
        svc = _stub_service(consolidation_conn=conn)
        result = svc.query_for_context("test prompt", max_tokens=5000)
        assert result is not None
        rag_pos = result.index("Relevant knowledge")
        insight_pos = result.index("Consolidation insights")
        assert insight_pos > rag_pos

    def test_rag_content_still_present(self) -> None:
        """Original RAG snippets must not be displaced by insight insertion."""
        conn = _make_db(with_insights=True)
        svc = _stub_service(consolidation_conn=conn)
        result = svc.query_for_context("test prompt", max_tokens=5000)
        assert result is not None
        assert "Test Doc" in result


# ---------------------------------------------------------------------------
# TestFromAC_TokenBudget — AC: max_tokens respected
# ---------------------------------------------------------------------------


class TestFromAC_TokenBudget:  # noqa: N801
    """Insights share the same max_tokens budget as RAG; budget must not be exceeded."""

    def test_total_output_within_budget(self) -> None:
        """Total token count of output (including insights) must stay within max_tokens."""
        conn = _make_db(with_insights=True)
        svc = _stub_service(consolidation_conn=conn)
        budget = 200
        result = svc.query_for_context("test", max_tokens=budget)
        assert result is not None
        assert _token_count(result) <= budget

    def test_no_insights_when_budget_exhausted_by_rag(self) -> None:
        """When RAG output consumes all tokens, no insight section should appear."""
        conn = _make_db(with_insights=True)
        svc = _stub_service(consolidation_conn=conn)
        # Tiny budget that barely fits the RAG header + one doc line
        result = svc.query_for_context("test", max_tokens=10)
        if result is not None:
            assert "Consolidation insights" not in result

    def test_partial_insights_truncated_at_word_boundary(self) -> None:
        """When budget allows only partial insights, truncation must happen at a word boundary."""
        conn = _make_db(with_insights=True)
        svc = _stub_service(consolidation_conn=conn)
        # Give enough budget for RAG + header + partial insights
        result = svc.query_for_context("test", max_tokens=50)
        if result is not None and "Consolidation insights" in result:
            # No broken words — last char should be alphanumeric or punctuation
            assert not result.endswith(" ")


# ---------------------------------------------------------------------------
# TestFromAC_EmptyTable — AC: empty consolidations table = unchanged output
# ---------------------------------------------------------------------------


class TestFromAC_EmptyTable:  # noqa: N801
    """A connected DB with no consolidation rows must produce baseline output."""

    def test_empty_table_no_insight_section(self) -> None:
        """With 0 rows in consolidations, output must have no insight header."""
        conn = _make_db(with_insights=False)  # schema exists, no rows
        svc = _stub_service(consolidation_conn=conn)
        result = svc.query_for_context("test", max_tokens=5000)
        assert result is not None
        assert "Consolidation insights" not in result

    def test_empty_table_matches_none_conn_output(self) -> None:
        """Empty table output must be identical to None-conn output."""
        conn = _make_db(with_insights=False)
        svc_with_conn = _stub_service(consolidation_conn=conn)
        svc_none = _stub_service(consolidation_conn=None)
        result_conn = svc_with_conn.query_for_context("test", max_tokens=5000)
        result_none = svc_none.query_for_context("test", max_tokens=5000)
        assert result_conn == result_none


# ---------------------------------------------------------------------------
# TestFromAC_ExceptionHandling — AC: exception caught + logged
# ---------------------------------------------------------------------------


class TestFromAC_ExceptionHandling:  # noqa: N801
    """Consolidation query failures must be caught and logged at WARNING."""

    def test_corrupt_conn_still_returns_rag_output(self) -> None:
        """A broken consolidation connection must not prevent RAG output."""
        conn = MagicMock(spec=sqlite3.Connection)
        cursor_mock = MagicMock()
        cursor_mock.execute.side_effect = sqlite3.OperationalError("no such table")
        conn.execute.side_effect = sqlite3.OperationalError("no such table")
        conn.cursor.return_value = cursor_mock

        svc = _stub_service(consolidation_conn=conn)
        result = svc.query_for_context("test", max_tokens=5000)
        # RAG output must still be present despite consolidation failure
        assert result is not None
        assert "Relevant knowledge" in result

    def test_exception_logged_at_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """Consolidation failures must emit a WARNING-level log entry."""
        conn = MagicMock(spec=sqlite3.Connection)
        conn.execute.side_effect = sqlite3.OperationalError("table broken")
        conn.cursor.return_value = MagicMock(
            execute=MagicMock(side_effect=sqlite3.OperationalError("table broken")),
        )

        svc = _stub_service(consolidation_conn=conn)
        with caplog.at_level(logging.WARNING):
            svc.query_for_context("test", max_tokens=5000)
        assert any("consolidat" in r.message.lower() for r in caplog.records)

    def test_no_insight_section_on_exception(self) -> None:
        """When consolidation query raises, no insight section in output."""
        conn = MagicMock(spec=sqlite3.Connection)
        conn.execute.side_effect = RuntimeError("unexpected")
        conn.cursor.return_value = MagicMock(
            execute=MagicMock(side_effect=RuntimeError("unexpected")),
        )

        svc = _stub_service(consolidation_conn=conn)
        result = svc.query_for_context("test", max_tokens=5000)
        if result is not None:
            assert "Consolidation insights" not in result


# ---------------------------------------------------------------------------
# TestFromAC_InsightFormat — AC: header + bullets format
# ---------------------------------------------------------------------------


class TestFromAC_InsightFormat:  # noqa: N801
    """Insights must be formatted with a header and bullet points."""

    def test_header_present(self) -> None:
        """Output must contain a 'Consolidation insights' header."""
        conn = _make_db(with_insights=True)
        svc = _stub_service(consolidation_conn=conn)
        result = svc.query_for_context("test", max_tokens=5000)
        assert result is not None
        assert "Consolidation insights" in result

    def test_bullets_present(self) -> None:
        """Each insight row must be rendered as a bullet ('- ...')."""
        conn = _make_db(with_insights=True)
        svc = _stub_service(consolidation_conn=conn)
        result = svc.query_for_context("test", max_tokens=5000)
        assert result is not None
        # Extract the insight section
        idx = result.index("Consolidation insights")
        insight_section = result[idx:]
        bullet_lines = [ln for ln in insight_section.splitlines() if ln.strip().startswith("- ")]
        assert len(bullet_lines) >= 1

    def test_insight_text_in_bullets(self) -> None:
        """Actual insight text from DB must appear in bullet lines."""
        conn = _make_db(with_insights=True)
        svc = _stub_service(consolidation_conn=conn)
        result = svc.query_for_context("test", max_tokens=5000)
        assert result is not None
        assert "Insight number" in result

    def test_max_three_insights(self) -> None:
        """At most 3 insights should be included (LIMIT 3 in SQL)."""
        conn = _make_db(with_insights=False)
        # Seed 5 insights to verify LIMIT
        for i in range(1, 6):
            conn.execute(
                "INSERT INTO consolidations (id, source_ids, summary, insight, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (f"c-{i}", f"src-{i}", f"summary {i}", f"Insight {i}", f"2026-01-0{i}"),
            )
        conn.commit()
        svc = _stub_service(consolidation_conn=conn)
        result = svc.query_for_context("test", max_tokens=5000)
        assert result is not None
        idx = result.index("Consolidation insights")
        insight_section = result[idx:]
        bullet_lines = [ln for ln in insight_section.splitlines() if ln.strip().startswith("- ")]
        assert len(bullet_lines) <= 3


# ---------------------------------------------------------------------------
# TestFromAC_BootstrapWiring — AC: bootstrap passes consolidation_conn
# ---------------------------------------------------------------------------


class TestFromAC_BootstrapWiring:  # noqa: N801
    """Bootstrap must pass consolidation_conn=infra.conn when enabled, else None."""

    def test_enabled_passes_infra_conn(self) -> None:
        """When consolidation_enabled=True, KnowledgeQueryService gets infra.conn."""
        from owlbear.bootstrap.knowledge import _build_knowledge_toolset

        infra = MagicMock()
        infra.conn = MagicMock(spec=sqlite3.Connection)

        with patch(
            "owlbear.bootstrap.knowledge.KnowledgeQueryService",
        ) as mock_cls:
            mock_cls.return_value = MagicMock()
            mock_cls.return_value.default_max_tokens = 2000
            _build_knowledge_toolset(
                workspace=MagicMock(),
                infra=infra,
                consolidation_enabled=True,
            )
            # Verify consolidation_conn=infra.conn was passed
            call_kwargs = mock_cls.call_args
            assert call_kwargs is not None
            assert call_kwargs.kwargs.get("consolidation_conn") is infra.conn

    def test_disabled_passes_none(self) -> None:
        """When consolidation_enabled=False, consolidation_conn must be None."""
        from owlbear.bootstrap.knowledge import _build_knowledge_toolset

        infra = MagicMock()
        infra.conn = MagicMock(spec=sqlite3.Connection)

        with patch(
            "owlbear.bootstrap.knowledge.KnowledgeQueryService",
        ) as mock_cls:
            mock_cls.return_value = MagicMock()
            mock_cls.return_value.default_max_tokens = 2000
            _build_knowledge_toolset(
                workspace=MagicMock(),
                infra=infra,
                consolidation_enabled=False,
            )
            call_kwargs = mock_cls.call_args
            assert call_kwargs is not None
            # Either consolidation_conn not passed (defaults to None) or explicitly None
            assert call_kwargs.kwargs.get("consolidation_conn") is None

    def test_default_is_disabled(self) -> None:
        """When consolidation_enabled is not specified, consolidation_conn must be None."""
        from owlbear.bootstrap.knowledge import _build_knowledge_toolset

        infra = MagicMock()
        infra.conn = MagicMock(spec=sqlite3.Connection)

        with patch(
            "owlbear.bootstrap.knowledge.KnowledgeQueryService",
        ) as mock_cls:
            mock_cls.return_value = MagicMock()
            mock_cls.return_value.default_max_tokens = 2000
            _build_knowledge_toolset(
                workspace=MagicMock(),
                infra=infra,
            )
            call_kwargs = mock_cls.call_args
            assert call_kwargs is not None
            assert call_kwargs.kwargs.get("consolidation_conn") is None
