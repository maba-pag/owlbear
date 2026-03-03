"""Tests for bearclaw project CLI subcommands.

TDD red-phase: tests define expected behavior of the project subcommand group
(create, list, switch, archive) using CliRunner and tmp_path-backed ProjectStore.

See kanban task #348 for acceptance criteria.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from bearclaw.cli import app

runner = CliRunner()


@pytest.fixture
def _mock_settings(tmp_path: Path):
    """Patch OwlBearSettings so config_dir and project_root point at tmp_path."""
    mock_settings = MagicMock()
    mock_settings.config_dir = tmp_path
    mock_settings.project_root = tmp_path / "project-root"
    with patch("bearclaw.cli.OwlBearSettings", return_value=mock_settings):
        yield tmp_path


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------


class TestProjectHelp:
    """The 'project' subcommand group appears in CLI help."""

    def test_project_in_main_help(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "project" in result.output

    def test_project_help_lists_subcommands(self) -> None:
        result = runner.invoke(app, ["project", "--help"])
        assert result.exit_code == 0
        assert "create" in result.output
        assert "list" in result.output
        assert "switch" in result.output
        assert "archive" in result.output


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestProjectCreate:
    """bearclaw project create --name NAME --workspace PATH."""

    @pytest.mark.usefixtures("_mock_settings")
    def test_create_success(self, tmp_path: Path) -> None:
        ws = str(tmp_path / "workspace")
        result = runner.invoke(
            app, ["project", "create", "--name", "My Project", "--workspace", ws]
        )
        assert result.exit_code == 0
        assert "My Project" in result.output

    @pytest.mark.usefixtures("_mock_settings")
    def test_create_default_workspace_is_cwd(self) -> None:
        """When --workspace is omitted, CWD is used."""
        result = runner.invoke(app, ["project", "create", "--name", "CWD Project"])
        assert result.exit_code == 0
        assert "CWD Project" in result.output

    @pytest.mark.usefixtures("_mock_settings")
    def test_create_duplicate_name_errors(self, tmp_path: Path) -> None:
        ws = str(tmp_path / "workspace")
        runner.invoke(app, ["project", "create", "--name", "Dup", "--workspace", ws])
        result = runner.invoke(
            app, ["project", "create", "--name", "Dup", "--workspace", ws]
        )
        assert result.exit_code == 1
        assert "already exists" in result.output

    @pytest.mark.usefixtures("_mock_settings")
    def test_create_persists_json_file(self, tmp_path: Path) -> None:
        ws = str(tmp_path / "workspace")
        runner.invoke(
            app, ["project", "create", "--name", "Persisted", "--workspace", ws]
        )
        projects_dir = tmp_path / "projects"
        json_files = list(projects_dir.glob("*.json"))
        assert len(json_files) == 1


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


class TestProjectList:
    """bearclaw project list — table of projects."""

    @pytest.mark.usefixtures("_mock_settings")
    def test_list_shows_active_project(self, tmp_path: Path) -> None:
        ws = str(tmp_path / "workspace")
        runner.invoke(
            app, ["project", "create", "--name", "Listed", "--workspace", ws]
        )
        result = runner.invoke(app, ["project", "list"])
        assert result.exit_code == 0
        assert "Listed" in result.output

    @pytest.mark.usefixtures("_mock_settings")
    def test_list_hides_archived_by_default(self, tmp_path: Path) -> None:
        ws = str(tmp_path / "workspace")
        runner.invoke(
            app, ["project", "create", "--name", "Hidden", "--workspace", ws]
        )
        runner.invoke(app, ["project", "archive", "Hidden"])
        result = runner.invoke(app, ["project", "list"])
        assert result.exit_code == 0
        assert "Hidden" not in result.output

    @pytest.mark.usefixtures("_mock_settings")
    def test_list_all_includes_archived(self, tmp_path: Path) -> None:
        ws = str(tmp_path / "workspace")
        runner.invoke(
            app, ["project", "create", "--name", "Visible", "--workspace", ws]
        )
        runner.invoke(app, ["project", "archive", "Visible"])
        result = runner.invoke(app, ["project", "list", "--all"])
        assert result.exit_code == 0
        assert "Visible" in result.output
        assert "archived" in result.output

    @pytest.mark.usefixtures("_mock_settings")
    def test_list_empty_prints_message(self) -> None:
        result = runner.invoke(app, ["project", "list"])
        assert result.exit_code == 0
        assert "No projects" in result.output


# ---------------------------------------------------------------------------
# switch
# ---------------------------------------------------------------------------


class TestProjectSwitch:
    """bearclaw project switch NAME — writes active_project file."""

    @pytest.mark.usefixtures("_mock_settings")
    def test_switch_writes_active_project_file(self, tmp_path: Path) -> None:
        ws = str(tmp_path / "workspace")
        runner.invoke(
            app, ["project", "create", "--name", "Switchable", "--workspace", ws]
        )
        result = runner.invoke(app, ["project", "switch", "Switchable"])
        assert result.exit_code == 0

        active_path = tmp_path / "active_project"
        assert active_path.exists()
        assert active_path.read_text(encoding="utf-8").strip() == "switchable"

    @pytest.mark.usefixtures("_mock_settings")
    def test_switch_nonexistent_project_errors(self) -> None:
        result = runner.invoke(app, ["project", "switch", "Ghost"])
        assert result.exit_code == 1
        assert "No project" in result.output

    @pytest.mark.usefixtures("_mock_settings")
    def test_switch_prints_confirmation(self, tmp_path: Path) -> None:
        ws = str(tmp_path / "workspace")
        runner.invoke(
            app, ["project", "create", "--name", "Confirmed", "--workspace", ws]
        )
        result = runner.invoke(app, ["project", "switch", "Confirmed"])
        assert result.exit_code == 0
        assert "Confirmed" in result.output


# ---------------------------------------------------------------------------
# archive
# ---------------------------------------------------------------------------


class TestProjectArchive:
    """bearclaw project archive NAME — sets status to archived."""

    @pytest.mark.usefixtures("_mock_settings")
    def test_archive_success(self, tmp_path: Path) -> None:
        ws = str(tmp_path / "workspace")
        runner.invoke(
            app, ["project", "create", "--name", "Archivable", "--workspace", ws]
        )
        result = runner.invoke(app, ["project", "archive", "Archivable"])
        assert result.exit_code == 0
        assert "Archivable" in result.output

    @pytest.mark.usefixtures("_mock_settings")
    def test_archive_nonexistent_project_errors(self) -> None:
        result = runner.invoke(app, ["project", "archive", "Ghost"])
        assert result.exit_code == 1
        assert "No project" in result.output

    @pytest.mark.usefixtures("_mock_settings")
    def test_archive_makes_project_inactive(self, tmp_path: Path) -> None:
        ws = str(tmp_path / "workspace")
        runner.invoke(
            app, ["project", "create", "--name", "GoingAway", "--workspace", ws]
        )
        runner.invoke(app, ["project", "archive", "GoingAway"])
        # Verify it's archived in list --all
        result = runner.invoke(app, ["project", "list", "--all"])
        assert "archived" in result.output


# ---------------------------------------------------------------------------
# new (workspace scaffolding)
# ---------------------------------------------------------------------------


class TestProjectNew:
    """bearclaw project new NAME --template TEMPLATE — scaffold project."""

    def test_new_in_help(self) -> None:
        result = runner.invoke(app, ["project", "--help"])
        assert "new" in result.output

    @pytest.mark.usefixtures("_mock_settings")
    def test_new_default_bare_template(self, tmp_path: Path) -> None:
        """Default template is 'bare' when --template is omitted."""
        expected = tmp_path / "project-root" / "my-app"
        with patch(
            "owlbear.projects.workspace.ProjectWorkspace"
        ) as mock_ws_cls:
            mock_ws_cls.return_value.create_project.return_value = expected
            result = runner.invoke(app, ["project", "new", "My App"])
        assert result.exit_code == 0
        mock_ws_cls.return_value.create_project.assert_called_once_with(
            "My App", "bare"
        )

    @pytest.mark.usefixtures("_mock_settings")
    def test_new_with_template_option(self, tmp_path: Path) -> None:
        expected = tmp_path / "project-root" / "my-app"
        with patch(
            "owlbear.projects.workspace.ProjectWorkspace"
        ) as mock_ws_cls:
            mock_ws_cls.return_value.create_project.return_value = expected
            result = runner.invoke(
                app, ["project", "new", "My App", "--template", "python-uv"]
            )
        assert result.exit_code == 0
        mock_ws_cls.return_value.create_project.assert_called_once_with(
            "My App", "python-uv"
        )

    @pytest.mark.usefixtures("_mock_settings")
    def test_new_prints_path(self, tmp_path: Path) -> None:
        expected = tmp_path / "project-root" / "my-app"
        with patch(
            "owlbear.projects.workspace.ProjectWorkspace"
        ) as mock_ws_cls:
            mock_ws_cls.return_value.create_project.return_value = expected
            result = runner.invoke(app, ["project", "new", "My App"])
        assert str(expected) in result.output

    @pytest.mark.usefixtures("_mock_settings")
    def test_new_invalid_template_errors(self) -> None:
        with patch(
            "owlbear.projects.workspace.ProjectWorkspace"
        ) as mock_ws_cls:
            mock_ws_cls.return_value.create_project.side_effect = ValueError(
                "Unknown template 'bad'. Valid: ['bare', 'node', 'python-pip', 'python-uv']"
            )
            result = runner.invoke(
                app, ["project", "new", "My App", "--template", "bad"]
            )
        assert result.exit_code == 1
        assert "Error" in result.output

    @pytest.mark.usefixtures("_mock_settings")
    def test_new_duplicate_name_errors(self) -> None:
        with patch(
            "owlbear.projects.workspace.ProjectWorkspace"
        ) as mock_ws_cls:
            mock_ws_cls.return_value.create_project.side_effect = ValueError(
                "Project 'My App' already exists"
            )
            result = runner.invoke(app, ["project", "new", "My App"])
        assert result.exit_code == 1
        assert "already exists" in result.output

    @pytest.mark.usefixtures("_mock_settings")
    def test_new_dir_exists_errors(self) -> None:
        with patch(
            "owlbear.projects.workspace.ProjectWorkspace"
        ) as mock_ws_cls:
            mock_ws_cls.return_value.create_project.side_effect = FileExistsError(
                "Directory already exists: /some/path"
            )
            result = runner.invoke(app, ["project", "new", "My App"])
        assert result.exit_code == 1
        assert "Error" in result.output
