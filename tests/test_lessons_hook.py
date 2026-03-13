"""Tests for LessonsInjectionHook — SESSION_START lessons context injection.

TDD RED phase for task #761 (core hook) and #751 (config, bootstrap, error handling).
Covers: constructor defaults, register on SESSION_START, mtime-sorted file reading,
token budget truncation, missing/empty directory handling, data population,
HookRegistry integration, never-raises error degradation, config setting, and
conditional bootstrap registration.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear.core.lessons_hook import LessonsInjectionHook

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(coro: object) -> object:
    """Convenience wrapper around asyncio.run for coroutines."""
    return asyncio.run(coro)  # type: ignore[arg-type]


def _session_data(session_id: str = "test-session") -> dict[str, object]:
    """Build a minimal SESSION_START payload."""
    return {"session_id": session_id}


def _write_md(path: Path, content: str, mtime: float) -> None:
    """Write a .md file and set its modification time."""
    path.write_text(content, encoding="utf-8")
    os.utime(path, (mtime, mtime))


# ---------------------------------------------------------------------------
# AC: Constructor accepts lessons_dir (Path) and max_tokens (int) with defaults
# ---------------------------------------------------------------------------


class TestFromACConstructor:
    """Constructor parameter handling and defaults."""

    def test_default_lessons_dir(self) -> None:
        hook = LessonsInjectionHook()
        assert hook.lessons_dir == Path(".owlbear/lessons")

    def test_default_max_tokens(self) -> None:
        hook = LessonsInjectionHook()
        assert hook.max_tokens == 500

    def test_custom_lessons_dir(self, tmp_path: Path) -> None:
        custom = tmp_path / "my-lessons"
        hook = LessonsInjectionHook(lessons_dir=custom)
        assert hook.lessons_dir == custom

    def test_custom_max_tokens(self) -> None:
        hook = LessonsInjectionHook(max_tokens=1000)
        assert hook.max_tokens == 1000

    def test_none_lessons_dir_uses_default(self) -> None:
        hook = LessonsInjectionHook(lessons_dir=None)
        assert hook.lessons_dir == Path(".owlbear/lessons")


# ---------------------------------------------------------------------------
# AC: register() hooks into SESSION_START
# ---------------------------------------------------------------------------


class TestFromACRegister:
    """register() attaches the hook to SESSION_START."""

    def test_register_adds_to_session_start(self) -> None:
        from owlbear.core.hooks import HookEvent, HookRegistry

        registry = HookRegistry()
        hook = LessonsInjectionHook()
        hook.register(registry)

        handlers = registry.handlers.get(HookEvent.SESSION_START, [])
        assert hook in handlers

    def test_register_does_not_add_to_other_events(self) -> None:
        from owlbear.core.hooks import HookEvent, HookRegistry

        registry = HookRegistry()
        hook = LessonsInjectionHook()
        hook.register(registry)

        for event in HookEvent:
            if event != HookEvent.SESSION_START:
                handlers = registry.handlers.get(event, [])
                assert hook not in handlers


# ---------------------------------------------------------------------------
# AC: __call__ reads .md files from lessons_dir sorted by mtime descending
# ---------------------------------------------------------------------------


class TestFromACMtimeSorting:
    """Files are read newest-first by mtime."""

    def test_newest_file_content_appears_first(self, tmp_path: Path) -> None:
        lessons_dir = tmp_path / "lessons"
        lessons_dir.mkdir()

        _write_md(lessons_dir / "old.md", "old-content", mtime=1000.0)
        _write_md(lessons_dir / "new.md", "new-content", mtime=2000.0)

        hook = LessonsInjectionHook(lessons_dir=lessons_dir, max_tokens=5000)
        data = _session_data()
        _run(hook(data))

        lessons: str = data["lessons"]  # type: ignore[index]
        # Newest content should appear before oldest
        assert lessons.index("new-content") < lessons.index("old-content")

    def test_three_files_ordered_by_mtime_desc(self, tmp_path: Path) -> None:
        lessons_dir = tmp_path / "lessons"
        lessons_dir.mkdir()

        _write_md(lessons_dir / "a.md", "AAA", mtime=1000.0)
        _write_md(lessons_dir / "b.md", "BBB", mtime=3000.0)
        _write_md(lessons_dir / "c.md", "CCC", mtime=2000.0)

        hook = LessonsInjectionHook(lessons_dir=lessons_dir, max_tokens=5000)
        data = _session_data()
        _run(hook(data))

        lessons: str = data["lessons"]  # type: ignore[index]
        assert lessons.index("BBB") < lessons.index("CCC") < lessons.index("AAA")

    def test_only_md_files_are_read(self, tmp_path: Path) -> None:
        lessons_dir = tmp_path / "lessons"
        lessons_dir.mkdir()

        _write_md(lessons_dir / "lesson.md", "md-content", mtime=2000.0)
        (lessons_dir / "notes.txt").write_text("txt-content", encoding="utf-8")

        hook = LessonsInjectionHook(lessons_dir=lessons_dir, max_tokens=5000)
        data = _session_data()
        _run(hook(data))

        lessons: str = data["lessons"]  # type: ignore[index]
        assert "md-content" in lessons
        assert "txt-content" not in lessons


# ---------------------------------------------------------------------------
# AC: concatenation stops when token budget (len(text)//4) is exhausted
# ---------------------------------------------------------------------------


class TestFromACTokenBudget:
    """Token budget enforcement using len(text)//4 approximation."""

    def test_single_file_within_budget_fully_included(self, tmp_path: Path) -> None:
        lessons_dir = tmp_path / "lessons"
        lessons_dir.mkdir()

        # 40 chars -> 10 tokens, budget is 500 -> fits easily
        _write_md(lessons_dir / "small.md", "x" * 40, mtime=1000.0)

        hook = LessonsInjectionHook(lessons_dir=lessons_dir, max_tokens=500)
        data = _session_data()
        _run(hook(data))

        assert data["lessons"] == "x" * 40  # type: ignore[index]

    def test_budget_exceeded_stops_adding_files(self, tmp_path: Path) -> None:
        lessons_dir = tmp_path / "lessons"
        lessons_dir.mkdir()

        # Budget: 10 tokens = 40 chars
        # File 1 (newest): 36 chars -> 9 tokens, fits
        # File 2 (oldest): 36 chars -> 9 tokens, would exceed budget
        _write_md(lessons_dir / "newest.md", "A" * 36, mtime=2000.0)
        _write_md(lessons_dir / "oldest.md", "B" * 36, mtime=1000.0)

        hook = LessonsInjectionHook(lessons_dir=lessons_dir, max_tokens=10)
        data = _session_data()
        _run(hook(data))

        lessons: str = data["lessons"]  # type: ignore[index]
        assert "A" * 36 in lessons
        # Second file should NOT be fully included since budget is exhausted
        assert len(lessons) // 4 <= 10

    def test_last_file_truncated_at_newline_boundary(self, tmp_path: Path) -> None:
        lessons_dir = tmp_path / "lessons"
        lessons_dir.mkdir()

        # Budget: 20 tokens = 80 chars
        # Newest file uses 40 chars (10 tokens) -> 10 tokens remain
        # Oldest file has lines: each ~20 chars. Budget allows ~40 more chars (10 tokens).
        # The truncation should happen at a newline boundary.
        newest_content = "A" * 40
        oldest_content = "line-one-is-here\nline-two-is-here\nline-three-here!\nline-four-here!!"
        _write_md(lessons_dir / "newest.md", newest_content, mtime=2000.0)
        _write_md(lessons_dir / "oldest.md", oldest_content, mtime=1000.0)

        hook = LessonsInjectionHook(lessons_dir=lessons_dir, max_tokens=20)
        data = _session_data()
        _run(hook(data))

        lessons: str = data["lessons"]  # type: ignore[index]
        # Total should not exceed budget
        assert len(lessons) // 4 <= 20
        # The truncated portion from oldest file should end at a newline boundary
        # (no partial lines)
        if oldest_content not in lessons:
            # If oldest was truncated, the included portion should end at a line break
            oldest_portion = lessons[len(newest_content) :]
            # Strip any separator that might exist between files
            oldest_portion = oldest_portion.lstrip()
            if oldest_portion:
                # Should not end mid-line
                lines = oldest_content.split("\n", maxsplit=2)
                assert oldest_portion.endswith(("\n", lines[0], lines[1]))

    def test_zero_budget_produces_empty_string(self, tmp_path: Path) -> None:
        lessons_dir = tmp_path / "lessons"
        lessons_dir.mkdir()

        _write_md(lessons_dir / "a.md", "content", mtime=1000.0)

        hook = LessonsInjectionHook(lessons_dir=lessons_dir, max_tokens=0)
        data = _session_data()
        _run(hook(data))

        assert data["lessons"] == ""  # type: ignore[index]

    def test_exact_budget_boundary(self, tmp_path: Path) -> None:
        lessons_dir = tmp_path / "lessons"
        lessons_dir.mkdir()

        # Exactly 100 tokens = 400 chars
        _write_md(lessons_dir / "exact.md", "x" * 400, mtime=1000.0)

        hook = LessonsInjectionHook(lessons_dir=lessons_dir, max_tokens=100)
        data = _session_data()
        _run(hook(data))

        lessons: str = data["lessons"]  # type: ignore[index]
        assert len(lessons) // 4 <= 100


