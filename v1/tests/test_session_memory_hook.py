"""Tests for SessionMemoryHook — TDD RED phase for task #622.

Tests the contract described in the AC:
- SessionMemoryHook registers on SESSION_END, extracts messages, calls
  summarizer, writes to .owlbear/session-memory.md
- Graceful degradation on summarizer failure
- ContextManager.instructions reads session-memory.md when present
- session_memory_enabled config in OwlBearSettings
- Bootstrap wiring guarded by config
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

# ---------------------------------------------------------------------------
# SessionMemoryHook — core hook behaviour
# ---------------------------------------------------------------------------


class TestFromAC_SessionMemoryHook:
    """AC lines 1-8: SessionMemoryHook class, constructor, register,
    SESSION_END handler, empty-messages edge case, graceful degradation,
    and directory creation."""

    def test_import_and_instantiate(self, tmp_path: Path) -> None:
        """AC-1: SessionMemoryHook importable from owlbear.core.session_memory_hook."""
        from owlbear.core.session_memory_hook import SessionMemoryHook

        summarizer = AsyncMock(return_value="summary")
        hook = SessionMemoryHook(workspace_root=tmp_path, summarizer=summarizer)
        assert hook is not None

    def test_constructor_accepts_workspace_and_summarizer(self, tmp_path: Path) -> None:
        """AC-2: Constructor takes workspace_root: Path and summarizer callable."""
        from owlbear.core.session_memory_hook import SessionMemoryHook

        async def fake_summarizer(_text: str) -> str:
            return "summary"

        hook = SessionMemoryHook(workspace_root=tmp_path, summarizer=fake_summarizer)
        # Verify the hook stored the workspace root — no implementation detail
        # about internal attrs, just that it was accepted without error.
        assert hook is not None

    def test_register_hooks_session_end_only(self, tmp_path: Path) -> None:
        """AC-3: register() registers handler on SESSION_END only."""
        from owlbear.core.hooks import HookEvent, HookRegistry
        from owlbear.core.session_memory_hook import SessionMemoryHook

        hooks = HookRegistry()
        summarizer = AsyncMock(return_value="summary")
        hook = SessionMemoryHook(workspace_root=tmp_path, summarizer=summarizer)
        hook.register(hooks)

        # SESSION_END must have exactly one handler
        assert len(hooks.handlers.get(HookEvent.SESSION_END, [])) == 1

        # No other events should have handlers from this hook
        for event in HookEvent:
            if event != HookEvent.SESSION_END:
                handlers = hooks.handlers.get(event, [])
                assert len(handlers) == 0, f"Unexpected handler on {event}"

    @pytest.mark.asyncio
    async def test_session_end_writes_summary_file(self, tmp_path: Path) -> None:
        """AC-4: On SESSION_END, extract messages, call summarizer, write file."""
        from owlbear.core.session_memory_hook import SessionMemoryHook

        summary_text = "## Key Decisions\n- Used DI\n## Active Tasks\n- #622"
        summarizer = AsyncMock(return_value=summary_text)

        hook = SessionMemoryHook(workspace_root=tmp_path, summarizer=summarizer)

        data = {
            "session_id": "test-session",
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
            ],
        }
        await hook(data)

        output_path = tmp_path / ".owlbear" / "session-memory.md"
        assert output_path.exists(), "session-memory.md was not written"
        content = output_path.read_text(encoding="utf-8")
        assert summary_text in content

    @pytest.mark.asyncio
    async def test_summarizer_receives_serialised_messages(self, tmp_path: Path) -> None:
        """AC-4/6: Hook serialises messages to text before calling summarizer."""
        from owlbear.core.session_memory_hook import SessionMemoryHook

        summarizer = AsyncMock(return_value="summary")
        hook = SessionMemoryHook(workspace_root=tmp_path, summarizer=summarizer)

        messages = [
            {"role": "user", "content": "What is X?"},
            {"role": "assistant", "content": "X is Y."},
        ]
        data = {"session_id": "s1", "messages": messages}
        await hook(data)

        # Summarizer must be called exactly once with a string (not a list)
        summarizer.assert_called_once()
        call_arg = summarizer.call_args[0][0]
        assert isinstance(call_arg, str), "Summarizer should receive a string, not raw messages"
        # The serialised text should contain the message content
        assert "What is X?" in call_arg
        assert "X is Y." in call_arg

    @pytest.mark.asyncio
    async def test_empty_messages_skips_persist(self, tmp_path: Path) -> None:
        """AC-5: Empty messages list → no file written, no error."""
        from owlbear.core.session_memory_hook import SessionMemoryHook

        summarizer = AsyncMock(return_value="summary")
        hook = SessionMemoryHook(workspace_root=tmp_path, summarizer=summarizer)

        data = {"session_id": "s1", "messages": []}
        await hook(data)

        output_path = tmp_path / ".owlbear" / "session-memory.md"
        assert not output_path.exists(), "File should not be written for empty messages"
        summarizer.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_messages_key_skips_persist(self, tmp_path: Path) -> None:
        """AC-5: Missing 'messages' key in data → no file written, no error."""
        from owlbear.core.session_memory_hook import SessionMemoryHook

        summarizer = AsyncMock(return_value="summary")
        hook = SessionMemoryHook(workspace_root=tmp_path, summarizer=summarizer)

        data = {"session_id": "s1"}
        await hook(data)

        output_path = tmp_path / ".owlbear" / "session-memory.md"
        assert not output_path.exists(), "File should not be written when messages key missing"
        summarizer.assert_not_called()

    @pytest.mark.asyncio
    async def test_summarizer_failure_logs_warning_no_raise(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """AC-7: Summarizer failure → logger.warning(), never raise."""
        from owlbear.core.session_memory_hook import SessionMemoryHook

        summarizer = AsyncMock(side_effect=RuntimeError("LLM unavailable"))
        hook = SessionMemoryHook(workspace_root=tmp_path, summarizer=summarizer)

        data = {
            "session_id": "s1",
            "messages": [{"role": "user", "content": "test"}],
        }

        with caplog.at_level(logging.WARNING):
            # Must not raise
            await hook(data)

        # Should have logged a warning
        assert any("warning" in r.levelname.lower() for r in caplog.records), (
            "Expected a WARNING log when summarizer fails"
        )

        # File should NOT be written on failure
        output_path = tmp_path / ".owlbear" / "session-memory.md"
        assert not output_path.exists()

    @pytest.mark.asyncio
    async def test_creates_owlbear_directory_if_missing(self, tmp_path: Path) -> None:
        """AC-8: .owlbear/ directory created with mkdir(parents=True, exist_ok=True)."""
        from owlbear.core.session_memory_hook import SessionMemoryHook

        # Ensure .owlbear does NOT exist
        owlbear_dir = tmp_path / ".owlbear"
        assert not owlbear_dir.exists()

        summarizer = AsyncMock(return_value="summary text")
        hook = SessionMemoryHook(workspace_root=tmp_path, summarizer=summarizer)

        data = {
            "session_id": "s1",
            "messages": [{"role": "user", "content": "hello"}],
        }
        await hook(data)

        assert owlbear_dir.exists(), ".owlbear directory should have been created"
        assert (owlbear_dir / "session-memory.md").exists()

    @pytest.mark.asyncio
    async def test_owlbear_directory_already_exists(self, tmp_path: Path) -> None:
        """AC-8 boundary: .owlbear/ already exists → no error (exist_ok=True)."""
        from owlbear.core.session_memory_hook import SessionMemoryHook

        owlbear_dir = tmp_path / ".owlbear"
        owlbear_dir.mkdir()

        summarizer = AsyncMock(return_value="summary text")
        hook = SessionMemoryHook(workspace_root=tmp_path, summarizer=summarizer)

        data = {
            "session_id": "s1",
            "messages": [{"role": "user", "content": "hi"}],
        }
        await hook(data)

        assert (owlbear_dir / "session-memory.md").exists()

    @pytest.mark.asyncio
    async def test_overwrites_existing_session_memory(self, tmp_path: Path) -> None:
        """Boundary: existing session-memory.md is overwritten, not appended."""
        from owlbear.core.session_memory_hook import SessionMemoryHook

        owlbear_dir = tmp_path / ".owlbear"
        owlbear_dir.mkdir()
        existing_file = owlbear_dir / "session-memory.md"
        existing_file.write_text("old content", encoding="utf-8")

        summarizer = AsyncMock(return_value="new summary")
        hook = SessionMemoryHook(workspace_root=tmp_path, summarizer=summarizer)

        data = {
            "session_id": "s2",
            "messages": [{"role": "user", "content": "update"}],
        }
        await hook(data)

        content = existing_file.read_text(encoding="utf-8")
        assert "old content" not in content
        assert "new summary" in content


# ---------------------------------------------------------------------------
# ContextManager — session-memory restore
# ---------------------------------------------------------------------------


class TestFromAC_ContextManagerSessionRestore:
    """AC lines 9-10: ContextManager.instructions reads session-memory.md."""

    def test_instructions_includes_session_memory(self, tmp_path: Path) -> None:
        """AC-9: instructions includes .owlbear/session-memory.md when present."""
        from owlbear.memory.context import ContextManager

        # Create the context.md so there's a base
        (tmp_path / "context.md").write_text("base context", encoding="utf-8")

        # Create session-memory.md
        owlbear_dir = tmp_path / ".owlbear"
        owlbear_dir.mkdir()
        (owlbear_dir / "session-memory.md").write_text(
            "## Key Decisions\n- Used hook pattern",
            encoding="utf-8",
        )

        mgr = ContextManager(tmp_path)
        instructions = mgr.instructions

        assert "base context" in instructions
        assert "Key Decisions" in instructions
        assert "Used hook pattern" in instructions

    def test_session_memory_after_memory_md(self, tmp_path: Path) -> None:
        """AC-9 boundary: session-memory content appears after MEMORY.md."""
        from owlbear.memory.context import ContextManager

        (tmp_path / "context.md").write_text("context", encoding="utf-8")
        (tmp_path / "MEMORY.md").write_text("persistent memory", encoding="utf-8")
        owlbear_dir = tmp_path / ".owlbear"
        owlbear_dir.mkdir()
        (owlbear_dir / "session-memory.md").write_text("session recall", encoding="utf-8")

        mgr = ContextManager(tmp_path)
        instructions = mgr.instructions

        # All three sources must be present
        assert "context" in instructions
        assert "persistent memory" in instructions
        assert "session recall" in instructions

        # session-memory must appear after MEMORY.md
        mem_pos = instructions.index("persistent memory")
        sess_pos = instructions.index("session recall")
        assert sess_pos > mem_pos, "session-memory should appear after MEMORY.md"

    def test_instructions_without_session_memory_still_works(self, tmp_path: Path) -> None:
        """AC-10: Missing session-memory.md silently skipped.

        ContextManager must have the code path that checks for session-memory.md
        but gracefully handles absence. We verify the new attribute/property
        that signals session memory support exists.
        """
        from owlbear.memory.context import ContextManager

        (tmp_path / "context.md").write_text("base context", encoding="utf-8")
        (tmp_path / "MEMORY.md").write_text("memory content", encoding="utf-8")
        # No .owlbear/session-memory.md

        mgr = ContextManager(tmp_path)
        instructions = mgr.instructions

        assert "base context" in instructions
        assert "memory content" in instructions
        # The new code path for reading session-memory.md must exist.
        # Verify by checking ContextManager source has session-memory logic.
        import inspect

        src = inspect.getsource(type(mgr))
        assert "session-memory" in src or "session_memory" in src, (
            "ContextManager must contain session-memory logic"
        )


# ---------------------------------------------------------------------------
# Config — session_memory_enabled setting
# ---------------------------------------------------------------------------


class TestFromAC_SessionMemoryConfig:
    """AC line 11: session_memory_enabled in OwlBearSettings."""

    def test_setting_defaults_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """AC-11: session_memory_enabled defaults to False."""
        from owlbear.config import OwlBearSettings

        # Clear any env vars that might interfere
        for var in [k for k in os.environ if k.startswith("OWLBEAR_")]:
            monkeypatch.delenv(var, raising=False)

        settings = OwlBearSettings()
        assert hasattr(settings, "session_memory_enabled"), (
            "OwlBearSettings must have session_memory_enabled field"
        )
        assert settings.session_memory_enabled is False

    def test_setting_can_enable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """AC-11: session_memory_enabled can be set to True."""
        from owlbear.config import OwlBearSettings

        for var in [k for k in os.environ if k.startswith("OWLBEAR_")]:
            monkeypatch.delenv(var, raising=False)

        settings = OwlBearSettings(session_memory_enabled=True)
        assert settings.session_memory_enabled is True

    def test_setting_via_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """AC-11 boundary: setting is controllable via OWLBEAR_ env var."""
        from owlbear.config import OwlBearSettings

        for var in [k for k in os.environ if k.startswith("OWLBEAR_")]:
            monkeypatch.delenv(var, raising=False)

        monkeypatch.setenv("OWLBEAR_SESSION_MEMORY_ENABLED", "true")
        settings = OwlBearSettings()
        assert settings.session_memory_enabled is True


# ---------------------------------------------------------------------------
# Bootstrap wiring — guarded by config
# ---------------------------------------------------------------------------


class TestFromAC_SessionMemoryBootstrap:
    """AC lines 12-13: Bootstrap wiring in __init__.py, guarded by config."""

    def test_wire_post_model_hooks_registers_when_enabled(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC-12/13: _wire_post_model_hooks registers SessionMemoryHook on
        SESSION_END when session_memory_enabled=True."""
        from unittest.mock import MagicMock

        from owlbear.bootstrap import _wire_post_model_hooks
        from owlbear.config import OwlBearSettings
        from owlbear.core.hooks import HookEvent, HookRegistry

        for var in [k for k in os.environ if k.startswith("OWLBEAR_")]:
            monkeypatch.delenv(var, raising=False)

        settings = OwlBearSettings(session_memory_enabled=True)
        model = MagicMock()  # fake Model
        hooks = HookRegistry()

        _wire_post_model_hooks(settings, model, tmp_path, hooks, ingest_pipeline=None)

        session_end_handlers = hooks.handlers.get(HookEvent.SESSION_END, [])
        assert len(session_end_handlers) >= 1, (
            "SessionMemoryHook should be registered on SESSION_END via bootstrap"
        )

    def test_wire_post_model_hooks_skips_when_disabled(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC-13: _wire_post_model_hooks does NOT register SessionMemoryHook
        when session_memory_enabled=False (default)."""
        from unittest.mock import MagicMock

        from owlbear.bootstrap import _wire_post_model_hooks
        from owlbear.config import OwlBearSettings
        from owlbear.core.hooks import HookEvent, HookRegistry

        for var in [k for k in os.environ if k.startswith("OWLBEAR_")]:
            monkeypatch.delenv(var, raising=False)

        settings = OwlBearSettings(session_memory_enabled=False)
        model = MagicMock()
        hooks = HookRegistry()

        _wire_post_model_hooks(settings, model, tmp_path, hooks, ingest_pipeline=None)

        session_end_handlers = hooks.handlers.get(HookEvent.SESSION_END, [])
        assert len(session_end_handlers) == 0, (
            "No SessionMemoryHook should be registered when disabled"
        )

    def test_wire_session_memory_hook_registers_session_end(
        self,
        tmp_path: Path,
    ) -> None:
        """AC-12: _wire_session_memory_hook creates and registers the hook."""
        from unittest.mock import MagicMock

        from owlbear.bootstrap import _wire_session_memory_hook
        from owlbear.core.hooks import HookEvent, HookRegistry

        model = MagicMock()
        hooks = HookRegistry()

        _wire_session_memory_hook(model, tmp_path, hooks)

        session_end_handlers = hooks.handlers.get(HookEvent.SESSION_END, [])
        assert len(session_end_handlers) == 1
