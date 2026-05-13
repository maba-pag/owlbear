"""RED phase tests — body newline normalization at MCP kanban ingress.

Task: #1532  Parent: #1531
"""

from __future__ import annotations

import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.models import SingleTaskResponse
from owlbear_mcp_kanban.server import (
    AppContext,
    create_dr,
    create_task,
    edit_task,
    end_work,
)

# ── shared helpers ────────────────────────────────────────────────────────────

_CONFIG_YAML = "next_id: 1\n"

# Substring that uniquely identifies the normalization guidance message (AC 3).
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
    return any(_NORM_SUBSTR in g for g in guidance)


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_view_ctx(tmp_path: Path) -> tuple[AppContext, MagicMock]:
    """App context with mock agent view for all mutation tools."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Seed", status="todo", priority="important")
    engine.list_tasks()

    mock_view = MagicMock()
    resp = _make_response()
    mock_view.create_task.return_value = resp
    mock_view.edit_task.return_value = resp
    mock_view.end_work.return_value = resp
    engine._agent_view = mock_view  # noqa: SLF001

    return AppContext(engine=engine, kanban_dir=kanban_dir), mock_view


@pytest.fixture
def dr_ctx(tmp_path: Path) -> AppContext:
    """Real board for create_dr integration tests."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("DR seed", status="todo", priority="important")
    engine.list_tasks()
    return AppContext(engine=engine, kanban_dir=kanban_dir)


# ── helpers for create_dr monkeypatch ─────────────────────────────────────────


def _fake_decisions(captured: dict) -> types.SimpleNamespace:
    """Return a decisions namespace stub that captures body and creates a real file."""

    def fake_create_dr(
        d_dir: Path,
        _engine: object,
        *,
        task_id: int,
        body: str,
        **_extra: object,
    ) -> Path:
        captured["body"] = body
        d_dir.mkdir(parents=True, exist_ok=True)
        path = d_dir / f"{task_id}-test.md"
        path.write_text(body, encoding="utf-8")
        return path

    return types.SimpleNamespace(create_dr=fake_create_dr)


# ── 1. Unit tests: _normalize_escaped_newlines helper ────────────────────────


class TestFromAC_NormalizeHelper:
    """AC 1: helper exists in server.py; implements three-step protect/normalize/restore."""

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

    def test_actual_newline_0x0a_unchanged_changed_false(self) -> None:
        # Correct newline (0x0A) must NOT be touched.
        text, changed = self._fn()("line1\nline2")
        assert text == "line1\nline2"
        assert changed is False

    def test_literal_backslash_n_becomes_actual_newline(self) -> None:
        # Simulates JSON `\\n` → Python receives `\n` (0x5C 0x6E) — the agent bug.
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
        # JSON `\\\\n` → Python receives `\\n` (0x5C 0x5C 0x6E).
        # Three-step should reduce `\\n` (3 chars) → `\n` (2 chars, i.e. literal backslash+n).
        text, changed = self._fn()("prefix\\\\nsuffix")
        assert text == "prefix\\nsuffix"
        assert changed is True

    def test_mixed_bug_and_escape_convention_in_same_string(self) -> None:
        # `\\n` = bug → newline; `\\\\n` = convention → `\n` (literal backslash+n)
        text, changed = self._fn()("bug\\nok\\\\nend")
        assert text == "bug\nok\\nend"
        assert changed is True

    def test_sentinel_never_leaks_into_output(self) -> None:
        text, _ = self._fn()("a\\nb\\\\nc")
        assert "\x00" not in text

    def test_changed_false_when_no_literal_backslash_n_present(self) -> None:
        _, changed = self._fn()("Just a real newline\n here, nothing to fix.")
        assert changed is False


# ── 2. create_task — body normalization ──────────────────────────────────────


class TestFromAC_CreateTaskNormalization:
    """AC 2, 3, 5: create_task body normalized; guidance appended; escape convention."""

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
        # JSON `\\\\n` → Python `\\n` (double backslash+n); should become `\n` (single).
        app_ctx, mock_view = mock_view_ctx
        await create_task(_make_ctx(app_ctx), title="T", body="want\\\\nliteral")
        body_passed = mock_view.create_task.call_args.kwargs["body"]
        assert body_passed == "want\\nliteral"


# ── 3. edit_task — body and append_body normalization ────────────────────────


class TestFromAC_EditTaskNormalization:
    """AC 2, 3, 5: edit_task body and append_body normalized; guidance appended."""

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
    async def test_guidance_appended_when_body_normalized(
        self, mock_view_ctx: tuple[AppContext, MagicMock]
    ) -> None:
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


# ── 4. end_work — note normalization ─────────────────────────────────────────