# ---------------------------------------------------------------------------
# AC: missing/empty directory -> injects empty string, no error
# ---------------------------------------------------------------------------


class TestFromACMissingEmptyDir:
    """Graceful handling of missing or empty lessons directory."""

    def test_missing_directory_returns_empty_string(self, tmp_path: Path) -> None:
        nonexistent = tmp_path / "does-not-exist"
        hook = LessonsInjectionHook(lessons_dir=nonexistent)
        data = _session_data()
        _run(hook(data))

        assert data["lessons"] == ""  # type: ignore[index]

    def test_missing_directory_does_not_raise(self, tmp_path: Path) -> None:
        nonexistent = tmp_path / "does-not-exist"
        hook = LessonsInjectionHook(lessons_dir=nonexistent)
        data = _session_data()
        # Should not raise any exception
        _run(hook(data))

    def test_empty_directory_returns_empty_string(self, tmp_path: Path) -> None:
        lessons_dir = tmp_path / "empty-lessons"
        lessons_dir.mkdir()

        hook = LessonsInjectionHook(lessons_dir=lessons_dir)
        data = _session_data()
        _run(hook(data))

        assert data["lessons"] == ""  # type: ignore[index]

    def test_directory_with_only_non_md_files_returns_empty(self, tmp_path: Path) -> None:
        lessons_dir = tmp_path / "lessons"
        lessons_dir.mkdir()
        (lessons_dir / "notes.txt").write_text("content", encoding="utf-8")
        (lessons_dir / "data.json").write_text("{}", encoding="utf-8")

        hook = LessonsInjectionHook(lessons_dir=lessons_dir)
        data = _session_data()
        _run(hook(data))

        assert data["lessons"] == ""  # type: ignore[index]


