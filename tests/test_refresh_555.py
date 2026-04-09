"""RED-phase tests for RefreshOrchestrator contract gaps (#555 — second cycle).

Tests two AC requirements NOT covered by existing test suites:

1. file_glob: AC says "validates each glob result with _paths.sandbox_path"
   Current implementation ONLY validates base_dir once — no per-file call.

2. file_glob: Architecture Review builder note requires ALL handlers to call
   pipeline.ingest(intake_result, scope=source.scope). Current implementation
   omits the scope kwarg in _handle_file_glob.

Both tests FAIL against the current implementation:
- sandbox_path wraps spy: call_count == 1 (base_dir only), not 3 (base_dir + 2 files)
- pipeline.ingest called as ingest(intake_result) — missing scope kwarg
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from owlbear_knowledge._paths import sandbox_path as _real_sandbox_path
from owlbear_knowledge.ingest import IngestResult
from owlbear_knowledge.intake import IntakeResult
from owlbear_knowledge.models import KnowledgeSource, SourceType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _make_source(
    *,
    source_type: SourceType = SourceType.FILE_GLOB,
    config: dict[str, Any] | None = None,
    scope: str = "global",
) -> KnowledgeSource:
    return KnowledgeSource(
        name="src",
        source_type=source_type,
        enabled=True,
        priority=0,
        config=config or {},
        scope=scope,
        created_at=_now(),
        updated_at=_now(),
    )


def _ok_ingest_result() -> IngestResult:
    return IngestResult(
        document_id="doc-1",
        chunk_count=1,
        entity_count=0,
        edge_count=0,
        status="ok",
    )


def _make_intake_result(source: str = "file.txt") -> IntakeResult:
    return IntakeResult(
        content="hello",
        source=source,
        metadata={"source_type": "file", "fetched_at": _now()},
    )


# ===========================================================================
# AC: file_glob "validates each glob result with _paths.sandbox_path"
# ===========================================================================


class TestFromAC_FileGlobPerFileSandboxValidation:  # noqa: N801
    """AC: 'validates each glob result with _paths.sandbox_path'.

    Current _handle_file_glob only calls sandbox_path once (for base_dir),
    then iterates over safe_base.glob() results without per-file validation.
    Both glob-result files must be individually validated.
    """

    @pytest.mark.asyncio
    async def test_sandbox_path_called_for_each_glob_result(self, tmp_path: Path) -> None:
        """sandbox_path is called for base_dir AND for each matched file."""
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        (tmp_path / "a.txt").write_text("content a")
        (tmp_path / "b.txt").write_text("content b")

        pipeline_mock = MagicMock()
        pipeline_mock.ingest = AsyncMock(return_value=_ok_ingest_result())
        store_mock = MagicMock()
        store_mock.update = MagicMock()

        with (
            patch(
                "owlbear_knowledge.refresh.sandbox_path",
                wraps=_real_sandbox_path,
            ) as mock_sb,
            patch(
                "owlbear_knowledge.intake.read_file",
                new=AsyncMock(return_value=_make_intake_result()),
            ),
        ):
            orch = RefreshOrchestrator(store=store_mock, pipeline=pipeline_mock, workspace_root=tmp_path)
            source = _make_source(
                source_type=SourceType.FILE_GLOB,
                config={"pattern": "*.txt"},
            )
            await orch.refresh(source)

        # AC: "validates each glob result with _paths.sandbox_path"
        # 1 base_dir call + 2 per-file calls = 3 total
        # Current implementation: only 1 call (base_dir only) — this FAILS
        file_paths_checked = {call[0][1] for call in mock_sb.call_args_list}
        assert (tmp_path / "a.txt") in file_paths_checked, (
            f"sandbox_path was not called for glob result a.txt; calls: {mock_sb.call_args_list}"
        )
        assert (tmp_path / "b.txt") in file_paths_checked, (
            f"sandbox_path was not called for glob result b.txt; calls: {mock_sb.call_args_list}"
        )


# ===========================================================================
# AC + Arch Review: file_glob must pass scope=source.scope to pipeline.ingest
# ===========================================================================


class TestFromAC_FileGlobScopeForwarding:  # noqa: N801
    """Architecture Review builder note for file_glob handler.

    The architect explicitly required: "pass scope=source.scope to pipeline.ingest
    in all handlers" — citing url_list as the model. Current _handle_file_glob
    calls pipeline.ingest(intake_result) with no scope kwarg.
    """

    @pytest.mark.asyncio
    async def test_file_glob_passes_source_scope_to_pipeline_ingest(self, tmp_path: Path) -> None:
        """pipeline.ingest must receive scope=source.scope in the file_glob handler."""
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        (tmp_path / "doc.txt").write_text("content")
        pipeline_mock = MagicMock()
        pipeline_mock.ingest = AsyncMock(return_value=_ok_ingest_result())
        store_mock = MagicMock()
        store_mock.update = MagicMock()

        with patch(
            "owlbear_knowledge.intake.read_file",
            new=AsyncMock(return_value=_make_intake_result()),
        ):
            orch = RefreshOrchestrator(store=store_mock, pipeline=pipeline_mock, workspace_root=tmp_path)
            source = _make_source(
                source_type=SourceType.FILE_GLOB,
                config={"pattern": "*.txt"},
                scope="my-project",
            )
            await orch.refresh(source)

        # Arch Review: file_glob must forward scope=source.scope
        # Current implementation calls ingest(intake_result) — no scope — this FAILS
        pipeline_mock.ingest.assert_called_once_with(ANY, scope="my-project")


# ===========================================================================
# AC: url_list "calls pipeline.ingest(intake_result, scope=source.scope)"
# Restored from cycle-1 (removed when cycle-2 overwrote this file)
# ===========================================================================


class TestFromAC_UrlListScopeForwarding:  # noqa: N801
    """AC: url_list handler calls pipeline.ingest(intake_result, scope=source.scope).

    The reviewer found no test asserting scope kwarg for url_list: all three
    url_list tests in test_refresh_orchestrator.py only check call_count and
    result.refreshed — none assert scope=source.scope.  This test would fail
    if the scope kwarg were dropped or hard-coded.
    """

    @pytest.mark.asyncio
    async def test_url_list_passes_source_scope_to_pipeline_ingest(self) -> None:
        """pipeline.ingest must receive scope=source.scope in the url_list handler."""
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        pipeline_mock = MagicMock()
        pipeline_mock.ingest = AsyncMock(return_value=_ok_ingest_result())
        store_mock = MagicMock()
        store_mock.update = MagicMock()

        with patch(
            "owlbear_knowledge.intake.read_url",
            new=AsyncMock(return_value=_make_intake_result("https://a.com")),
        ):
            orch = RefreshOrchestrator(store=store_mock, pipeline=pipeline_mock)
            source = _make_source(
                source_type=SourceType.URL_LIST,
                config={"urls": ["https://a.com"]},
                scope="my-project",
            )
            await orch.refresh(source)

        # AC: url_list must call pipeline.ingest(intake_result, scope=source.scope)
        # Drops scope kwarg? -> assert_called_once_with fails -> regression caught
        pipeline_mock.ingest.assert_called_once_with(ANY, scope="my-project")

    @pytest.mark.asyncio
    async def test_url_list_scope_forwarded_for_every_url(self) -> None:
        """scope=source.scope is forwarded for all URLs, not just the first."""
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        pipeline_mock = MagicMock()
        pipeline_mock.ingest = AsyncMock(return_value=_ok_ingest_result())
        store_mock = MagicMock()
        store_mock.update = MagicMock()

        with patch(
            "owlbear_knowledge.intake.read_url",
            new=AsyncMock(return_value=_make_intake_result("https://x.com")),
        ):
            orch = RefreshOrchestrator(store=store_mock, pipeline=pipeline_mock)
            source = _make_source(
                source_type=SourceType.URL_LIST,
                config={"urls": ["https://a.com", "https://b.com", "https://c.com"]},
                scope="team-wiki",
            )
            await orch.refresh(source)

        assert pipeline_mock.ingest.call_count == 3
        for call in pipeline_mock.ingest.call_args_list:
            _, kwargs = call
            assert kwargs.get("scope") == "team-wiki", (
                f"pipeline.ingest call missing scope='team-wiki'; got kwargs={kwargs}"
            )
