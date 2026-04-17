"""Tests: LLMExtractor conditional wiring into MCP knowledge server — task #876.

TDD RED phase — all tests must FAIL before builder implements server.py changes.

AC coverage:
  AC1: server.py conditionally instantiates LLMExtractor when openai importable AND key set
  AC2: env vars OWLBEAR_LLM_API_KEY (→ OPENAI_API_KEY fallback), OWLBEAR_LLM_MODEL
       (default gpt-4o-mini), OWLBEAR_LLM_BASE_URL (→ OPENAI_BASE_URL fallback)
  AC3: falls back to EntityExtractor(extractor=None) when openai not installed or no key
  AC4: IntraDocGraphBuilder always instantiated with extractor=structured_extractor
  AC5: InterDocGraphBuilder instantiated only when structured_extractor is not None, else None
  AC6: AppContext gains structured_extractor, intra_doc_builder, inter_doc_builder fields
  AC7: no ImportError when openai is not installed (lazy import via try/except)
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


def _make_llm_mod(llm_cls: MagicMock) -> ModuleType:
    """Return a fake owlbear_knowledge.llm_extractor module containing a mock LLMExtractor."""
    mod = ModuleType("owlbear_knowledge.llm_extractor")
    mod.LLMExtractor = llm_cls  # type: ignore[attr-defined]
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
        patch("owlbear_mcp_knowledge.server.make_evaluate_fn", return_value=AsyncMock()),
    ):
        yield


# ---------------------------------------------------------------------------
# TestFromAC_LLMExtractorConditionalInstantiation
# AC1, AC2, AC3, AC7
# ---------------------------------------------------------------------------


class TestFromAC_LLMExtractorConditionalInstantiation:
    """app_lifespan conditionally creates LLMExtractor based on import availability and env vars."""

    @pytest.mark.asyncio
    async def test_llm_extractor_created_when_owlbear_api_key_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """LLMExtractor is instantiated when OWLBEAR_LLM_API_KEY is set. (AC1)"""
        monkeypatch.setenv("OWLBEAR_LLM_API_KEY", "sk-owlbear-test")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        mock_llm_cls = MagicMock(name="LLMExtractorCls")
        with patch.dict(sys.modules, {"owlbear_knowledge.llm_extractor": _make_llm_mod(mock_llm_cls)}):
            async with app_lifespan(MagicMock()):
                pass
        mock_llm_cls.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_extractor_created_when_openai_api_key_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """LLMExtractor is created when OPENAI_API_KEY is set as fallback (AC2 — hybrid env)"""
        monkeypatch.delenv("OWLBEAR_LLM_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-fallback")
        mock_llm_cls = MagicMock(name="LLMExtractorCls")
        with patch.dict(sys.modules, {"owlbear_knowledge.llm_extractor": _make_llm_mod(mock_llm_cls)}):
            async with app_lifespan(MagicMock()):
                pass
        mock_llm_cls.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_extractor_receives_default_model_gpt4o_mini(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """LLMExtractor receives model='gpt-4o-mini' when OWLBEAR_LLM_MODEL is absent. (AC2)"""
        monkeypatch.setenv("OWLBEAR_LLM_API_KEY", "sk-test")
        monkeypatch.delenv("OWLBEAR_LLM_MODEL", raising=False)
        mock_llm_cls = MagicMock(name="LLMExtractorCls")
        with patch.dict(sys.modules, {"owlbear_knowledge.llm_extractor": _make_llm_mod(mock_llm_cls)}):
            async with app_lifespan(MagicMock()):
                pass
        mock_llm_cls.assert_called_once()
        _, kwargs = mock_llm_cls.call_args
        assert kwargs.get("model") == "gpt-4o-mini", "Default model must be gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_llm_extractor_receives_custom_model_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """LLMExtractor receives the model name from OWLBEAR_LLM_MODEL. (AC2)"""
        monkeypatch.setenv("OWLBEAR_LLM_API_KEY", "sk-test")
        monkeypatch.setenv("OWLBEAR_LLM_MODEL", "gpt-4-turbo")
        mock_llm_cls = MagicMock(name="LLMExtractorCls")
        with patch.dict(sys.modules, {"owlbear_knowledge.llm_extractor": _make_llm_mod(mock_llm_cls)}):
            async with app_lifespan(MagicMock()):
                pass
        mock_llm_cls.assert_called_once()
        _, kwargs = mock_llm_cls.call_args
        assert kwargs.get("model") == "gpt-4-turbo"

    @pytest.mark.asyncio
    async def test_llm_extractor_receives_owlbear_base_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_LLM_BASE_URL is forwarded to LLMExtractor. (AC2)"""
        monkeypatch.setenv("OWLBEAR_LLM_API_KEY", "sk-test")
        monkeypatch.setenv("OWLBEAR_LLM_BASE_URL", "https://custom.example.com/v1")
        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
        mock_llm_cls = MagicMock(name="LLMExtractorCls")
        with patch.dict(sys.modules, {"owlbear_knowledge.llm_extractor": _make_llm_mod(mock_llm_cls)}):
            async with app_lifespan(MagicMock()):
                pass
        mock_llm_cls.assert_called_once()
        _, kwargs = mock_llm_cls.call_args
        assert kwargs.get("base_url") == "https://custom.example.com/v1"

    @pytest.mark.asyncio
    async def test_llm_extractor_receives_openai_base_url_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Falls back to OPENAI_BASE_URL when OWLBEAR_LLM_BASE_URL is absent. (AC2)"""
        monkeypatch.setenv("OWLBEAR_LLM_API_KEY", "sk-test")
        monkeypatch.delenv("OWLBEAR_LLM_BASE_URL", raising=False)
        monkeypatch.setenv("OPENAI_BASE_URL", "https://proxy.example.com/v1")
        mock_llm_cls = MagicMock(name="LLMExtractorCls")
        with patch.dict(sys.modules, {"owlbear_knowledge.llm_extractor": _make_llm_mod(mock_llm_cls)}):
            async with app_lifespan(MagicMock()):
                pass
        mock_llm_cls.assert_called_once()
        _, kwargs = mock_llm_cls.call_args
        assert kwargs.get("base_url") == "https://proxy.example.com/v1"

    @pytest.mark.asyncio
    async def test_no_import_error_and_structured_extractor_none_when_openai_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """app_lifespan silences ImportError; ctx.structured_extractor is None. (AC7, AC3, AC6)"""
        monkeypatch.delenv("OWLBEAR_LLM_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with patch.dict(sys.modules, {"owlbear_knowledge.llm_extractor": None}):
            # Must not raise ImportError — and AppContext must expose structured_extractor
            async with app_lifespan(MagicMock()) as ctx:
                assert ctx.structured_extractor is None  # noqa: S101

    @pytest.mark.asyncio
    async def test_entity_extractor_called_with_extractor_none_when_openai_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """EntityExtractor(extractor=None) when openai import fails. (AC3)"""
        monkeypatch.delenv("OWLBEAR_LLM_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        mock_entity_cls = MagicMock(name="EntityExtractorCls")
        with (
            patch.dict(sys.modules, {"owlbear_knowledge.llm_extractor": None}),
            patch("owlbear_mcp_knowledge.server.EntityExtractor", mock_entity_cls),
        ):
            async with app_lifespan(MagicMock()):
                pass
        mock_entity_cls.assert_called_once_with(extractor=None)

    @pytest.mark.asyncio
    async def test_entity_extractor_called_with_extractor_none_when_no_api_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """EntityExtractor(extractor=None) when openai is importable but no key is set. (AC3)"""
        monkeypatch.delenv("OWLBEAR_LLM_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        mock_llm_cls = MagicMock(name="LLMExtractorCls")
        mock_entity_cls = MagicMock(name="EntityExtractorCls")
        with (
            patch.dict(sys.modules, {"owlbear_knowledge.llm_extractor": _make_llm_mod(mock_llm_cls)}),
            patch("owlbear_mcp_knowledge.server.EntityExtractor", mock_entity_cls),
            patch("owlbear_knowledge.copilot_auth.get_copilot_token", new_callable=AsyncMock, side_effect=RuntimeError("no copilot")),
        ):
            async with app_lifespan(MagicMock()):
                pass
        mock_entity_cls.assert_called_once_with(extractor=None)
        mock_llm_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_entity_extractor_called_with_llm_extractor_instance_when_available(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """EntityExtractor receives the LLMExtractor instance as extractor=. (AC1, AC3)"""
        monkeypatch.setenv("OWLBEAR_LLM_API_KEY", "sk-test")
        mock_llm_instance = MagicMock(name="LLMExtractorInstance")
        mock_llm_cls = MagicMock(name="LLMExtractorCls", return_value=mock_llm_instance)
        mock_entity_cls = MagicMock(name="EntityExtractorCls")
        with (
            patch.dict(sys.modules, {"owlbear_knowledge.llm_extractor": _make_llm_mod(mock_llm_cls)}),
            patch("owlbear_mcp_knowledge.server.EntityExtractor", mock_entity_cls),
        ):
            async with app_lifespan(MagicMock()):
                pass
        mock_entity_cls.assert_called_once_with(extractor=mock_llm_instance)


# ---------------------------------------------------------------------------
# TestFromAC_GraphBuilderWiring
# AC4, AC5
# ---------------------------------------------------------------------------


class TestFromAC_GraphBuilderWiring:
    """IntraDocGraphBuilder is always created; InterDocGraphBuilder only when extractor exists."""

    @pytest.mark.asyncio
    async def test_intra_doc_builder_on_app_context_when_extractor_available(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AppContext.intra_doc_builder is not None when LLMExtractor is wired in. (AC4)"""
        monkeypatch.setenv("OWLBEAR_LLM_API_KEY", "sk-test")
        mock_llm_cls = MagicMock(name="LLMExtractorCls")
        with patch.dict(sys.modules, {"owlbear_knowledge.llm_extractor": _make_llm_mod(mock_llm_cls)}):
            async with app_lifespan(MagicMock()) as ctx:
                assert ctx.intra_doc_builder is not None  # noqa: S101

    @pytest.mark.asyncio
    async def test_intra_doc_builder_on_app_context_even_without_extractor(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AppContext.intra_doc_builder is not None even when no LLMExtractor (no-op). (AC4)"""
        monkeypatch.delenv("OWLBEAR_LLM_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with patch.dict(sys.modules, {"owlbear_knowledge.llm_extractor": None}):
            async with app_lifespan(MagicMock()) as ctx:
                assert ctx.intra_doc_builder is not None  # noqa: S101

    @pytest.mark.asyncio
    async def test_intra_doc_builder_receives_extractor_kwarg(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """IntraDocGraphBuilder(extractor=<llm_instance>) when LLMExtractor available. (AC4)"""
        monkeypatch.setenv("OWLBEAR_LLM_API_KEY", "sk-test")
        mock_llm_instance = MagicMock(name="LLMExtractorInstance")
        mock_llm_cls = MagicMock(name="LLMExtractorCls", return_value=mock_llm_instance)
        mock_intra_cls = MagicMock(name="IntraDocGraphBuilderCls")
        with (
            patch.dict(sys.modules, {"owlbear_knowledge.llm_extractor": _make_llm_mod(mock_llm_cls)}),
            # AttributeError until builder imports IntraDocGraphBuilder into server.py (RED)
            patch("owlbear_mcp_knowledge.server.IntraDocGraphBuilder", mock_intra_cls),
        ):
            async with app_lifespan(MagicMock()):
                pass
        mock_intra_cls.assert_called_once()
        _, kwargs = mock_intra_cls.call_args
        assert "extractor" in kwargs, "IntraDocGraphBuilder must receive extractor= kwarg"
        assert kwargs["extractor"] is mock_llm_instance

    @pytest.mark.asyncio
    async def test_inter_doc_builder_none_on_app_context_when_no_extractor(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AppContext.inter_doc_builder is None when no structured extractor available. (AC5)"""
        monkeypatch.delenv("OWLBEAR_LLM_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with patch.dict(sys.modules, {"owlbear_knowledge.llm_extractor": None}):
            async with app_lifespan(MagicMock()) as ctx:
                assert ctx.inter_doc_builder is None  # noqa: S101

    @pytest.mark.asyncio
    async def test_inter_doc_builder_instantiated_with_extractor_vs_gs(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """InterDocGraphBuilder(extractor, vs, gs) when extractor available. (AC5)"""
        monkeypatch.setenv("OWLBEAR_LLM_API_KEY", "sk-test")
        mock_llm_instance = MagicMock(name="LLMExtractorInstance")
        mock_llm_cls = MagicMock(name="LLMExtractorCls", return_value=mock_llm_instance)
        mock_inter_cls = MagicMock(name="InterDocGraphBuilderCls")
        mock_vs = MagicMock(name="VectorStore")
        mock_gs = MagicMock(name="GraphStore")
        with (
            patch.dict(sys.modules, {"owlbear_knowledge.llm_extractor": _make_llm_mod(mock_llm_cls)}),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore", return_value=mock_vs),
            patch("owlbear_mcp_knowledge.server.GraphStore", return_value=mock_gs),
            # AttributeError until builder imports InterDocGraphBuilder into server.py (RED)
            patch("owlbear_mcp_knowledge.server.InterDocGraphBuilder", mock_inter_cls),
        ):
            async with app_lifespan(MagicMock()):
                pass
        mock_inter_cls.assert_called_once()
        args, _ = mock_inter_cls.call_args
        assert args[0] is mock_llm_instance, "First positional arg must be the extractor"
        assert args[1] is mock_vs, "Second positional arg must be vector_store"
        assert args[2] is mock_gs, "Third positional arg must be graph_store"


# ---------------------------------------------------------------------------
# TestFromAC_AppContextFields
# AC6
# ---------------------------------------------------------------------------


class TestFromAC_AppContextFields:
    """AppContext exposes structured_extractor, intra_doc_builder, inter_doc_builder."""

    @pytest.mark.asyncio
    async def test_app_context_has_structured_extractor_field(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """AppContext.structured_extractor exists (is None when no openai key). (AC6)"""
        monkeypatch.delenv("OWLBEAR_LLM_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with patch.dict(sys.modules, {"owlbear_knowledge.llm_extractor": None}):
            async with app_lifespan(MagicMock()) as ctx:
                _ = ctx.structured_extractor  # AttributeError until builder adds the field

    @pytest.mark.asyncio
    async def test_app_context_all_three_builder_fields_present_with_extractor(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """structured_extractor, intra_doc_builder, inter_doc_builder all present. (AC6)"""
        monkeypatch.setenv("OWLBEAR_LLM_API_KEY", "sk-test")
        mock_llm_cls = MagicMock(name="LLMExtractorCls")
        with patch.dict(sys.modules, {"owlbear_knowledge.llm_extractor": _make_llm_mod(mock_llm_cls)}):
            async with app_lifespan(MagicMock()) as ctx:
                # All three fields must be accessible — AttributeError until builder adds them
                assert ctx.structured_extractor is not None  # noqa: S101
                assert ctx.intra_doc_builder is not None  # noqa: S101
                assert ctx.inter_doc_builder is not None  # noqa: S101
