"""RED-phase tests for legacy API key branch removal — task #1358.

AC coverage:
  AC1: OWLBEAR_LLM_API_KEY / OPENAI_API_KEY branch removed; structured_extractor=None always.
  AC2: LLMExtractor lazy import and related env-var reads removed from server.py source.
  AC3: README.md no longer documents OWLBEAR_LLM_API_KEY or OPENAI_API_KEY env vars.
  AC4: Dead test files test_copilot_server_wiring_888.py and test_llmextractor_wiring_876.py deleted.
  AC5: EntityExtractor and IntraDocGraphBuilder receive extractor=None unconditionally.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_mcp_knowledge.server import app_lifespan

_REPO_ROOT = Path(__file__).parent.parent
_SERVER_PY = _REPO_ROOT / "serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py"
_README = _REPO_ROOT / "serve/mcp-knowledge/README.md"
_MCP_KNOWLEDGE_TESTS = _REPO_ROOT / "serve/mcp-knowledge/tests"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_llm_mod(llm_cls: MagicMock | None = None) -> ModuleType:
    """Return a fake owlbear_knowledge.llm_extractor module."""
    mod = ModuleType("owlbear_knowledge.llm_extractor")
    mod.LLMExtractor = llm_cls or MagicMock(name="LLMExtractorCls")  # type: ignore[attr-defined]
    return mod


# ---------------------------------------------------------------------------
# Autouse fixture — patches heavy I/O deps so app_lifespan runs without real DB/network
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def mock_lifespan_deps() -> None:
    """Patch I/O-heavy constructors so app_lifespan can run without real resources."""
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
# TestFromAC_ApiKeyBranchRemoved — AC1
# structured_extractor is None regardless of which key env vars are set
# ---------------------------------------------------------------------------


class TestFromAC_ApiKeyBranchRemoved:
    """AC1: OWLBEAR_LLM_API_KEY / OPENAI_API_KEY branch removed; structured_extractor=None."""

    @pytest.mark.asyncio
    async def test_structured_extractor_none_when_owlbear_key_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """structured_extractor=None even when OWLBEAR_LLM_API_KEY is set.

        Currently FAILS: current code creates an LLMExtractor instance when the key is present.
        """
        monkeypatch.setenv("OWLBEAR_LLM_API_KEY", "sk-should-be-ignored")
        mock_llm_cls = MagicMock(name="LLMExtractorCls", return_value=MagicMock())
        with patch.dict(sys.modules, {"owlbear_knowledge.llm_extractor": _make_llm_mod(mock_llm_cls)}):
            async with app_lifespan(MagicMock()) as ctx:
                assert ctx.structured_extractor is None  # noqa: S101

    @pytest.mark.asyncio
    async def test_structured_extractor_none_when_openai_key_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """structured_extractor=None even when OPENAI_API_KEY is set as fallback.

        Currently FAILS: current code enters the api_key branch via the OPENAI_API_KEY or-clause.
        """
        monkeypatch.delenv("OWLBEAR_LLM_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-should-be-ignored")
        mock_llm_cls = MagicMock(name="LLMExtractorCls", return_value=MagicMock())
        with patch.dict(sys.modules, {"owlbear_knowledge.llm_extractor": _make_llm_mod(mock_llm_cls)}):
            async with app_lifespan(MagicMock()) as ctx:
                assert ctx.structured_extractor is None  # noqa: S101

    @pytest.mark.asyncio
    async def test_llmextractor_never_instantiated_when_both_keys_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """LLMExtractor.__init__ is never called even when both API key env vars are present.

        Currently FAILS: current code calls LLMExtractor() inside the if api_key: branch.
        """
        monkeypatch.setenv("OWLBEAR_LLM_API_KEY", "sk-primary")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fallback")
        mock_llm_cls = MagicMock(name="LLMExtractorCls")
        with patch.dict(sys.modules, {"owlbear_knowledge.llm_extractor": _make_llm_mod(mock_llm_cls)}):
            async with app_lifespan(MagicMock()):
                pass
        mock_llm_cls.assert_not_called()


# ---------------------------------------------------------------------------
# TestFromAC_DeadImportsRemoved — AC2
# LLMExtractor lazy import and env-var reads absent from server.py source text
# ---------------------------------------------------------------------------


class TestFromAC_DeadImportsRemoved:
    """AC2: server.py source no longer references LLMExtractor or the removed env vars."""

    def test_server_source_no_llm_extractor_import(self) -> None:
        """server.py contains no reference to 'llm_extractor'.

        Currently FAILS: conditional 'from owlbear_knowledge.llm_extractor import LLMExtractor'
        is present inside the api_key branch at L536.
        """
        source = _SERVER_PY.read_text()
        assert "llm_extractor" not in source  # noqa: S101

    def test_server_source_no_owlbear_llm_api_key(self) -> None:
        """server.py contains no os.environ read for 'OWLBEAR_LLM_API_KEY'.

        Currently FAILS: the api_key branch reads this env var at L531.
        """
        source = _SERVER_PY.read_text()
        assert "OWLBEAR_LLM_API_KEY" not in source  # noqa: S101

    def test_server_source_no_openai_api_key(self) -> None:
        """server.py contains no os.environ read for 'OPENAI_API_KEY'.

        Currently FAILS: the api_key branch reads this as a fallback key at L532.
        """
        source = _SERVER_PY.read_text()
        assert "OPENAI_API_KEY" not in source  # noqa: S101


# ---------------------------------------------------------------------------
# TestFromAC_ReadmeCleanup — AC3
# README.md no longer documents the removed API key env vars
# ---------------------------------------------------------------------------


class TestFromAC_ReadmeCleanup:
    """AC3: README.md env-var table row for LLM API keys has been removed."""

    def test_readme_no_owlbear_llm_api_key(self) -> None:
        """README.md does not mention OWLBEAR_LLM_API_KEY.

        Currently FAILS: README configuration table includes this env var at L43.
        """
        readme = _README.read_text()
        assert "OWLBEAR_LLM_API_KEY" not in readme  # noqa: S101

    def test_readme_no_openai_api_key(self) -> None:
        """README.md does not mention OPENAI_API_KEY as an LLM key fallback.

        Currently FAILS: README configuration table includes this env var at L44.
        """
        readme = _README.read_text()
        assert "OPENAI_API_KEY" not in readme  # noqa: S101


# ---------------------------------------------------------------------------
# TestFromAC_DeadTestsRemoved — AC4
# Dead test files asserting API-key-present behavior have been deleted
# ---------------------------------------------------------------------------


class TestFromAC_DeadTestsRemoved:
    """AC4: test files covering the removed API key path no longer exist."""

    def test_copilot_server_wiring_888_file_deleted(self) -> None:
        """test_copilot_server_wiring_888.py has been deleted from serve/mcp-knowledge/tests/.

        Currently FAILS: the file exists and covers the now-removed API key path.
        """
        dead_file = _MCP_KNOWLEDGE_TESTS / "test_copilot_server_wiring_888.py"
        assert not dead_file.exists()  # noqa: S101

    def test_llmextractor_wiring_876_file_deleted(self) -> None:
        """test_llmextractor_wiring_876.py has been deleted from serve/mcp-knowledge/tests/.

        Currently FAILS: the file exists and tests conditional LLMExtractor wiring
        that the removed api_key branch enabled.
        """
        dead_file = _MCP_KNOWLEDGE_TESTS / "test_llmextractor_wiring_876.py"
        assert not dead_file.exists()  # noqa: S101


# ---------------------------------------------------------------------------
# TestFromAC_NoRegression — AC5
# EntityExtractor and IntraDocGraphBuilder receive extractor=None unconditionally
# ---------------------------------------------------------------------------


class TestFromAC_NoRegression:
    """AC5: EntityExtractor and IntraDocGraphBuilder always get extractor=None after cleanup."""

    @pytest.mark.asyncio
    async def test_entity_extractor_receives_none_when_api_key_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """EntityExtractor is constructed with extractor=None even when OWLBEAR_LLM_API_KEY is set.

        Currently FAILS: current code passes an LLMExtractor instance as extractor when a key
        is present.
        """
        monkeypatch.setenv("OWLBEAR_LLM_API_KEY", "sk-test-key")
        mock_llm_cls = MagicMock(name="LLMExtractorCls", return_value=MagicMock())
        with (
            patch.dict(sys.modules, {"owlbear_knowledge.llm_extractor": _make_llm_mod(mock_llm_cls)}),
            patch("owlbear_mcp_knowledge.server.EntityExtractor") as mock_ee,
        ):
            async with app_lifespan(MagicMock()):
                pass
        mock_ee.assert_called_once()
        _, kwargs = mock_ee.call_args
        assert kwargs.get("extractor") is None  # noqa: S101

    @pytest.mark.asyncio
    async def test_intra_doc_builder_receives_none_when_api_key_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """IntraDocGraphBuilder is constructed with extractor=None even when API key is set.

        Currently FAILS: current code passes an LLMExtractor instance as extractor when a key
        is present.
        """
        monkeypatch.setenv("OWLBEAR_LLM_API_KEY", "sk-test-key")
        mock_llm_cls = MagicMock(name="LLMExtractorCls", return_value=MagicMock())
        with (
            patch.dict(sys.modules, {"owlbear_knowledge.llm_extractor": _make_llm_mod(mock_llm_cls)}),
            patch("owlbear_mcp_knowledge.server.IntraDocGraphBuilder") as mock_idb,
        ):
            async with app_lifespan(MagicMock()):
                pass
        mock_idb.assert_called_once()
        _, kwargs = mock_idb.call_args
        assert kwargs.get("extractor") is None  # noqa: S101
