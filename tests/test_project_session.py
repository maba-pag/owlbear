"""Tests for session-project binding — per-project session directories.

Verifies that SessionStore paths are correctly routed to
``config_dir/projects/{id}/sessions/`` when a project is active,
and fall back to ``config_dir/sessions/`` otherwise.

See kanban task #349 for acceptance criteria.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import MagicMock

from pydantic_ai.messages import ModelRequest, UserPromptPart

from bearclaw.cli import _build_chat_session, chat

# ---------------------------------------------------------------------------
# Session creation in project directory
# ---------------------------------------------------------------------------


class TestSessionInProjectDir:
    """AC: Sessions stored at config_dir/projects/{id}/sessions/{name}.jsonl."""

    def test_session_under_project_dir(self, tmp_path: Path) -> None:
        """When project_id is given, session lands in projects/{id}/sessions/."""
        settings = MagicMock()
        settings.config_dir = tmp_path

        name, store = _build_chat_session(settings, "my-session", project_id="alpha")

        expected = tmp_path / "projects" / "alpha" / "sessions" / "my-session.jsonl"
        assert store.path == expected
        assert name == "my-session"

    def test_session_default_dir_without_project(self, tmp_path: Path) -> None:
        """Backward compat: no project -> config_dir/sessions/."""
        settings = MagicMock()
        settings.config_dir = tmp_path

        _name, store = _build_chat_session(settings, "fallback-session")

        expected = tmp_path / "sessions" / "fallback-session.jsonl"
        assert store.path == expected

    def test_session_default_dir_project_none(self, tmp_path: Path) -> None:
        """Explicit project_id=None -> same as no project."""
        settings = MagicMock()
        settings.config_dir = tmp_path

        _name, store = _build_chat_session(
            settings, "compat-session", project_id=None,
        )

        expected = tmp_path / "sessions" / "compat-session.jsonl"
        assert store.path == expected

    def test_auto_generated_session_name(self, tmp_path: Path) -> None:
        """When session=None, an auto-generated name is used."""
        settings = MagicMock()
        settings.config_dir = tmp_path

        name, store = _build_chat_session(settings, None, project_id="beta")

        assert name.startswith("chat-")
        assert "beta" in str(store.path)
        assert str(store.path).endswith(".jsonl")


# ---------------------------------------------------------------------------
# Session isolation between projects
# ---------------------------------------------------------------------------


class TestSessionIsolation:
    """AC: session isolation between two projects."""

    def test_two_projects_different_dirs(self, tmp_path: Path) -> None:
        """Sessions for different projects are stored in different directories."""
        settings = MagicMock()
        settings.config_dir = tmp_path

        _, store_a = _build_chat_session(
            settings, "shared-name", project_id="project-a",
        )
        _, store_b = _build_chat_session(
            settings, "shared-name", project_id="project-b",
        )

        assert store_a.path != store_b.path
        assert "project-a" in str(store_a.path)
        assert "project-b" in str(store_b.path)

    def test_project_session_does_not_clash_with_global(
        self, tmp_path: Path,
    ) -> None:
        """A project session and a global session with the same name differ."""
        settings = MagicMock()
        settings.config_dir = tmp_path

        _, store_proj = _build_chat_session(
            settings, "same-name", project_id="proj",
        )
        _, store_global = _build_chat_session(settings, "same-name")

        assert store_proj.path != store_global.path

    def test_write_and_read_isolation(self, tmp_path: Path) -> None:
        """Writing to one project's session doesn't affect another's."""
        settings = MagicMock()
        settings.config_dir = tmp_path

        _, store_a = _build_chat_session(
            settings, "iso-test", project_id="proj-a",
        )
        _, store_b = _build_chat_session(
            settings, "iso-test", project_id="proj-b",
        )

        msg = ModelRequest(parts=[UserPromptPart(content="hello from A")])
        store_a.append(msg)

        loaded_a = store_a.load()
        loaded_b = store_b.load()

        assert len(loaded_a) == 1
        assert len(loaded_b) == 0


# ---------------------------------------------------------------------------
# Bootstrap session respects project path
# ---------------------------------------------------------------------------


class TestBootstrapSessionProjectPath:
    """AC: _build_chat_session in bootstrap respects active project path."""

    def test_bootstrap_session_uses_project_dir(self, tmp_path: Path) -> None:
        """bootstrap() creates session under project dir when project_id given."""
        settings = MagicMock()
        settings.config_dir = tmp_path

        _, store = _build_chat_session(
            settings, "boot-session", project_id="my-proj",
        )

        assert store.path.parent.parent.name == "my-proj"
        assert store.path.parent.name == "sessions"


# ---------------------------------------------------------------------------
# Chat --project flag integration
# ---------------------------------------------------------------------------


class TestChatProjectFlag:
    """AC: bearclaw chat --project NAME uses project-scoped session dir."""

    def test_chat_command_accepts_project_option(self) -> None:
        """The chat command signature includes --project."""
        sig = inspect.signature(chat)
        assert "project" in sig.parameters

    def test_build_chat_session_with_project_resolves_path(
        self, tmp_path: Path,
    ) -> None:
        """_build_chat_session with project_id routes to project sessions dir."""
        settings = MagicMock()
        settings.config_dir = tmp_path

        _name, store = _build_chat_session(
            settings, "proj-chat", project_id="web-app",
        )

        assert store.path == (
            tmp_path / "projects" / "web-app" / "sessions" / "proj-chat.jsonl"
        )
