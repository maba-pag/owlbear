"""Durable MCP server regression tests for escaped-newline normalization."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.models import SingleTaskResponse
from owlbear_mcp_kanban.server import (
    AppContext,
    create_task,
    edit_task,
    end_work,
)

_CONFIG_YAML = "next_id: 1\n"
_NORM_SUBSTR = "normalized to actual newlines"


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    (kanban_dir / "decisions").mkdir(exist_ok=True)
    return kanban_dir


def _make_ctx(app_ctx: AppContext) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


def _make_response(**overrides: object) -> SingleTaskResponse:
    defaults: dict[str, object] = {
        "id": 1,
        "title": "T",
        "status": "todo",
        "priority": "important",
        "tags": [],
        "depends_on": [],
        "blocked": False,
        "block_reason": None,
        "claimed": False,
        "claimed_at": None,
        "archival_reason": None,
        "archival_refs": [],
        "dep_status": None,
        "created": "2026-01-01T00:00:00+00:00",
        "updated": "2026-01-01T00:00:00+00:00",
        "body": "",
        "guidance": [],
    }
    defaults.update(overrides)
    return SingleTaskResponse.model_validate(defaults)


def _has_norm_guidance(guidance: list[str]) -> bool:
    return any(_NORM_SUBSTR in guidance_item for guidance_item in guidance)


@pytest.fixture
def mock_view_ctx(tmp_path: Path) -> tuple[AppContext, MagicMock]:
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Seed", status="build", priority="medium")
    engine.list_tasks()

    mock_view = MagicMock()
    resp = _make_response()
    mock_view.create_task.return_value = resp
    mock_view.edit_task.return_value = resp
    mock_view.end_work.return_value = resp
    engine._agent_view = mock_view  # noqa: SLF001

    return AppContext(engine=engine, kanban_dir=kanban_dir), mock_view


class TestNormalizeEscapedNewlines:
    def _fn(self):  # type: ignore[return]
        from owlbear_mcp_kanban.server import _normalize_escaped_newlines

        return _normalize_escaped_newlines

    def test_importable_from_server_module(self) -> None:
        from owlbear_mcp_kanban.server import _normalize_escaped_newlines  # noqa: F401

    def test_returns_str_bool_two_tuple(self) -> None:
        out = self._fn()("any text")
        assert isinstance(out, tuple)
        assert len(out) == 2
        assert isinstance(out[0], str)
        assert isinstance(out[1], bool)

    def test_empty_string_unchanged_and_changed_false(self) -> None:
        text, changed = self._fn()("")
        assert text == ""
        assert changed is False

    def test_plain_text_no_backslash_n_unchanged_changed_false(self) -> None:
        text, changed = self._fn()("Hello world, no escapes here.")
        assert text == "Hello world, no escapes here."
        assert changed is False

    def test_actual_newline_unchanged_changed_false(self) -> None:
        text, changed = self._fn()("line1\nline2")
        assert text == "line1\nline2"
        assert changed is False

    def test_literal_backslash_n_becomes_actual_newline(self) -> None:
        text, changed = self._fn()("line1\\nline2")
        assert text == "line1\nline2"
        assert changed is True

    def test_multiple_literal_backslash_n_all_become_newlines(self) -> None:
        text, changed = self._fn()("a\\nb\\nc")
        assert text == "a\nb\nc"
        assert changed is True

    def test_only_literal_backslash_n_becomes_newline(self) -> None:
        text, changed = self._fn()("\\n")
        assert text == "\n"
        assert changed is True

    def test_escape_convention_double_backslash_n_preserved_as_single(self) -> None:
        text, changed = self._fn()("prefix\\\\nsuffix")
        assert text == "prefix\\nsuffix"
        assert changed is True

    def test_mixed_bug_and_escape_convention_in_same_string(self) -> None:
        text, changed = self._fn()("bug\\nok\\\\nend")
        assert text == "bug\nok\\nend"
        assert changed is True

    def test_sentinel_never_leaks_into_output(self) -> None:
        text, _ = self._fn()("a\\nb\\\\nc")
        assert "\x00" not in text

    def test_changed_false_when_no_literal_backslash_n_present(self) -> None:
        _, changed = self._fn()("Just a real newline\n here, nothing to fix.")
        assert changed is False


class TestCreateTaskNormalization:
    @pytest.mark.asyncio
    async def test_body_literal_backslash_n_normalized_before_engine_call(
        self, mock_view_ctx: tuple[AppContext, MagicMock]
    ) -> None:
        app_ctx, mock_view = mock_view_ctx
        await create_task(_make_ctx(app_ctx), title="T", body="line1\\nline2")
        body_passed = mock_view.create_task.call_args.kwargs["body"]
        assert body_passed == "line1\nline2"

    @pytest.mark.asyncio
    async def test_guidance_appended_to_result_when_body_normalized(
        self, mock_view_ctx: tuple[AppContext, MagicMock]
    ) -> None:
        app_ctx, _ = mock_view_ctx
        result = await create_task(_make_ctx(app_ctx), title="T", body="line1\\nline2")
        assert _has_norm_guidance(result.guidance)

    @pytest.mark.asyncio
    async def test_escape_convention_body_preserved_as_single_backslash_n(
        self, mock_view_ctx: tuple[AppContext, MagicMock]
    ) -> None:
        app_ctx, mock_view = mock_view_ctx
        await create_task(_make_ctx(app_ctx), title="T", body="want\\\\nliteral")
        body_passed = mock_view.create_task.call_args.kwargs["body"]
        assert body_passed == "want\\nliteral"


class TestEditTaskNormalization:
    @pytest.mark.asyncio
    async def test_body_literal_backslash_n_normalized_before_engine_call(
        self, mock_view_ctx: tuple[AppContext, MagicMock]
    ) -> None:
        app_ctx, mock_view = mock_view_ctx
        await edit_task(_make_ctx(app_ctx), id="1", body="line1\\nline2")
        body_passed = mock_view.edit_task.call_args.kwargs["body"]
        assert body_passed == "line1\nline2"

    @pytest.mark.asyncio
    async def test_append_body_literal_backslash_n_normalized_before_engine_call(
        self, mock_view_ctx: tuple[AppContext, MagicMock]
    ) -> None:
        app_ctx, mock_view = mock_view_ctx
        await edit_task(_make_ctx(app_ctx), id="1", append_body="note\\nmore")
        append_passed = mock_view.edit_task.call_args.kwargs["append_body"]
        assert append_passed == "note\nmore"

    @pytest.mark.asyncio
    async def test_guidance_appended_when_body_normalized(self, mock_view_ctx: tuple[AppContext, MagicMock]) -> None:
        app_ctx, _ = mock_view_ctx
        result = await edit_task(_make_ctx(app_ctx), id="1", body="line1\\nline2")
        assert _has_norm_guidance(result.guidance)

    @pytest.mark.asyncio
    async def test_guidance_appended_when_append_body_normalized(
        self, mock_view_ctx: tuple[AppContext, MagicMock]
    ) -> None:
        app_ctx, _ = mock_view_ctx
        result = await edit_task(_make_ctx(app_ctx), id="1", append_body="note\\nmore")
        assert _has_norm_guidance(result.guidance)

    @pytest.mark.asyncio
    async def test_escape_convention_body_preserved_as_single_backslash_n(
        self, mock_view_ctx: tuple[AppContext, MagicMock]
    ) -> None:
        app_ctx, mock_view = mock_view_ctx
        await edit_task(_make_ctx(app_ctx), id="1", body="want\\\\nliteral")
        body_passed = mock_view.edit_task.call_args.kwargs["body"]
        assert body_passed == "want\\nliteral"

    @pytest.mark.asyncio
    async def test_escape_convention_append_body_preserved_as_single_backslash_n(
        self, mock_view_ctx: tuple[AppContext, MagicMock]
    ) -> None:
        app_ctx, mock_view = mock_view_ctx
        await edit_task(_make_ctx(app_ctx), id="1", append_body="want\\\\nliteral")
        append_passed = mock_view.edit_task.call_args.kwargs["append_body"]
        assert append_passed == "want\\nliteral"


class TestEndWorkNormalization:
    @pytest.mark.asyncio
    async def test_note_literal_backslash_n_normalized_before_engine_call(
        self, mock_view_ctx: tuple[AppContext, MagicMock]
    ) -> None:
        app_ctx, mock_view = mock_view_ctx
        await end_work(_make_ctx(app_ctx), id="1", outcome="success", note="done\\nmore")
        note_passed = mock_view.end_work.call_args.kwargs["note"]
        assert note_passed == "done\nmore"

    @pytest.mark.asyncio
    async def test_guidance_appended_when_note_normalized(self, mock_view_ctx: tuple[AppContext, MagicMock]) -> None:
        app_ctx, _ = mock_view_ctx
        result = await end_work(_make_ctx(app_ctx), id="1", outcome="success", note="done\\nmore")
        assert _has_norm_guidance(result.guidance)

    @pytest.mark.asyncio
    async def test_escape_convention_note_preserved_as_single_backslash_n(
        self, mock_view_ctx: tuple[AppContext, MagicMock]
    ) -> None:
        app_ctx, mock_view = mock_view_ctx
        await end_work(_make_ctx(app_ctx), id="1", outcome="success", note="want\\\\nliteral")
        note_passed = mock_view.end_work.call_args.kwargs["note"]
        assert note_passed == "want\\nliteral"


class TestGuidancePositioning:
    @pytest.mark.asyncio
    async def test_edit_task_existing_and_norm_guidance_both_present(
        self,
        mock_view_ctx: tuple[AppContext, MagicMock],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        app_ctx, _ = mock_view_ctx
        monkeypatch.setattr(
            "owlbear_mcp_kanban.server.collect_guidance",
            lambda *_args, **_kwargs: ["existing reminder"],
        )
        result = await edit_task(_make_ctx(app_ctx), id="1", body="line1\\nline2")
        assert any(guidance == "existing reminder" for guidance in result.guidance)
        assert _has_norm_guidance(result.guidance)
        existing_idx = next(index for index, guidance in enumerate(result.guidance) if guidance == "existing reminder")
        norm_idx = next(index for index, guidance in enumerate(result.guidance) if _NORM_SUBSTR in guidance)
        assert existing_idx < norm_idx

    @pytest.mark.asyncio
    async def test_end_work_existing_and_norm_guidance_both_present(
        self,
        mock_view_ctx: tuple[AppContext, MagicMock],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        app_ctx, _ = mock_view_ctx
        monkeypatch.setattr(
            "owlbear_mcp_kanban.server.collect_guidance",
            lambda *_args, **_kwargs: ["existing reminder"],
        )
        result = await end_work(_make_ctx(app_ctx), id="1", outcome="success", note="done\\nmore")
        assert any(guidance == "existing reminder" for guidance in result.guidance)
        assert _has_norm_guidance(result.guidance)
        existing_idx = next(index for index, guidance in enumerate(result.guidance) if guidance == "existing reminder")
        norm_idx = next(index for index, guidance in enumerate(result.guidance) if _NORM_SUBSTR in guidance)
        assert existing_idx < norm_idx


class TestPassthroughWithoutNormalization:
    @pytest.mark.asyncio
    async def test_create_task_body_passthrough_no_normalization(
        self, mock_view_ctx: tuple[AppContext, MagicMock]
    ) -> None:
        from owlbear_mcp_kanban.server import _normalize_escaped_newlines

        _, changed = _normalize_escaped_newlines("clean body no escapes")
        assert not changed
        app_ctx, mock_view = mock_view_ctx
        result = await create_task(_make_ctx(app_ctx), title="T", body="clean body no escapes")
        body_passed = mock_view.create_task.call_args.kwargs["body"]
        assert body_passed == "clean body no escapes"
        assert not _has_norm_guidance(result.guidance)

    @pytest.mark.asyncio
    async def test_edit_task_body_passthrough_no_normalization(
        self, mock_view_ctx: tuple[AppContext, MagicMock]
    ) -> None:
        from owlbear_mcp_kanban.server import _normalize_escaped_newlines

        _, changed = _normalize_escaped_newlines("clean body no escapes")
        assert not changed
        app_ctx, mock_view = mock_view_ctx
        result = await edit_task(_make_ctx(app_ctx), id="1", body="clean body no escapes")
        body_passed = mock_view.edit_task.call_args.kwargs["body"]
        assert body_passed == "clean body no escapes"
        assert not _has_norm_guidance(result.guidance)

    @pytest.mark.asyncio
    async def test_edit_task_append_body_passthrough_no_normalization(
        self, mock_view_ctx: tuple[AppContext, MagicMock]
    ) -> None:
        from owlbear_mcp_kanban.server import _normalize_escaped_newlines

        _, changed = _normalize_escaped_newlines("clean append no escapes")
        assert not changed
        app_ctx, mock_view = mock_view_ctx
        result = await edit_task(_make_ctx(app_ctx), id="1", append_body="clean append no escapes")
        append_passed = mock_view.edit_task.call_args.kwargs["append_body"]
        assert append_passed == "clean append no escapes"
        assert not _has_norm_guidance(result.guidance)

    @pytest.mark.asyncio
    async def test_end_work_note_passthrough_no_normalization(
        self, mock_view_ctx: tuple[AppContext, MagicMock]
    ) -> None:
        from owlbear_mcp_kanban.server import _normalize_escaped_newlines

        _, changed = _normalize_escaped_newlines("clean note no escapes")
        assert not changed
        app_ctx, mock_view = mock_view_ctx
        result = await end_work(_make_ctx(app_ctx), id="1", outcome="success", note="clean note no escapes")
        note_passed = mock_view.end_work.call_args.kwargs["note"]
        assert note_passed == "clean note no escapes"
        assert not _has_norm_guidance(result.guidance)
