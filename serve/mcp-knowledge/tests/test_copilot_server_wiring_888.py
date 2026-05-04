"""Replacement tests for server.py after copilot_auth removal (task #1317).

Replaces the 5 copilot-fallback assertions removed when #1318 deleted the
copilot_auth fallback path.  New tests cover the API-key path (complementary
to test_server_1317.py which covers the no-API-key path).

AC4 of task #1317: existing tests replaced with tests reflecting removed auth flow.
"""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_mcp_knowledge.server import app_lifespan


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_llm_mod(llm_cls: MagicMock | None = None) -> ModuleType:
    """Return a fake owlbear_knowledge.llm_extractor module."""
    mod = ModuleType("owlbear_knowledge.llm_extractor")
    mod.LLMExtractor = llm_cls or MagicMock(name="LLMExtractorCls")  # type: ignore[attr-defined]
    return mod


# ---------------------------------------------------------------------------
# Fixture: patches all I/O-heavy constructors so app_lifespan runs in-memory
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def mock_lifespan_deps():
    """Patch heavy dependencies so app_lifespan can run without real DB/network."""
    with (
        patch("owlbear_mcp_knowledge.server.init_db", return_value=MagicMock()),
        patch("owlbear_mcp_knowledge.server.GraphStore"),
        patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
        patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
        patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
        patch("owlbear_mcp_knowledge.server.GraphAugmentedRetriever"),
        patch(
            "owlbear_mcp_knowledge.server.make_evaluate_fn", return_value=AsyncMock()
        ),
    ):
        yield


# ---------------------------------------------------------------------------
# TestFromAC_ApiKeyPath
# Replacement for removed CopilotServerFallback — tests the API-key wiring path
# ---------------------------------------------------------------------------


class TestFromAC_ApiKeyPath:
    """Replacement: OWLBEAR_LLM_API_KEY path wires LLMExtractor (no copilot fallback)."""

    @pytest.mark.asyncio
    async def test_llm_extractor_created_when_api_key_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """structured_extractor is not None when OWLBEAR_LLM_API_KEY is set."""
        monkeypatch.setenv("OWLBEAR_LLM_API_KEY", "sk-test-key")

        mock_llm_cls = MagicMock(name="LLMExtractorCls", return_value=MagicMock())
        llm_mod = _make_llm_mod(mock_llm_cls)

        with patch.dict(sys.modules, {"owlbear_knowledge.llm_extractor": llm_mod}):
            async with app_lifespan(MagicMock()) as ctx:
                assert ctx.structured_extractor is not None  # noqa: S101

    @pytest.mark.asyncio
    async def test_llm_extractor_receives_api_key_value(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """LLMExtractor is constructed with the api_key from OWLBEAR_LLM_API_KEY."""
        monkeypatch.setenv("OWLBEAR_LLM_API_KEY", "sk-expected-key")

        mock_llm_cls = MagicMock(name="LLMExtractorCls", return_value=MagicMock())
        llm_mod = _make_llm_mod(mock_llm_cls)

        with patch.dict(sys.modules, {"owlbear_knowledge.llm_extractor": llm_mod}):
            async with app_lifespan(MagicMock()):
                pass

        mock_llm_cls.assert_called_once()
        _, kwargs = mock_llm_cls.call_args
        assert kwargs.get("api_key") == "sk-expected-key"  # noqa: S101

    @pytest.mark.asyncio
    async def test_structured_extractor_none_when_llm_import_fails(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """structured_extractor is None when LLMExtractor import raises (graceful degradation)."""
        monkeypatch.setenv("OWLBEAR_LLM_API_KEY", "sk-test-key")

        # Blocking import via None sentinel in sys.modules raises ImportError on 'from ... import'
        with patch.dict(sys.modules, {"owlbear_knowledge.llm_extractor": None}):
            async with app_lifespan(MagicMock()) as ctx:
                assert ctx.structured_extractor is None  # noqa: S101