# ---------------------------------------------------------------------------
# AC: data['lessons'] populated with concatenated lesson text
# ---------------------------------------------------------------------------


class TestFromACDataPopulation:
    """data['lessons'] is set with the concatenated lesson text."""

    def test_lessons_key_exists_after_call(self, tmp_path: Path) -> None:
        lessons_dir = tmp_path / "lessons"
        lessons_dir.mkdir()
        _write_md(lessons_dir / "a.md", "content", mtime=1000.0)

        hook = LessonsInjectionHook(lessons_dir=lessons_dir, max_tokens=5000)
        data = _session_data()
        _run(hook(data))

        assert "lessons" in data

    def test_lessons_key_is_string(self, tmp_path: Path) -> None:
        lessons_dir = tmp_path / "lessons"
        lessons_dir.mkdir()
        _write_md(lessons_dir / "a.md", "content", mtime=1000.0)

        hook = LessonsInjectionHook(lessons_dir=lessons_dir, max_tokens=5000)
        data = _session_data()
        _run(hook(data))

        assert isinstance(data["lessons"], str)  # type: ignore[index]

    def test_concatenation_includes_all_file_contents(self, tmp_path: Path) -> None:
        lessons_dir = tmp_path / "lessons"
        lessons_dir.mkdir()
        _write_md(lessons_dir / "first.md", "alpha", mtime=2000.0)
        _write_md(lessons_dir / "second.md", "bravo", mtime=1000.0)

        hook = LessonsInjectionHook(lessons_dir=lessons_dir, max_tokens=5000)
        data = _session_data()
        _run(hook(data))

        lessons: str = data["lessons"]  # type: ignore[index]
        assert "alpha" in lessons
        assert "bravo" in lessons

    def test_empty_dir_sets_lessons_to_empty_string(self, tmp_path: Path) -> None:
        lessons_dir = tmp_path / "lessons"
        lessons_dir.mkdir()

        hook = LessonsInjectionHook(lessons_dir=lessons_dir, max_tokens=5000)
        data = _session_data()
        _run(hook(data))

        assert data["lessons"] == ""  # type: ignore[index]


