"""Failing tests for task #92: setup script core functions.

Covers:
  - VS Code settings.json: all three location types, both paths per type,
    forward slashes, idempotent merge
  - VS Code mcp.json: three server entries, correct module names, relative
    owlbear path, idempotent skip-if-exists
  - kanban/ setup: config.yml, tasks/, setup.ps1 copy, clean next_id,
    idempotent skip-if-exists
  - data/knowledge/ directory creation
  - .github/copilot-instructions.md: project name inclusion, idempotent skip
  - Path auto-detection from script __file__ location
  - Success message output (capsys)

All tests fail on current HEAD because scripts/setup.py is a 3-line stub
with no callable functions.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import target — will raise ImportError until functions exist (RED phase)
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from setup import (  # noqa: E402  # type: ignore[import]
    compute_owlbear_relpath,
    create_copilot_instructions,
    create_kanban_dir,
    create_knowledge_dir,
    create_mcp_config,
    create_vscode_settings,
    setup,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_owlbear_dir(tmp_path: Path) -> Path:
    """Create a minimal mock owlbear directory with required source files."""
    owlbear_dir = tmp_path / "owlbear"
    kanban = owlbear_dir / "kanban"
    kanban.mkdir(parents=True)
    # next_id: 42 — must be reset to clean value when copying to project
    (kanban / "config.yml").write_text(
        "next_id: 42\nstatuses:\n  - todo\n  - done\n", encoding="utf-8"
    )
    (kanban / "setup.ps1").write_text("# kanban-md download script\n", encoding="utf-8")
    return owlbear_dir


def _project_dir(tmp_path: Path) -> Path:
    """Create and return an empty project directory."""
    d = tmp_path / "proj"
    d.mkdir()
    return d


# ---------------------------------------------------------------------------
# AC: VS Code settings.json generation
# ---------------------------------------------------------------------------


class TestFromAC_VscodeSettings:
    """AC: settings.json has all three location types, both paths each, forward slashes, merge."""

    def test_settings_json_file_created(self, tmp_path: Path) -> None:
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_vscode_settings(project_dir, owlbear_dir)
        assert (project_dir / ".vscode" / "settings.json").exists()

    def test_settings_json_has_agent_files_locations(self, tmp_path: Path) -> None:
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_vscode_settings(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "settings.json").read_text())
        assert "chat.agentFilesLocations" in data

    def test_settings_json_has_agent_skills_locations(self, tmp_path: Path) -> None:
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_vscode_settings(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "settings.json").read_text())
        assert "chat.agentSkillsLocations" in data

    def test_settings_json_has_instructions_files_locations(self, tmp_path: Path) -> None:
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_vscode_settings(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "settings.json").read_text())
        assert "chat.instructionsFilesLocations" in data

    def test_agent_files_locations_has_root_and_github_paths(self, tmp_path: Path) -> None:
        """agentFilesLocations must map both {rel}/agents and {rel}/.github/agents."""
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_vscode_settings(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "settings.json").read_text())
        paths = list(data["chat.agentFilesLocations"].keys())
        has_root = any(p.endswith("/agents") and "/.github/" not in p for p in paths)
        has_github = any("/.github/agents" in p for p in paths)
        assert has_root, f"agentFilesLocations missing {{rel}}/agents — got: {paths}"
        assert has_github, f"agentFilesLocations missing {{rel}}/.github/agents — got: {paths}"

    def test_agent_skills_locations_has_root_and_github_paths(self, tmp_path: Path) -> None:
        """agentSkillsLocations must map both {rel}/skills and {rel}/.github/skills."""
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_vscode_settings(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "settings.json").read_text())
        paths = list(data["chat.agentSkillsLocations"].keys())
        has_root = any(p.endswith("/skills") and "/.github/" not in p for p in paths)
        has_github = any("/.github/skills" in p for p in paths)
        assert has_root, f"agentSkillsLocations missing {{rel}}/skills — got: {paths}"
        assert has_github, f"agentSkillsLocations missing {{rel}}/.github/skills — got: {paths}"

    def test_instructions_locations_has_root_and_github_paths(self, tmp_path: Path) -> None:
        """instructionsFilesLocations must map both {rel}/instructions and {rel}/.github/instructions."""
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_vscode_settings(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "settings.json").read_text())
        paths = list(data["chat.instructionsFilesLocations"].keys())
        has_root = any(p.endswith("/instructions") and "/.github/" not in p for p in paths)
        has_github = any("/.github/instructions" in p for p in paths)
        assert has_root, f"instructionsFilesLocations missing {{rel}}/instructions — got: {paths}"
        assert has_github, (
            f"instructionsFilesLocations missing {{rel}}/.github/instructions — got: {paths}"
        )

    def test_location_paths_use_forward_slashes(self, tmp_path: Path) -> None:
        """All VS Code location paths must use forward slashes (no backslashes)."""
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_vscode_settings(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "settings.json").read_text())
        for key in (
            "chat.agentFilesLocations",
            "chat.agentSkillsLocations",
            "chat.instructionsFilesLocations",
        ):
            for path_key in data[key]:
                assert "\\" not in path_key, f"Backslash in {key} path: {path_key!r}"

    def test_idempotent_merge_preserves_existing_user_keys(self, tmp_path: Path) -> None:
        """Calling with existing settings.json must preserve pre-existing user keys."""
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        vscode_dir = project_dir / ".vscode"
        vscode_dir.mkdir(parents=True)
        existing = {"editor.fontSize": 14, "editor.wordWrap": "on"}
        (vscode_dir / "settings.json").write_text(json.dumps(existing), encoding="utf-8")
        create_vscode_settings(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "settings.json").read_text())
        assert data.get("editor.fontSize") == 14, "editor.fontSize was overwritten"
        assert data.get("editor.wordWrap") == "on", "editor.wordWrap was overwritten"

    def test_idempotent_merge_adds_owlbear_keys_to_existing_file(self, tmp_path: Path) -> None:
        """Calling with existing settings.json must add owlbear keys alongside existing keys."""
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        vscode_dir = project_dir / ".vscode"
        vscode_dir.mkdir(parents=True)
        (vscode_dir / "settings.json").write_text('{"editor.fontSize": 14}', encoding="utf-8")
        create_vscode_settings(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "settings.json").read_text())
        assert "chat.agentFilesLocations" in data
        assert "chat.agentSkillsLocations" in data
        assert "chat.instructionsFilesLocations" in data


# ---------------------------------------------------------------------------
# AC: MCP config (.vscode/mcp.json)
# ---------------------------------------------------------------------------


class TestFromAC_McpConfig:
    """AC: mcp.json with three servers, correct module names, relative path, idempotent skip."""

    def test_mcp_json_file_created(self, tmp_path: Path) -> None:
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_mcp_config(project_dir, owlbear_dir)
        assert (project_dir / ".vscode" / "mcp.json").exists()

    def test_mcp_json_has_exactly_three_server_entries(self, tmp_path: Path) -> None:
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_mcp_config(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "mcp.json").read_text())
        assert len(data["servers"]) == 3, f"Expected 3 MCP servers, got {len(data['servers'])}"

    def test_mcp_args_contain_mcp_kanban_module(self, tmp_path: Path) -> None:
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_mcp_config(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "mcp.json").read_text())
        all_args = [str(a) for s in data["servers"].values() for a in s.get("args", [])]
        assert "mcp_kanban" in all_args, f"mcp_kanban not in MCP args: {all_args}"

    def test_mcp_args_contain_mcp_knowledge_module(self, tmp_path: Path) -> None:
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_mcp_config(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "mcp.json").read_text())
        all_args = [str(a) for s in data["servers"].values() for a in s.get("args", [])]
        assert "mcp_knowledge" in all_args, f"mcp_knowledge not in MCP args: {all_args}"

    def test_mcp_args_contain_mcp_project_module(self, tmp_path: Path) -> None:
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_mcp_config(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "mcp.json").read_text())
        all_args = [str(a) for s in data["servers"].values() for a in s.get("args", [])]
        assert "mcp_project" in all_args, f"mcp_project not in MCP args: {all_args}"

    def test_mcp_server_args_reference_relative_path_to_owlbear(self, tmp_path: Path) -> None:
        """At least one server arg must be a relative path pointing toward owlbear."""
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_mcp_config(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "mcp.json").read_text())
        all_args = [str(a) for s in data["servers"].values() for a in s.get("args", [])]
        has_relative = any(
            not Path(a).is_absolute() and (".." in a or a.startswith("..")) for a in all_args
        )
        assert has_relative, f"No relative owlbear path found in MCP server args: {all_args}"

    def test_mcp_json_idempotent_skips_if_file_exists(self, tmp_path: Path) -> None:
        """mcp.json must not be overwritten if it already exists."""
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        vscode_dir = project_dir / ".vscode"
        vscode_dir.mkdir(parents=True)
        sentinel = '{"servers": {"SENTINEL_SERVER": {}}}'
        (vscode_dir / "mcp.json").write_text(sentinel, encoding="utf-8")
        create_mcp_config(project_dir, owlbear_dir)
        content = (project_dir / ".vscode" / "mcp.json").read_text()
        assert "SENTINEL_SERVER" in content, "mcp.json was overwritten despite already existing"


# ---------------------------------------------------------------------------
# AC: kanban/ directory setup
# ---------------------------------------------------------------------------


class TestFromAC_KanbanSetup:
    """AC: kanban/ with config.yml, tasks/, setup.ps1, clean next_id, idempotent skip."""

    def test_kanban_directory_created(self, tmp_path: Path) -> None:
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_kanban_dir(project_dir, owlbear_dir)
        assert (project_dir / "kanban").is_dir()

    def test_kanban_config_yml_exists(self, tmp_path: Path) -> None:
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_kanban_dir(project_dir, owlbear_dir)
        assert (project_dir / "kanban" / "config.yml").exists()

    def test_kanban_tasks_subdirectory_created(self, tmp_path: Path) -> None:
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_kanban_dir(project_dir, owlbear_dir)
        assert (project_dir / "kanban" / "tasks").is_dir()

    def test_copied_config_yml_has_clean_next_id(self, tmp_path: Path) -> None:
        """Copied config.yml must NOT carry over the owlbear source next_id (42)."""
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        # _make_owlbear_dir sets next_id: 42; the copy must reset it
        create_kanban_dir(project_dir, owlbear_dir)
        content = (project_dir / "kanban" / "config.yml").read_text()
        assert "42" not in content, (
            "next_id was not reset — copied config still contains owlbear source value 42"
        )

    def test_kanban_setup_ps1_copied(self, tmp_path: Path) -> None:
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_kanban_dir(project_dir, owlbear_dir)
        assert (project_dir / "kanban" / "setup.ps1").exists()

    def test_kanban_config_yml_idempotent_skips_if_exists(self, tmp_path: Path) -> None:
        """config.yml must not be overwritten when it already exists."""
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        kanban_dir = project_dir / "kanban"
        kanban_dir.mkdir(parents=True)
        (kanban_dir / "config.yml").write_text("# SENTINEL_CONFIG\n", encoding="utf-8")
        create_kanban_dir(project_dir, owlbear_dir)
        content = (project_dir / "kanban" / "config.yml").read_text()
        assert "SENTINEL_CONFIG" in content, "kanban/config.yml was overwritten despite existing"


# ---------------------------------------------------------------------------
# AC: data/knowledge/ directory and .github/copilot-instructions.md
# ---------------------------------------------------------------------------


class TestFromAC_DataAndInstructions:
    """AC: data/knowledge/ dir, copilot-instructions.md with project name, idempotent skip."""

    def test_data_knowledge_directory_created(self, tmp_path: Path) -> None:
        project_dir = _project_dir(tmp_path)
        create_knowledge_dir(project_dir)
        assert (project_dir / "data" / "knowledge").is_dir()

    def test_copilot_instructions_file_created(self, tmp_path: Path) -> None:
        project_dir = _project_dir(tmp_path)
        create_copilot_instructions(project_dir, name="TestProject")
        assert (project_dir / ".github" / "copilot-instructions.md").exists()

    def test_copilot_instructions_contains_project_name(self, tmp_path: Path) -> None:
        project_dir = _project_dir(tmp_path)
        create_copilot_instructions(project_dir, name="MyOwlBearProject")
        content = (project_dir / ".github" / "copilot-instructions.md").read_text()
        assert "MyOwlBearProject" in content, "Project name not found in copilot-instructions.md"

    def test_copilot_instructions_idempotent_skips_if_exists(self, tmp_path: Path) -> None:
        """.github/copilot-instructions.md must not be overwritten if it already exists."""
        project_dir = _project_dir(tmp_path)
        github_dir = project_dir / ".github"
        github_dir.mkdir(parents=True)
        (github_dir / "copilot-instructions.md").write_text(
            "# SENTINEL_INSTRUCTIONS\n", encoding="utf-8"
        )
        create_copilot_instructions(project_dir, name="NewProject")
        content = (project_dir / ".github" / "copilot-instructions.md").read_text()
        assert "SENTINEL_INSTRUCTIONS" in content, (
            ".github/copilot-instructions.md was overwritten despite already existing"
        )


# ---------------------------------------------------------------------------
# AC: Path auto-detection and success message output
# ---------------------------------------------------------------------------


class TestFromAC_PathDetectionAndOutput:
    """AC: forward-slash relative paths, owlbear dir auto-detection, success message."""

    def test_compute_owlbear_relpath_uses_forward_slashes(self, tmp_path: Path) -> None:
        """compute_owlbear_relpath must return a POSIX path with no backslashes."""
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        rel = compute_owlbear_relpath(owlbear_dir, project_dir)
        assert "\\" not in rel, f"Backslash in computed relative path: {rel!r}"

    def test_setup_auto_detects_owlbear_dir_from_script_location(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """setup() without explicit owlbear_dir must resolve it from the script's __file__."""
        project_dir = _project_dir(tmp_path)
        monkeypatch.chdir(project_dir)
        # No owlbear_dir passed — auto-detect from Path(__file__).resolve().parent.parent
        setup(project_dir=project_dir)
        assert (project_dir / ".vscode" / "settings.json").exists(), (
            "setup() auto-detection failed — .vscode/settings.json not created"
        )

    def test_setup_prints_success_message(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """setup() must print a non-empty success message with next steps."""
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        setup(project_dir=project_dir, owlbear_dir=owlbear_dir)
        captured = capsys.readouterr()
        assert captured.out.strip(), "No success message printed — expected next-steps output"
