"""RED-phase tests for server.py Copilot fallback wiring (task #888).

AC coverage:
  AC4: LLMExtractor uses Copilot token when OWLBEAR_LLM_API_KEY is not set
  AC5: Graceful fallback: if Copilot auth fails, extraction is None (no-op)
  AC3 (extended): Copilot-Integration-Id and Editor headers forwarded to LLMExtractor

All tests FAIL until #888 implements the Copilot fallback path in app_lifespan.
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


def _make_copilot_auth_mod(
    get_token_return: str | None = "copilot_token_xyz",  # noqa: S107
    get_token_side_effect: Exception | None = None,
    editor_versions: dict | None = None,
) -> ModuleType:
    """Return a fake owlbear_knowledge.copilot_auth module."""
    mod = ModuleType("owlbear_knowledge.copilot_auth")
    if get_token_side_effect is not None:
        mod.get_copilot_token = AsyncMock(side_effect=get_token_side_effect)  # type: ignore[attr-defined]
    else:
        mod.get_copilot_token = AsyncMock(return_value=get_token_return)  # type: ignore[attr-defined]
    mod.detect_editor_versions = MagicMock(  # type: ignore[attr-defined]
        return_value=editor_versions or {"Editor-Version": "vscode/1.97.1"}
    )
    return mod


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
# TestFromAC_CopilotServerFallback
# AC4, AC5: lifespan tries Copilot when no explicit API key is set
# ---------------------------------------------------------------------------


class TestFromAC_CopilotServerFallback:
    """AC4, AC5: app_lifespan falls back to Copilot auth when no LLM API key is set."""

    @pytest.mark.asyncio
    async def test_lifespan_calls_get_copilot_token_when_no_api_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_copilot_token() is called during lifespan when neither API key env var is set."""
        monkeypatch.delenv("OWLBEAR_LLM_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        copilot_mod = _make_copilot_auth_mod(get_token_return="cp_tok")
        llm_mod = _make_llm_mod()

        with patch.dict(
            sys.modules,
            {
                "owlbear_knowledge.copilot_auth": copilot_mod,
                "owlbear_knowledge.llm_extractor": llm_mod,
            },
        ):
            async with app_lifespan(MagicMock()):
                pass

        copilot_mod.get_copilot_token.assert_called_once()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_lifespan_creates_llm_extractor_with_copilot_token_as_api_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """LLMExtractor receives the Copilot token as api_key when no OWLBEAR_LLM_API_KEY set."""
        monkeypatch.delenv("OWLBEAR_LLM_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        copilot_token = "github_copilot_tok_abc"
        copilot_mod = _make_copilot_auth_mod(get_token_return=copilot_token)
        mock_llm_cls = MagicMock(name="LLMExtractorCls")
        llm_mod = _make_llm_mod(mock_llm_cls)

        with patch.dict(
            sys.modules,
            {
                "owlbear_knowledge.copilot_auth": copilot_mod,
                "owlbear_knowledge.llm_extractor": llm_mod,
            },
        ):
            async with app_lifespan(MagicMock()):
                pass

        mock_llm_cls.assert_called_once()
        _, kwargs = mock_llm_cls.call_args
        assert kwargs.get("api_key") == copilot_token

    @pytest.mark.asyncio
    async def test_lifespan_structured_extractor_not_none_when_copilot_succeeds(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ctx.structured_extractor is populated when Copilot auth succeeds and no API key."""
        monkeypatch.delenv("OWLBEAR_LLM_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        copilot_mod = _make_copilot_auth_mod(get_token_return="cp_tok")
        mock_llm_instance = MagicMock(name="LLMExtractorInstance")
        mock_llm_cls = MagicMock(name="LLMExtractorCls", return_value=mock_llm_instance)
        llm_mod = _make_llm_mod(mock_llm_cls)

        with patch.dict(
            sys.modules,
            {
                "owlbear_knowledge.copilot_auth": copilot_mod,
                "owlbear_knowledge.llm_extractor": llm_mod,
            },
        ):
            async with app_lifespan(MagicMock()) as ctx:
                # Copilot path wired: extractor must NOT be None
                assert ctx.structured_extractor is not None  # noqa: S101

    @pytest.mark.asyncio
    async def test_lifespan_structured_extractor_none_when_copilot_auth_fails(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ctx.structured_extractor is None when Copilot auth raises (graceful fallback)."""
        monkeypatch.delenv("OWLBEAR_LLM_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        copilot_mod = _make_copilot_auth_mod(
            get_token_side_effect=TimeoutError("browser auth timeout")
        )

        with patch.dict(sys.modules, {"owlbear_knowledge.copilot_auth": copilot_mod}):
            async with app_lifespan(MagicMock()) as ctx:
                # Both: Copilot was attempted AND gracefully degraded to None
                copilot_mod.get_copilot_token.assert_called_once()  # noqa: S101  # type: ignore[attr-defined]
                assert ctx.structured_extractor is None  # noqa: S101

    @pytest.mark.asyncio
    async def test_lifespan_passes_copilot_integration_header_to_llm_extractor(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """LLMExtractor receives 'Copilot-Integration-Id' in default_headers on Copilot path."""
        monkeypatch.delenv("OWLBEAR_LLM_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        copilot_mod = _make_copilot_auth_mod(get_token_return="cp_tok")
        mock_llm_cls = MagicMock(name="LLMExtractorCls")
        llm_mod = _make_llm_mod(mock_llm_cls)

        with patch.dict(
            sys.modules,
            {
                "owlbear_knowledge.copilot_auth": copilot_mod,
                "owlbear_knowledge.llm_extractor": llm_mod,
            },
        ):
            async with app_lifespan(MagicMock()):
                pass

        mock_llm_cls.assert_called_once()
        _, kwargs = mock_llm_cls.call_args
        default_headers = kwargs.get("default_headers") or {}
        assert "Copilot-Integration-Id" in default_headers, (
            f"Expected 'Copilot-Integration-Id' in default_headers. Got: {default_headers}"
        )