# ---------------------------------------------------------------------------
# AC: integration with HookRegistry (register + emit fires hook)
# ---------------------------------------------------------------------------


class TestFromACHookRegistryIntegration:
    """Full integration: register + emit fires the hook and populates data."""

    def test_emit_session_start_fires_hook(self, tmp_path: Path) -> None:
        from owlbear.core.hooks import HookEvent, HookRegistry

        lessons_dir = tmp_path / "lessons"
        lessons_dir.mkdir()
        _write_md(lessons_dir / "quick.md", "lesson-text", mtime=1000.0)

        registry = HookRegistry()
        hook = LessonsInjectionHook(lessons_dir=lessons_dir, max_tokens=5000)
        hook.register(registry)

        data = _session_data()
        _run(registry.emit(HookEvent.SESSION_START, data))

        assert "lessons" in data
        assert "lesson-text" in data["lessons"]  # type: ignore[index]

    def test_emit_populates_data_with_budget_enforcement(self, tmp_path: Path) -> None:
        from owlbear.core.hooks import HookEvent, HookRegistry

        lessons_dir = tmp_path / "lessons"
        lessons_dir.mkdir()
        # Budget: 5 tokens = 20 chars. File has 100 chars -> must be truncated
        _write_md(lessons_dir / "big.md", "Z" * 100, mtime=1000.0)

        registry = HookRegistry()
        hook = LessonsInjectionHook(lessons_dir=lessons_dir, max_tokens=5)
        hook.register(registry)

        data = _session_data()
        _run(registry.emit(HookEvent.SESSION_START, data))

        lessons: str = data["lessons"]  # type: ignore[index]
        assert len(lessons) // 4 <= 5

    def test_multiple_hooks_coexist(self, tmp_path: Path) -> None:
        """LessonsInjectionHook doesn't interfere with other SESSION_START hooks."""
        from owlbear.core.hooks import HookEvent, HookRegistry

        lessons_dir = tmp_path / "lessons"
        lessons_dir.mkdir()
        _write_md(lessons_dir / "a.md", "lesson-a", mtime=1000.0)

        registry = HookRegistry()

        # Register a simple marker hook first
        marker_called = []

        def marker_hook(_data: dict[str, object]) -> None:
            marker_called.append(True)

        registry.register(HookEvent.SESSION_START, marker_hook)

        hook = LessonsInjectionHook(lessons_dir=lessons_dir, max_tokens=5000)
        hook.register(registry)

        data = _session_data()
        _run(registry.emit(HookEvent.SESSION_START, data))

        assert len(marker_called) == 1
        assert "lessons" in data


