"""RED-phase tests for MCP startup without copilot_auth (task #1317).

AC coverage:
  AC1: copilot_auth NOT imported during app_lifespan; structured_extractor is None
       when OWLBEAR_LLM_API_KEY is unset.
  AC2: IngestPipeline and KnowledgeQueryService wired in lifespan context
       when structured_extractor is None.
  AC3: Lifespan startup deletes ~/.owlbear/copilot_token.json if present;
       cleanup is idempotent when file absent.

All tests FAIL until #1318 removes the copilot_auth fallback path and adds
token-file cleanup to app_lifespan.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_mcp_knowledge.server import app_lifespan


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_auth_module(token: str = "copilot_tok_xyz") -> ModuleType:  # noqa: S107
    """Return a fake owlbear_knowledge.copilot_auth module."""
    mod = ModuleType("owlbear_knowledge.copilot_auth")
    mod.get_copilot_token = AsyncMock(return_value=token)  # type: ignore[attr-defined]
    mod.detect_editor_versions = MagicMock(  # type: ignore[attr-defined]
        return_value={"Editor-Version": "vscode/1.97.1"}
    )
    return mod


def _mock_llm_module() -> ModuleType:
    """Return a fake owlbear_knowledge.llm_extractor module."""
    mod = ModuleType("owlbear_knowledge.llm_extractor")
    mock_instance = MagicMock(name="LLMExtractorInstance")
    mod.LLMExtractor = MagicMock(  # type: ignore[attr-defined]
        name="LLMExtractorCls", return_value=mock_instance
    )
    return mod


# ---------------------------------------------------------------------------
# Autouse fixture: patches I/O-heavy constructors so app_lifespan runs fast
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def mock_lifespan_deps() -> None:
    """Patch heavy I/O deps so app_lifespan runs without real DB or network."""
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
# TestFromAC_LifespanNoCopilotAuth
# AC1: copilot_auth not imported; structured_extractor is None without API key
# AC2: IngestPipeline + KnowledgeQueryService wired when structured_extractor is None
# ---------------------------------------------------------------------------


class TestFromAC_LifespanNoCopilotAuth:
    """AC1 + AC2: app_lifespan does not import copilot_auth after removal."""

    @pytest.mark.asyncio
    async def test_copilot_auth_not_imported_when_no_api_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_copilot_token is NOT called when OWLBEAR_LLM_API_KEY is unset.

        In the new code (after #1318), the copilot_auth import branch is removed,
        so get_copilot_token is never invoked.

        Currently FAILS: current lifespan enters the copilot fallback branch and
        calls get_copilot_token when no API key env var is set.
        """
        monkeypatch.delenv("OWLBEAR_LLM_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        mock_auth = _mock_auth_module()
        mock_llm = _mock_llm_module()

        with patch.dict(
            sys.modules,
            {
                "owlbear_knowledge.copilot_auth": mock_auth,
                "owlbear_knowledge.llm_extractor": mock_llm,
            },
        ):
            async with app_lifespan(MagicMock()):
                pass

        # New code: copilot_auth branch removed — get_copilot_token never called.
        # Current code: enters else-branch, calls get_copilot_token → assertion FAILS.
        mock_auth.get_copilot_token.assert_not_called()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_structured_extractor_is_none_without_api_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ctx.structured_extractor is None when OWLBEAR_LLM_API_KEY is unset.

        After #1318, copilot_auth path is removed; structured_extractor stays None.

        Currently FAILS: copilot path sets structured_extractor to an LLMExtractor
        instance when get_copilot_token succeeds.
        """
        monkeypatch.delenv("OWLBEAR_LLM_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        mock_auth = _mock_auth_module()
        mock_llm = _mock_llm_module()

        with patch.dict(
            sys.modules,
            {
                "owlbear_knowledge.copilot_auth": mock_auth,
                "owlbear_knowledge.llm_extractor": mock_llm,
            },
        ):
            async with app_lifespan(MagicMock()) as ctx:
                # New code: always None (no copilot fallback).
                # Current code: mock_llm.LLMExtractor instance (not None) → FAILS.
                assert ctx.structured_extractor is None  # noqa: S101

    @pytest.mark.asyncio
    async def test_ingest_pipeline_and_query_service_wired_with_null_extractor(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """IngestPipeline and KnowledgeQueryService are wired when structured_extractor is None.

        After #1318, with no copilot fallback, structured_extractor is None but
        pipeline services must still be fully wired in the lifespan context.

        Currently FAILS: structured_extractor is set (not None) because the current
        code runs the copilot path, making the third assertion fail.
        """
        monkeypatch.delenv("OWLBEAR_LLM_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        mock_auth = _mock_auth_module()
        mock_llm = _mock_llm_module()

        with patch.dict(
            sys.modules,
            {
                "owlbear_knowledge.copilot_auth": mock_auth,
                "owlbear_knowledge.llm_extractor": mock_llm,
            },
        ):
            async with app_lifespan(MagicMock()) as ctx:
                # structured_extractor must be None in the new no-copilot world.
                # Currently FAILS here before the pipeline assertions are reached.
                assert ctx.structured_extractor is None  # noqa: S101
                # Pipeline services must still be available.
                assert ctx.ingest_pipeline is not None  # noqa: S101
                assert ctx.query_service is not None  # noqa: S101


# ---------------------------------------------------------------------------
# TestFromAC_TokenFileCleanup
# AC3: lifespan startup cleans up ~/.owlbear/copilot_token.json
# ---------------------------------------------------------------------------


class TestFromAC_TokenFileCleanup:
    """AC3: app_lifespan deletes stale copilot_token.json at startup."""

    @pytest.fixture(autouse=True)
    def _block_copilot_auth(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Block copilot_auth import and clear API key env vars for cleanup tests."""
        # Blocking import via None sentinel: from owlbear_knowledge.copilot_auth import ...
        # raises ImportError → caught by lifespan's except → structured_extractor stays None.
        monkeypatch.setitem(sys.modules, "owlbear_knowledge.copilot_auth", None)
        monkeypatch.delenv("OWLBEAR_LLM_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    @pytest.mark.asyncio
    async def test_token_file_deleted_when_present_at_startup(
        self, tmp_path: Path
    ) -> None:
        """Lifespan deletes ~/.owlbear/copilot_token.json when it exists before startup.

        After #1318, the lifespan includes cleanup code that removes a stale token
        file left over from the old copilot_auth flow.

        Currently FAILS: no cleanup code in app_lifespan — file persists after startup.
        """
        token_dir = tmp_path / ".owlbear"
        token_dir.mkdir(parents=True)
        token_file = token_dir / "copilot_token.json"
        token_file.write_text('{"token": "stale_copilot_token"}')

        with patch("pathlib.Path.home", return_value=tmp_path):
            async with app_lifespan(MagicMock()):
                pass

        # New code: lifespan deletes the token file.
        # Current code: no cleanup — file still exists → assertion FAILS.
        assert not token_file.exists()  # noqa: S101

    @pytest.mark.asyncio
    async def test_token_file_cleanup_idempotent_when_absent(
        self, tmp_path: Path
    ) -> None:
        """Lifespan startup does not raise when copilot_token.json is absent.

        Idempotency: cleanup is attempted even when file is missing (missing_ok=True
        or equivalent), so a second startup does not fail.

        Currently FAILS: no cleanup code exists — Path.unlink is never called.
        """
        token_file = tmp_path / ".owlbear" / "copilot_token.json"
        assert not token_file.exists()

        with (
            patch("pathlib.Path.home", return_value=tmp_path),
            patch.object(Path, "unlink", autospec=True) as mock_unlink,
        ):
            async with app_lifespan(MagicMock()):
                pass

        # New code: cleanup code calls unlink (with missing_ok=True) even when absent.
        # Current code: no cleanup → unlink never called → assertion FAILS.
        mock_unlink.assert_called()
