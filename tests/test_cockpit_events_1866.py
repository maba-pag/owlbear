from __future__ import annotations

"""Smoke tests for #1866: derive archive_dir from board_config in events.py.

AC coverage:
  AC1: KanbanEngine exposes a public read-only archive_dir property returning Path,
       delegating to self._archive_dir (mirrors tasks_dir pattern at engine.py:518)
  AC2: events.py _stream() resolves archive_dir via engine.archive_dir — removes
       the hardcoded kanban_dir / "archive" literal
  AC3: Default config path is unchanged — regression guard ensuring existing
       test_cockpit_events.py and test_cockpit_cache_sse.py assumptions hold

All tests FAIL until the builder implements:
  serve/kanban/src/owlbear_kanban/engine.py (archive_dir property)
  serve/cockpit/src/owlbear_cockpit/routes/events.py (consume engine.archive_dir)
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from owlbear_kanban import KanbanEngine


_CONFIG_YAML = """\
statuses:
    - todo
    - done
priorities:
    - normal
entry_status: todo
terminal_status: done
wave_size: 4
agent_map:
    todo: builder
    done: auditor
agent_types: {}
agent_compatibility: {}
non_impl_tags: [research]
archival_reasons: [completed]
status_predicates: {}
claim_timeout: 1h
next_id: 1
"""


def _make_board(base_dir: Path, config_yaml: str = _CONFIG_YAML) -> Path:
    """Create a minimal kanban board directory and return kanban_dir."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(config_yaml, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


class TestFromAC_EngineArchiveDirProperty:
    """AC1: KanbanEngine.archive_dir — public read-only property returning Path."""

    def test_engine_exposes_archive_dir_property(self, tmp_path: Path) -> None:
        """engine.archive_dir must return a Path equal to kanban_dir / 'archive' (default)."""
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        result = engine.archive_dir
        assert isinstance(result, Path), f"archive_dir must return Path, got {type(result)}"
        assert result == kanban_dir / "archive"


class TestFromAC_EventsUsesEngineArchiveDir:
    """AC2: events.py _stream() uses engine.archive_dir, not hardcoded kanban_dir/'archive'."""

    def test_stream_uses_engine_archive_dir_not_hardcoded(self, tmp_path: Path) -> None:
        """_stream() must derive archive_dir from engine.archive_dir, not kanban_dir/'archive'."""
        from fastapi.testclient import TestClient  # noqa: PLC0415
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        import owlbear_cockpit.routes.events as events_module  # noqa: PLC0415

        kanban_dir = tmp_path / "board"
        kanban_dir.mkdir(parents=True, exist_ok=True)
        custom_archive = kanban_dir / "custom_archive"  # non-default — different from "archive"

        mock_engine = MagicMock()
        mock_engine.kanban_dir = kanban_dir
        mock_engine.tasks_dir = kanban_dir / "tasks"
        mock_engine.archive_dir = custom_archive

        captured: dict[str, Path] = {}
        original_bwf = events_module._build_watch_filter

        def capturing_bwf(
            tasks_dir: Path,
            archive_dir: Path,
            *args: object,
            **kwargs: object,
        ) -> object:
            captured["archive_dir"] = archive_dir
            return original_bwf(tasks_dir, archive_dir, *args, **kwargs)

        async def _noop_awatch(*_a: object, **_kw: object) -> object:
            return
            yield  # pragma: no cover — keeps this a valid async generator

        app.dependency_overrides[get_engine] = lambda: mock_engine
        try:
            with (
                patch("owlbear_cockpit.routes.events.awatch", _noop_awatch),
                patch("owlbear_cockpit.routes.events._build_watch_filter", capturing_bwf),
                TestClient(app, raise_server_exceptions=False) as client,
            ):
                client.get("/api/events")
        finally:
            app.dependency_overrides.clear()

        expected = custom_archive.resolve()
        assert captured.get("archive_dir") == expected, (
            f"_stream() must use engine.archive_dir={expected}, "
            f"but _build_watch_filter received archive_dir={captured.get('archive_dir')}"
        )


class TestFromAC_DefaultConfigPathUnchanged:
    """AC3: Regression guard — default archive_dir must equal kanban_dir / 'archive'."""

    def test_default_archive_dir_matches_existing_hardcoded_path(self, tmp_path: Path) -> None:
        """engine.archive_dir with default config must equal kanban_dir / 'archive'.

        Regression guard: existing tests in test_cockpit_events.py and
        test_cockpit_cache_sse.py create boards with the default 'archive' subdir.
        After the fix, engine.archive_dir must return the same path so those tests
        remain valid without modification.
        """
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        expected = kanban_dir / "archive"
        assert engine.archive_dir == expected, (
            f"Default archive_dir must be kanban_dir / 'archive' = {expected}, got {engine.archive_dir}"
        )