# ---------------------------------------------------------------------------
# AC: Never raises — logs warning on read errors and degrades to empty string
# ---------------------------------------------------------------------------


class TestFromAC_NeverRaises:  # noqa: N801
    """Error resilience: read errors are logged and produce empty/partial output."""

    def test_unreadable_file_logs_warning_and_continues(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """One file fails to read; the other's content is still returned."""
        lessons_dir = tmp_path / "lessons"
        lessons_dir.mkdir()

        _write_md(lessons_dir / "good.md", "good-content", mtime=1000.0)
        bad = lessons_dir / "bad.md"
        _write_md(bad, "bad-content", mtime=2000.0)

        # Patch read_text on the bad file to raise
        original_read = Path.read_text

        _msg = "access denied"

        def _patched_read(self: Path, *args: object, **kwargs: object) -> str:
            if self.name == "bad.md":
                raise PermissionError(_msg)
            return original_read(self, *args, **kwargs)

        with patch.object(Path, "read_text", _patched_read), caplog.at_level(logging.WARNING):
            hook = LessonsInjectionHook(lessons_dir=lessons_dir, max_tokens=5000)
            data = _session_data()
            _run(hook(data))

        lessons: str = data["lessons"]  # type: ignore[index]
        assert "good-content" in lessons
        assert "bad-content" not in lessons
        assert any("warning" in r.levelname.lower() for r in caplog.records)

    def test_read_error_all_files_returns_empty(
        self,
        tmp_path: Path,
    ) -> None:
        """All files fail to read — result is empty string, no exception."""
        lessons_dir = tmp_path / "lessons"
        lessons_dir.mkdir()

        _write_md(lessons_dir / "a.md", "aaa", mtime=1000.0)
        _write_md(lessons_dir / "b.md", "bbb", mtime=2000.0)

        _msg = "disk error"

        def _always_fail(_self: Path, *_args: object, **_kwargs: object) -> str:
            raise OSError(_msg)

        with patch.object(Path, "read_text", _always_fail):
            hook = LessonsInjectionHook(lessons_dir=lessons_dir, max_tokens=5000)
            data = _session_data()
            _run(hook(data))  # must NOT raise

        assert data["lessons"] == ""  # type: ignore[index]

    def test_unicode_decode_error_logs_and_skips(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """A file with invalid encoding is skipped; remaining files succeed."""
        lessons_dir = tmp_path / "lessons"
        lessons_dir.mkdir()

        good = lessons_dir / "good.md"
        _write_md(good, "good-data", mtime=1000.0)
        bad = lessons_dir / "bad.md"
        bad.write_bytes(b"\xff\xfe invalid utf-8 \x80\x81")
        os.utime(bad, (2000.0, 2000.0))

        original_read = Path.read_text

        _codec = "utf-8"
        _reason = "invalid"

        def _patched_read(self: Path, *args: object, **kwargs: object) -> str:
            if self.name == "bad.md":
                raise UnicodeDecodeError(_codec, b"\x80", 0, 1, _reason)
            return original_read(self, *args, **kwargs)

        with patch.object(Path, "read_text", _patched_read), caplog.at_level(logging.WARNING):
            hook = LessonsInjectionHook(lessons_dir=lessons_dir, max_tokens=5000)
            data = _session_data()
            _run(hook(data))

        lessons: str = data["lessons"]  # type: ignore[index]
        assert "good-data" in lessons
        assert any("warning" in r.levelname.lower() for r in caplog.records)

    def test_stat_error_degrades_gracefully(
        self,
        tmp_path: Path,
    ) -> None:
        """If stat() fails during sorting, the hook degrades instead of raising."""
        lessons_dir = tmp_path / "lessons"
        lessons_dir.mkdir()

        _write_md(lessons_dir / "a.md", "content-a", mtime=1000.0)

        original_stat = Path.stat

        _msg = "stat failed"

        def _broken_stat(self: Path, *args: object, **kwargs: object) -> object:
            if self.suffix == ".md":
                raise OSError(_msg)
            return original_stat(self, *args, **kwargs)

        with patch.object(Path, "stat", _broken_stat):
            hook = LessonsInjectionHook(lessons_dir=lessons_dir, max_tokens=5000)
            data = _session_data()
            _run(hook(data))  # must NOT raise

        # Degraded result — either empty or partial, but no crash
        assert isinstance(data["lessons"], str)  # type: ignore[index]


# ---------------------------------------------------------------------------
# AC: settings.lessons_injection_enabled: bool = False in OwlBearSettings
# ---------------------------------------------------------------------------


class TestFromAC_LessonsConfig:  # noqa: N801
    """Config field: lessons_injection_enabled defaults False, can be toggled."""

    def test_setting_defaults_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from owlbear.config import OwlBearSettings

        for var in [k for k in os.environ if k.startswith("OWLBEAR_")]:
            monkeypatch.delenv(var, raising=False)

        settings = OwlBearSettings()
        assert hasattr(settings, "lessons_injection_enabled"), (
            "OwlBearSettings must have lessons_injection_enabled field"
        )
        assert settings.lessons_injection_enabled is False

    def test_setting_can_enable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from owlbear.config import OwlBearSettings

        for var in [k for k in os.environ if k.startswith("OWLBEAR_")]:
            monkeypatch.delenv(var, raising=False)

        settings = OwlBearSettings(lessons_injection_enabled=True)
        assert settings.lessons_injection_enabled is True

    def test_setting_via_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from owlbear.config import OwlBearSettings

        for var in [k for k in os.environ if k.startswith("OWLBEAR_")]:
            monkeypatch.delenv(var, raising=False)

        monkeypatch.setenv("OWLBEAR_LESSONS_INJECTION_ENABLED", "true")
        settings = OwlBearSettings()
        assert settings.lessons_injection_enabled is True


# ---------------------------------------------------------------------------
# AC: Conditionally registered in bootstrap/hooks.py when enabled
# ---------------------------------------------------------------------------


class TestFromAC_BootstrapRegistration:  # noqa: N801
    """LessonsInjectionHook registered in build_hooks() only when enabled."""

    def _count_lessons_hooks(self, hooks: object) -> int:
        """Count LessonsInjectionHook instances in SESSION_START handlers."""
        from owlbear.core.hooks import HookEvent

        handlers = hooks.handlers.get(HookEvent.SESSION_START, [])  # type: ignore[attr-defined]
        return sum(1 for h in handlers if isinstance(h, LessonsInjectionHook))

    def test_build_hooks_registers_when_enabled(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from owlbear.bootstrap.hooks import build_hooks
        from owlbear.config import OwlBearSettings

        for var in [k for k in os.environ if k.startswith("OWLBEAR_")]:
            monkeypatch.delenv(var, raising=False)

        settings = OwlBearSettings(lessons_injection_enabled=True)
        hooks, _ = build_hooks(settings, workspace_root=None)

        assert self._count_lessons_hooks(hooks) >= 1, (
            "LessonsInjectionHook must be registered on SESSION_START when enabled"
        )

    def test_build_hooks_skips_when_disabled(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from owlbear.bootstrap.hooks import build_hooks
        from owlbear.config import OwlBearSettings

        for var in [k for k in os.environ if k.startswith("OWLBEAR_")]:
            monkeypatch.delenv(var, raising=False)

        settings = OwlBearSettings(lessons_injection_enabled=False)
        hooks, _ = build_hooks(settings, workspace_root=None)

        assert self._count_lessons_hooks(hooks) == 0, (
            "LessonsInjectionHook must NOT be registered when disabled"
        )
