"""Tests for owlbear.memory.knowledge.reranker — RerankerProvider protocol and BGE adapter.

TDD tests for tasks #191 (tests) and #179 (implementation).
Covers: protocol shape, lazy loading, reranking order.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from owlbear.memory.knowledge.reranker import (
    BGERerankerProvider,
    RerankerProvider,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_flag_module():
    """Inject a mock FlagEmbedding module into sys.modules.

    FlagEmbedding is an optional dependency not installed in the test
    environment, so we mock the entire module.
    """
    mock_module = MagicMock()
    with patch.dict(sys.modules, {"FlagEmbedding": mock_module}):
        yield mock_module


# ---------------------------------------------------------------------------
# (1) RerankerProvider protocol
# ---------------------------------------------------------------------------


class TestRerankerProvider:
    """RerankerProvider is a runtime-checkable Protocol with rerank()."""

    def test_protocol_is_runtime_checkable(self) -> None:
        """isinstance() works on RerankerProvider (runtime_checkable)."""
        assert isinstance(BGERerankerProvider(), RerankerProvider)

    def test_protocol_defines_rerank_method(self) -> None:
        """Protocol has a 'rerank' callable attribute."""
        assert hasattr(RerankerProvider, "rerank")

    def test_non_conforming_class_fails_isinstance(self) -> None:
        """An object without rerank() is not a RerankerProvider."""

        class NotAProvider:
            pass

        assert not isinstance(NotAProvider(), RerankerProvider)


# ---------------------------------------------------------------------------
# (2) BGERerankerProvider satisfies the RerankerProvider protocol
# ---------------------------------------------------------------------------


class TestBGERerankerProviderProtocol:
    """BGERerankerProvider satisfies the RerankerProvider protocol."""

    def test_isinstance_check(self) -> None:
        assert isinstance(BGERerankerProvider(), RerankerProvider)

    def test_has_rerank_method(self) -> None:
        provider = BGERerankerProvider()
        assert callable(getattr(provider, "rerank", None))


# ---------------------------------------------------------------------------
# (3) BGERerankerProvider lazily loads model on first rerank() call
# ---------------------------------------------------------------------------


class TestBGERerankerProviderLazyLoad:
    """BGERerankerProvider lazily loads model on first rerank() call."""

    def test_no_import_on_construction(self, mock_flag_module: MagicMock) -> None:
        """Creating BGERerankerProvider does NOT instantiate FlagReranker."""
        BGERerankerProvider()
        mock_flag_module.FlagReranker.assert_not_called()

    def test_model_created_on_first_rerank(self, mock_flag_module: MagicMock) -> None:
        """FlagReranker is created on the first rerank() call."""
        mock_instance = MagicMock()
        mock_instance.compute_score.return_value = [0.9, 0.5]
        mock_flag_module.FlagReranker.return_value = mock_instance

        provider = BGERerankerProvider()
        mock_flag_module.FlagReranker.assert_not_called()

        provider.rerank("query", ["passage1", "passage2"])
        mock_flag_module.FlagReranker.assert_called_once()

    def test_model_reused_on_subsequent_calls(self, mock_flag_module: MagicMock) -> None:
        """FlagReranker is created once, then reused."""
        mock_instance = MagicMock()
        mock_instance.compute_score.return_value = [0.9]
        mock_flag_module.FlagReranker.return_value = mock_instance

        provider = BGERerankerProvider()
        provider.rerank("q", ["p1"])
        mock_instance.compute_score.return_value = [0.8]
        provider.rerank("q", ["p2"])

        mock_flag_module.FlagReranker.assert_called_once()  # only one instantiation


# ---------------------------------------------------------------------------
# (4) rerank() returns (index, score) pairs sorted by score descending
# ---------------------------------------------------------------------------


class TestBGERerankerProviderRerank:
    """rerank() returns (index, score) pairs sorted by score descending."""

    def test_returns_sorted_descending(self, mock_flag_module: MagicMock) -> None:
        """Pairs are sorted by score in descending order."""
        mock_instance = MagicMock()
        # Passage 0 → 0.3, passage 1 → 0.9, passage 2 → 0.1
        mock_instance.compute_score.return_value = [0.3, 0.9, 0.1]
        mock_flag_module.FlagReranker.return_value = mock_instance

        provider = BGERerankerProvider()
        result = provider.rerank("query", ["p0", "p1", "p2"])

        assert result == [(1, 0.9), (0, 0.3), (2, 0.1)]

    def test_single_passage_returns_single_pair(self, mock_flag_module: MagicMock) -> None:
        """FlagReranker returns a bare float for a single pair."""
        mock_instance = MagicMock()
        mock_instance.compute_score.return_value = 0.75  # bare float
        mock_flag_module.FlagReranker.return_value = mock_instance

        provider = BGERerankerProvider()
        result = provider.rerank("query", ["only passage"])

        assert result == [(0, 0.75)]

    def test_passes_correct_pairs_to_model(self, mock_flag_module: MagicMock) -> None:
        """rerank() sends [[query, passage], ...] pairs to compute_score."""
        mock_instance = MagicMock()
        mock_instance.compute_score.return_value = [0.5, 0.7]
        mock_flag_module.FlagReranker.return_value = mock_instance

        provider = BGERerankerProvider()
        provider.rerank("my query", ["passage A", "passage B"])

        mock_instance.compute_score.assert_called_once_with(
            [["my query", "passage A"], ["my query", "passage B"]]
        )


# ---------------------------------------------------------------------------
# (5) Empty passages returns empty list
# ---------------------------------------------------------------------------


class TestRerankerEmptyPassages:
    """Empty passages input returns empty list."""

    def test_bge_empty_passages(self, mock_flag_module: MagicMock) -> None:
        """BGERerankerProvider.rerank with empty passages returns []."""
        provider = BGERerankerProvider()
        result = provider.rerank("query", [])
        assert result == []
        # Model should NOT be loaded for empty input
        mock_flag_module.FlagReranker.assert_not_called()


# ---------------------------------------------------------------------------
# (6) Import guard — actionable ImportError when FlagEmbedding missing
# ---------------------------------------------------------------------------


class TestRerankerImportGuard:
    """_ensure_model() raises ImportError with install instructions when FlagEmbedding missing."""

    def test_import_error_message_when_flag_embedding_missing(self) -> None:
        """ImportError message includes class name and install command."""
        with patch.dict(sys.modules, {"FlagEmbedding": None}):
            provider = BGERerankerProvider()
            with pytest.raises(ImportError, match="BGERerankerProvider"):
                provider.rerank("query", ["passage"])

    def test_import_error_message_includes_install_instructions(self) -> None:
        """ImportError message tells user how to install the package."""
        with patch.dict(sys.modules, {"FlagEmbedding": None}):
            provider = BGERerankerProvider()
            with pytest.raises(ImportError, match="uv pip install FlagEmbedding"):
                provider.rerank("query", ["passage"])
