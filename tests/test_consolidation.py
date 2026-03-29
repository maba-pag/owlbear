"""RED-phase tests for ConsolidationService and ConsolidationInsight (#138).

Covers:
  - ConsolidationService instantiation (TestFromAC_ConsolidationService)
  - ConsolidationInsight model validation (TestFromAC_ConsolidationInsight)

All tests fail in RED phase — modules not implemented yet.
"""

from __future__ import annotations

import sqlite3

import pytest
from pydantic import ValidationError

from owlbear_knowledge.consolidation import ConsolidationInsight, ConsolidationService


# ---------------------------------------------------------------------------
# TestFromAC_ConsolidationService
# ---------------------------------------------------------------------------


class TestFromAC_ConsolidationService:  # noqa: N801
    """AC: ConsolidationService instantiation and consolidate() contract."""

    def test_instantiates_with_sqlite_connection(self) -> None:
        """ConsolidationService(conn) accepts a sqlite3.Connection."""
        conn = sqlite3.connect(":memory:")
        svc = ConsolidationService(conn)
        assert svc is not None

    def test_accepts_optional_graph_store_param(self) -> None:
        """ConsolidationService(conn, graph_store=...) accepts a graph_store kwarg."""
        conn = sqlite3.connect(":memory:")
        mock_store = object()
        svc = ConsolidationService(conn, graph_store=mock_store)
        assert svc is not None

    def test_accepts_optional_model_param(self) -> None:
        """ConsolidationService(conn, model=...) accepts a model kwarg."""
        conn = sqlite3.connect(":memory:")
        svc = ConsolidationService(conn, model="gpt-4o")
        assert svc is not None

    @pytest.mark.asyncio(loop_scope="function")
    async def test_consolidate_returns_zero_when_no_chunks(self) -> None:
        """await consolidate(batch_size=50) returns 0 when no unconsolidated chunks exist."""
        conn = sqlite3.connect(":memory:")
        svc = ConsolidationService(conn)
        result = await svc.consolidate(batch_size=50)
        assert result == 0

    @pytest.mark.asyncio(loop_scope="function")
    async def test_consolidate_uses_default_batch_size(self) -> None:
        """consolidate() can be called with no args (batch_size has a default)."""
        conn = sqlite3.connect(":memory:")
        svc = ConsolidationService(conn)
        result = await svc.consolidate()
        assert isinstance(result, int)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_consolidate_returns_int(self) -> None:
        """consolidate(batch_size=50) return value is an int (consolidated count)."""
        conn = sqlite3.connect(":memory:")
        svc = ConsolidationService(conn)
        result = await svc.consolidate(batch_size=50)
        assert isinstance(result, int)


# ---------------------------------------------------------------------------
# TestFromAC_ConsolidationInsight
# ---------------------------------------------------------------------------


class TestFromAC_ConsolidationInsight:  # noqa: N801
    """AC: ConsolidationInsight model validation and frozen constraint."""

    def test_instantiates_with_required_fields(self) -> None:
        """ConsolidationInsight validates all required fields when provided."""
        insight = ConsolidationInsight(
            id="ins-1",
            source_ids=["src-1", "src-2"],
            insight="Entities share common scope",
            created_at="2026-03-29T00:00:00Z",
        )
        assert insight.id == "ins-1"
        assert insight.source_ids == ["src-1", "src-2"]
        assert insight.insight == "Entities share common scope"
        assert insight.created_at == "2026-03-29T00:00:00Z"

    def test_id_field_is_required(self) -> None:
        """Missing id field raises ValidationError."""
        with pytest.raises(ValidationError):
            ConsolidationInsight(
                source_ids=["src-1"],
                insight="some insight",
                created_at="2026-01-01",
            )

    def test_source_ids_field_is_required(self) -> None:
        """Missing source_ids field raises ValidationError."""
        with pytest.raises(ValidationError):
            ConsolidationInsight(
                id="ins-1",
                insight="some insight",
                created_at="2026-01-01",
            )

    def test_insight_field_is_required(self) -> None:
        """Missing insight field raises ValidationError."""
        with pytest.raises(ValidationError):
            ConsolidationInsight(
                id="ins-1",
                source_ids=["src-1"],
                created_at="2026-01-01",
            )

    def test_created_at_field_is_required(self) -> None:
        """Missing created_at field raises ValidationError."""
        with pytest.raises(ValidationError):
            ConsolidationInsight(
                id="ins-1",
                source_ids=["src-1"],
                insight="some insight",
            )

    def test_source_ids_is_list_of_str(self) -> None:
        """source_ids accepts a list of strings."""
        insight = ConsolidationInsight(
            id="ins-1",
            source_ids=["a", "b", "c"],
            insight="multi-source",
            created_at="2026-03-29",
        )
        assert isinstance(insight.source_ids, list)
        assert all(isinstance(s, str) for s in insight.source_ids)

    def test_is_frozen_cannot_mutate_id(self) -> None:
        """ConsolidationInsight is frozen — mutating id raises an error."""
        insight = ConsolidationInsight(
            id="ins-1",
            source_ids=["src-1"],
            insight="immutable",
            created_at="2026-03-29",
        )
        with pytest.raises((TypeError, ValidationError)):
            insight.id = "ins-99"  # type: ignore[misc]

    def test_is_frozen_cannot_mutate_insight(self) -> None:
        """ConsolidationInsight is frozen — mutating insight raises an error."""
        insight = ConsolidationInsight(
            id="ins-1",
            source_ids=["src-1"],
            insight="original",
            created_at="2026-03-29",
        )
        with pytest.raises((TypeError, ValidationError)):
            insight.insight = "modified"  # type: ignore[misc]