class TestFromAC_EndWorkNormalization:
    """AC 2, 3, 5: end_work note normalized; guidance appended."""

    @pytest.mark.asyncio
    async def test_note_literal_backslash_n_normalized_before_engine_call(
        self, mock_view_ctx: tuple[AppContext, MagicMock]
    ) -> None:
        app_ctx, mock_view = mock_view_ctx
        await end_work(
            _make_ctx(app_ctx), id="1", outcome="success", note="done\\nmore"
        )
        note_passed = mock_view.end_work.call_args.kwargs["note"]
        assert note_passed == "done\nmore"

    @pytest.mark.asyncio
    async def test_guidance_appended_when_note_normalized(
        self, mock_view_ctx: tuple[AppContext, MagicMock]
    ) -> None:
        app_ctx, _ = mock_view_ctx
        result = await end_work(
            _make_ctx(app_ctx), id="1", outcome="success", note="done\\nmore"
        )
        assert _has_norm_guidance(result.guidance)

    @pytest.mark.asyncio
    async def test_escape_convention_note_preserved_as_single_backslash_n(
        self, mock_view_ctx: tuple[AppContext, MagicMock]
    ) -> None:
        app_ctx, mock_view = mock_view_ctx
        await end_work(
            _make_ctx(app_ctx), id="1", outcome="success", note="want\\\\nliteral"
        )
        note_passed = mock_view.end_work.call_args.kwargs["note"]
        assert note_passed == "want\\nliteral"


# ── 5. create_dr — body normalization ────────────────────────────────────────


class TestFromAC_CreateDrNormalization:
    """AC 2, 3, 4, 5: create_dr body normalized; guidance key in dict response."""

    @pytest.mark.asyncio
    async def test_body_literal_backslash_n_normalized_before_decisions_call(
        self, dr_ctx: AppContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict = {}
        monkeypatch.setattr(
            "owlbear_mcp_kanban.server.decisions",
            _fake_decisions(captured),
        )
        await create_dr(
            _make_ctx(dr_ctx),
            task_id="1",
            agent="test-agent",
            request_type="action",
            body="reason\\ndetail",
        )
        assert captured["body"] == "reason\ndetail"

    @pytest.mark.asyncio
    async def test_guidance_key_present_in_response_when_body_normalized(
        self, dr_ctx: AppContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict = {}
        monkeypatch.setattr(
            "owlbear_mcp_kanban.server.decisions",
            _fake_decisions(captured),
        )
        result = await create_dr(
            _make_ctx(dr_ctx),
            task_id="1",
            agent="test-agent",
            request_type="action",
            body="reason\\ndetail",
        )
        assert "guidance" in result
        assert isinstance(result["guidance"], list)
        assert _has_norm_guidance(result["guidance"])

    @pytest.mark.asyncio
    async def test_escape_convention_body_preserved_as_single_backslash_n(
        self, dr_ctx: AppContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # JSON `\\\\n` → Python `\\n` (double backslash+n); decisions call should
        # receive `\n` (single backslash+n).
        captured: dict = {}
        monkeypatch.setattr(
            "owlbear_mcp_kanban.server.decisions",
            _fake_decisions(captured),
        )
        await create_dr(
            _make_ctx(dr_ctx),
            task_id="1",
            agent="test-agent",
            request_type="action",
            body="want\\\\nliteral",
        )
        assert captured["body"] == "want\\nliteral"


# ── 6. Guidance positional ordering ──────────────────────────────────────────


class TestFromAC_GuidancePositioning:
    """AC 4: normalization guidance appended AFTER existing collect_guidance block;
    both existing reminders and normalization guidance appear when both conditions fire."""

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
        assert any(g == "existing reminder" for g in result.guidance)
        assert _has_norm_guidance(result.guidance)
        # Assert relative order: existing reminder must precede normalization guidance.
        existing_idx = next(i for i, g in enumerate(result.guidance) if g == "existing reminder")
        norm_idx = next(i for i, g in enumerate(result.guidance) if _NORM_SUBSTR in g)
        assert existing_idx < norm_idx, "normalization guidance must come AFTER existing guidance"

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
        result = await end_work(
            _make_ctx(app_ctx), id="1", outcome="success", note="done\\nmore"
        )
        assert any(g == "existing reminder" for g in result.guidance)
        assert _has_norm_guidance(result.guidance)
        # Assert relative order: existing reminder must precede normalization guidance.
        existing_idx = next(i for i, g in enumerate(result.guidance) if g == "existing reminder")
        norm_idx = next(i for i, g in enumerate(result.guidance) if _NORM_SUBSTR in g)
        assert existing_idx < norm_idx, "normalization guidance must come AFTER existing guidance"


# ── 7. Passthrough: no normalization when no literal \n in input ─────────────


class TestFromAC_PassthroughNoNormalization:
    """AC 6 (AC 5 in brief): when input has no literal \\n, no normalization occurs and no
    guidance is emitted. Each test imports _normalize_escaped_newlines directly so it fails
    with ImportError until the implementation ships (RED anchor)."""

    @pytest.mark.asyncio
    async def test_create_task_body_passthrough_no_normalization(
        self, mock_view_ctx: tuple[AppContext, MagicMock]
    ) -> None:
        from owlbear_mcp_kanban.server import _normalize_escaped_newlines  # RED anchor

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
        from owlbear_mcp_kanban.server import _normalize_escaped_newlines  # RED anchor

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
        from owlbear_mcp_kanban.server import _normalize_escaped_newlines  # RED anchor

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
        from owlbear_mcp_kanban.server import _normalize_escaped_newlines  # RED anchor

        _, changed = _normalize_escaped_newlines("clean note no escapes")
        assert not changed
        app_ctx, mock_view = mock_view_ctx
        result = await end_work(
            _make_ctx(app_ctx), id="1", outcome="success", note="clean note no escapes"
        )
        note_passed = mock_view.end_work.call_args.kwargs["note"]
        assert note_passed == "clean note no escapes"
        assert not _has_norm_guidance(result.guidance)

    @pytest.mark.asyncio
    async def test_create_dr_body_passthrough_no_normalization(
        self, dr_ctx: AppContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from owlbear_mcp_kanban.server import _normalize_escaped_newlines  # RED anchor

        _, changed = _normalize_escaped_newlines("clean body no escapes")
        assert not changed
        captured: dict = {}
        monkeypatch.setattr(
            "owlbear_mcp_kanban.server.decisions",
            _fake_decisions(captured),
        )
        result = await create_dr(
            _make_ctx(dr_ctx),
            task_id="1",
            agent="test-agent",
            request_type="action",
            body="clean body no escapes",
        )
        assert captured["body"] == "clean body no escapes"
        assert not _has_norm_guidance(result.get("guidance", []))


# ── 8. Tool descriptions — normalization documented ───────────────────────────


class TestFromAC_ToolDescriptions:
    """AC 7: tool descriptions for create_task, edit_task, end_work, create_dr
    document normalization behavior and the escape convention."""

    def _tool_text(self, tool_name: str) -> str:
        """Return the combined description text visible to agents for the tool."""
        import owlbear_mcp_kanban.server as _srv

        tool = next(
            t
            for t in _srv.mcp._tool_manager._tools.values()  # noqa: SLF001
            if t.name == tool_name
        )
        parts = [tool.description or ""]
        for prop in tool.parameters.get("properties", {}).values():
            parts.append(prop.get("description", ""))
        return " ".join(parts).lower()

    def test_create_task_description_mentions_normalize(self) -> None:
        assert "normalize" in self._tool_text("create_task")

    def test_edit_task_description_mentions_normalize(self) -> None:
        assert "normalize" in self._tool_text("edit_task")

    def test_end_work_description_mentions_normalize(self) -> None:
        assert "normalize" in self._tool_text("end_work")

    def test_create_dr_description_mentions_normalize(self) -> None:
        assert "normalize" in self._tool_text("create_dr")

    def test_create_task_description_mentions_escape_convention(self) -> None:
        # Escape convention: \\\\n in JSON preserves literal \n
        text = self._tool_text("create_task")
        assert "escape" in text or "\\\\n" in text or "literal" in text

    def test_edit_task_description_mentions_escape_convention(self) -> None:
        text = self._tool_text("edit_task")
        assert "escape" in text or "\\\\n" in text or "literal" in text


# ── 9. Durable regression gate ────────────────────────────────────────────────


class TestFromAC_ExistingDurableTestsUnchanged:
    """Refined AC 7: no new failures in tests/test_mcp_kanban.py beyond the two
    known pre-existing failures (both predate the normalization feature):
      - TestMergedFrom1360::test_server_module_line_count_reduced
        (720-line cap outdated after legitimate feature growth)
      - TestMergedFrom1197::test_server_1170_make_engine_mock_uses_noncallable_agent_view
        (referenced test_server_1170.py file no longer exists)
    Provides the falsifiable regression gate required by the reviewer.
    """

    def test_durable_mcp_kanban_suite_no_new_failures(self) -> None:
        """Run the durable MCP kanban suite excluding the two known pre-existing failures.

        Fails if the normalization feature introduced any regression in existing
        MCP kanban tool behaviors.
        """
        import os
        import subprocess
        import sys
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent
        # Strip PYTEST_DISABLE_PLUGIN_AUTOLOAD so the subprocess gets the full
        # plugin suite (pytest-asyncio, pytest-xdist, etc.).
        env = {k: v for k, v in os.environ.items() if k != "PYTEST_DISABLE_PLUGIN_AUTOLOAD"}
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_mcp_kanban.py",
                "--deselect=tests/test_mcp_kanban.py::TestMergedFrom1360::test_server_module_line_count_reduced",
                "--deselect=tests/test_mcp_kanban.py::TestMergedFrom1197::test_server_1170_make_engine_mock_uses_noncallable_agent_view",
                "--override-ini=addopts=",
                "-q",
                "--no-header",
                "--tb=short",
            ],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            env=env,
        )
        assert result.returncode == 0, (
            "Durable MCP kanban suite has unexpected failures — normalization feature "
            f"may have introduced a regression:\n{result.stdout}\n{result.stderr}"
        )
