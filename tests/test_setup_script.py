"""Failing tests for task #92 (core functions), task #12 (AC gaps), and task #69 (project JSON) for setup script.

Covers:
  - VS Code settings.json: all three location types, both paths per type,
    forward slashes, idempotent merge
  - VS Code mcp.json: three server entries, correct module names, relative
    owlbear path, idempotent skip-if-exists
  - MCP server key names must be camelCase: owlbearKanban, owlbearKnowledge, owlbearProject
  - kanban/ setup: config.yml, tasks/, setup.ps1 copy, clean next_id,
    idempotent skip-if-exists
  - data/knowledge/ directory creation
  - .github/copilot-instructions.md: project name inclusion, idempotent skip
  - Path auto-detection from script __file__ location
  - Success message output (capsys)
  - setup() orchestrates ALL create_* functions (all artifacts created in one call)
  - create_project_json(): writes owlbear-project.json, 5 fields, POSIX path,
    UTC aware created_at, name/type defaults, idempotent skip, called from setup()
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest
from owlbear_mcp_project.models import OwlbearProjectFile

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

    def test_agent_files_locations_has_root_path_only(self, tmp_path: Path) -> None:
        """agentFilesLocations must map {rel}/agents only — .github/agents must be absent."""
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_vscode_settings(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "settings.json").read_text())
        paths = list(data["chat.agentFilesLocations"].keys())
        has_root = any(p.endswith("/agents") and "/.github/" not in p for p in paths)
        has_github = any("/.github/agents" in p for p in paths)
        assert has_root, f"agentFilesLocations missing {{rel}}/agents — got: {paths}"
        assert not has_github, f"agentFilesLocations must NOT contain {{rel}}/.github/agents — got: {paths}"

    def test_agent_skills_locations_has_root_path(self, tmp_path: Path) -> None:
        """agentSkillsLocations must map {rel}/skills."""
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_vscode_settings(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "settings.json").read_text())
        paths = list(data["chat.agentSkillsLocations"].keys())
        has_root = any(p.endswith("/skills") and "/.github/" not in p for p in paths)
        assert has_root, f"agentSkillsLocations missing {{rel}}/skills — got: {paths}"

    def test_instructions_locations_has_root_path_only(self, tmp_path: Path) -> None:
        """instructionsFilesLocations must map {rel}/instructions only — .github/instructions must be absent."""
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_vscode_settings(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "settings.json").read_text())
        paths = list(data["chat.instructionsFilesLocations"].keys())
        has_root = any(p.endswith("/instructions") and "/.github/" not in p for p in paths)
        has_github = any("/.github/instructions" in p for p in paths)
        assert has_root, f"instructionsFilesLocations missing {{rel}}/instructions — got: {paths}"
        assert not has_github, (
            f"instructionsFilesLocations must NOT contain {{rel}}/.github/instructions — got: {paths}"
        )

    def test_location_values_are_booleans(self, tmp_path: Path) -> None:
        """VS Code expects boolean values for chat location settings, not strings."""
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_vscode_settings(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "settings.json").read_text())
        for key in ("chat.agentFilesLocations", "chat.agentSkillsLocations", "chat.instructionsFilesLocations"):
            for path, value in data[key].items():
                assert value is True, f"{key}[{path!r}] must be True (bool), got {value!r}"

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
        assert len(data["servers"]) == 5, f"Expected 5 MCP servers, got {len(data['servers'])}"

    def test_mcp_args_contain_mcp_kanban_module(self, tmp_path: Path) -> None:
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_mcp_config(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "mcp.json").read_text())
        all_args = [str(a) for s in data["servers"].values() for a in s.get("args", [])]
        assert "owlbear_mcp_kanban" in all_args, f"owlbear_mcp_kanban not in MCP args: {all_args}"

    def test_mcp_args_contain_mcp_knowledge_module(self, tmp_path: Path) -> None:
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_mcp_config(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "mcp.json").read_text())
        all_args = [str(a) for s in data["servers"].values() for a in s.get("args", [])]
        assert "owlbear_mcp_knowledge" in all_args, f"owlbear_mcp_knowledge not in MCP args: {all_args}"

    def test_mcp_args_contain_mcp_project_module(self, tmp_path: Path) -> None:
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_mcp_config(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "mcp.json").read_text())
        all_args = [str(a) for s in data["servers"].values() for a in s.get("args", [])]
        assert "owlbear_mcp_project" in all_args, f"owlbear_mcp_project not in MCP args: {all_args}"

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
        """Copied config.yml must reset next_id to exactly 1 (not just strip source value)."""
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        # _make_owlbear_dir sets next_id: 42; the copy must reset it to exactly 1
        create_kanban_dir(project_dir, owlbear_dir)
        content = (project_dir / "kanban" / "config.yml").read_text()
        assert "42" not in content, (
            "next_id was not reset — copied config still contains owlbear source value 42"
        )
        assert "next_id: 1" in content, (
            "next_id was not reset to 1 — AC requires clean next_id reset to 1"
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
        assert "mcp.json" in captured.out, "Expected mcp.json customization hint in next-steps output"
        assert "README" in captured.out, "Expected README reference in next-steps output"

    def test_setup_creates_all_expected_artifacts(self, tmp_path: Path) -> None:
        """setup() must call ALL create_* functions — every artifact must exist after one call."""
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        setup(project_dir=project_dir, owlbear_dir=owlbear_dir)
        assert (project_dir / ".vscode" / "settings.json").exists(), "settings.json not created"
        assert (project_dir / ".vscode" / "mcp.json").exists(), "mcp.json not created"
        assert (project_dir / "kanban" / "config.yml").exists(), "kanban/config.yml not created"
        assert (project_dir / "kanban" / "tasks").is_dir(), "kanban/tasks/ not created"
        assert (project_dir / "data" / "knowledge").is_dir(), "data/knowledge/ not created"
        assert (project_dir / ".github" / "copilot-instructions.md").exists(), (
            ".github/copilot-instructions.md not created"
        )


# ---------------------------------------------------------------------------
# AC: MCP server names must be kebab-case (task #570 — fixes camelCase bug)
# ---------------------------------------------------------------------------


class TestFromAC_McpServerNames:
    """AC: server keys must be owlbear-kanban, owlbear-knowledge, owlbear-memory, owlbear-project (kebab-case)."""

    def test_mcp_server_names_are_kebab_case(self, tmp_path: Path) -> None:
        """Server entry keys must be kebab-case — camelCase breaks owlbear-kanban/* tool routing."""
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_mcp_config(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "mcp.json").read_text())
        server_names = set(data["servers"].keys())
        expected = {"github", "owlbear-kanban", "owlbear-knowledge", "owlbear-memory", "owlbear-project"}
        assert server_names == expected, (
            f"MCP server names must be kebab-case for tool routing. Expected {expected}, got {server_names}"
        )

    def test_mcp_server_name_owlbear_kanban_exists(self, tmp_path: Path) -> None:
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_mcp_config(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "mcp.json").read_text())
        assert "owlbear-kanban" in data["servers"], (
            f"owlbear-kanban not in server keys: {list(data['servers'].keys())}"
        )

    def test_mcp_server_name_owlbear_knowledge_exists(self, tmp_path: Path) -> None:
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_mcp_config(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "mcp.json").read_text())
        assert "owlbear-knowledge" in data["servers"], (
            f"owlbear-knowledge not in server keys: {list(data['servers'].keys())}"
        )

    def test_mcp_server_name_owlbear_project_exists(self, tmp_path: Path) -> None:
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_mcp_config(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "mcp.json").read_text())
        assert "owlbear-project" in data["servers"], (
            f"owlbear-project not in server keys: {list(data['servers'].keys())}"
        )

    def test_mcp_server_name_owlbear_memory_exists(self, tmp_path: Path) -> None:
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_mcp_config(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "mcp.json").read_text())
        assert "owlbear-memory" in data["servers"], (
            f"owlbear-memory not in server keys: {list(data['servers'].keys())}"
        )

    def test_mcp_server_args_have_no_project_flag(self, tmp_path: Path) -> None:
        """No owlbear server entry may use --project flag — matching workspace convention."""
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_mcp_config(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "mcp.json").read_text())
        for name, entry in data["servers"].items():
            args = entry.get("args", [])
            assert "--project" not in args, (
                f"Server '{name}' must not use --project flag in args, got: {args}"
            )


# ---------------------------------------------------------------------------
# AC: Script runnable as standalone script (task #12 retry — __main__ gap)
# ---------------------------------------------------------------------------


class TestFromAC_StandaloneInvocation:
    """AC: Can be run as: python ../owlbear/scripts/setup.py"""

    def test_script_has_main_guard(self) -> None:
        """scripts/setup.py must have if __name__ == '__main__' guard to be runnable directly."""
        script = Path(__file__).parent.parent / "scripts" / "setup.py"
        content = script.read_text(encoding="utf-8")
        assert '__name__ == "__main__"' in content, (
            "scripts/setup.py has no if __name__ == '__main__' guard — "
            "running `python scripts/setup.py` is a no-op (defines functions only)"
        )

    def test_direct_invocation_creates_vscode_settings(self, tmp_path: Path) -> None:
        """Running the script directly must create .vscode/settings.json."""
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        script = Path(__file__).parent.parent / "scripts" / "setup.py"
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, (
            f"Script exited non-zero: {result.returncode}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert (project_dir / ".vscode" / "settings.json").exists(), (
            f"Direct invocation did not create .vscode/settings.json\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_direct_invocation_creates_mcp_config(self, tmp_path: Path) -> None:
        """Running the script directly must create .vscode/mcp.json."""
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        script = Path(__file__).parent.parent / "scripts" / "setup.py"
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, (
            f"Script exited non-zero: {result.returncode}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert (project_dir / ".vscode" / "mcp.json").exists(), (
            f"Direct invocation did not create .vscode/mcp.json\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_direct_invocation_prints_success_message(self, tmp_path: Path) -> None:
        """Running the script directly must print a success message to stdout."""
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        script = Path(__file__).parent.parent / "scripts" / "setup.py"
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, (
            f"Script exited non-zero: {result.returncode}\nstderr: {result.stderr}"
        )
        assert result.stdout.strip(), (
            "Direct invocation produced no stdout — expected a success message with next steps"
        )


# ---------------------------------------------------------------------------
# AC: GitHub remote MCP server entry (task #121)
# ---------------------------------------------------------------------------


class TestFromAC_GitHubMcpServer:
    """AC: create_mcp_config() includes github http server; first entry; 4 servers total; idempotent preserved."""

    def test_github_server_entry_exists(self, tmp_path: Path) -> None:
        """AC: create_mcp_config() must include a 'github' key in the servers dict."""
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_mcp_config(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "mcp.json").read_text())
        assert "github" in data["servers"], (
            f"'github' server entry missing. Found servers: {list(data['servers'].keys())}"
        )

    def test_github_server_has_type_http(self, tmp_path: Path) -> None:
        """AC: github server entry must have type: http."""
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_mcp_config(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "mcp.json").read_text())
        github = data["servers"].get("github", {})
        assert github.get("type") == "http", (
            f"github server type must be 'http', got: {github.get('type')!r}"
        )

    def test_github_server_has_correct_url(self, tmp_path: Path) -> None:
        """AC: github server must have url: https://api.githubcopilot.com/mcp/"""
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_mcp_config(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "mcp.json").read_text())
        github = data["servers"].get("github", {})
        assert github.get("url") == "https://api.githubcopilot.com/mcp/", (
            f"github server url must be 'https://api.githubcopilot.com/mcp/', got: {github.get('url')!r}"
        )

    def test_github_server_is_first_in_servers_dict(self, tmp_path: Path) -> None:
        """AC: github entry must appear first in the servers dict (zero-dep, immediately useful)."""
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_mcp_config(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "mcp.json").read_text())
        server_keys = list(data["servers"].keys())
        assert server_keys[0] == "github", (
            f"github must be the first server entry, but found first={server_keys[0]!r}. "
            f"Full order: {server_keys}"
        )

    def test_mcp_json_has_exactly_four_server_entries(self, tmp_path: Path) -> None:
        """AC: mcp.json must contain exactly 5 servers (github + 4 owlbear stdio servers)."""
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_mcp_config(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "mcp.json").read_text())
        assert len(data["servers"]) == 5, (
            f"Expected exactly 5 MCP server entries (github + 4 owlbear), "
            f"got {len(data['servers'])}: {list(data['servers'].keys())}"
        )

    def test_three_owlbear_servers_still_present_alongside_github(self, tmp_path: Path) -> None:
        """AC: adding github must not remove the 3 owlbear stdio servers."""
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_mcp_config(project_dir, owlbear_dir)
        data = json.loads((project_dir / ".vscode" / "mcp.json").read_text())
        servers = data["servers"]
        # Verify github is co-present (this test validates the "alongside" contract)
        assert "github" in servers, (
            f"github entry absent — cannot verify co-existence. Found: {list(servers.keys())}"
        )
        for key in ("owlbear-kanban", "owlbear-knowledge", "owlbear-project"):
            assert key in servers, (
                f"Expected owlbear server '{key}' to remain present alongside github entry. "
                f"Found: {list(servers.keys())}"
            )


# ---------------------------------------------------------------------------
# AC: create_project_json() — owlbear-project.json generation (task #69)
# ---------------------------------------------------------------------------


class TestFromAC_ProjectJsonGeneration:
    """AC-driven tests for create_project_json() in scripts/setup.py (task #69).

    Function signature (AC): create_project_json(project_dir, owlbear_dir, *, name=None, project_type='bare') -> None

    All tests use a deferred import so ImportError is contained to this class
    only, preserving the existing test suite while the builder implements the
    function.

    Covered AC lines:
      AC1  — Writes owlbear-project.json with all 5 fields
      AC2  — schema_version is 1
      AC3  — owlbear_path uses compute_owlbear_relpath() (POSIX forward slashes)
      AC4  — name defaults to project_dir.name; project_type defaults to 'bare'
      AC5  — created_at is timezone-aware UTC (datetime.now(tz=UTC))
      AC6  — Constructs OwlbearProjectFile for validation; round-trip validates
      AC7  — Idempotent: skips if file already exists (print message, no overwrite)
      AC8  — Called from setup() function
    """

    # ------------------------------------------------------------------
    # AC1: Writes owlbear-project.json with all 5 required fields
    # ------------------------------------------------------------------

    def test_creates_owlbear_project_json_file(self, tmp_path: Path) -> None:
        from setup import create_project_json  # type: ignore[import]  # ImportError until builder adds it

        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_project_json(project_dir, owlbear_dir)
        assert (project_dir / "owlbear-project.json").exists(), "owlbear-project.json was not created"

    def test_written_json_has_all_five_required_fields(self, tmp_path: Path) -> None:
        from setup import create_project_json  # type: ignore[import]

        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_project_json(project_dir, owlbear_dir)
        data = json.loads((project_dir / "owlbear-project.json").read_text(encoding="utf-8"))
        for field in ("schema_version", "name", "type", "owlbear_path", "created_at"):
            assert field in data, f"Missing required field: {field!r}"

    # ------------------------------------------------------------------
    # AC2: schema_version is 1
    # ------------------------------------------------------------------

    def test_schema_version_is_one(self, tmp_path: Path) -> None:
        from setup import create_project_json  # type: ignore[import]

        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_project_json(project_dir, owlbear_dir)
        data = json.loads((project_dir / "owlbear-project.json").read_text(encoding="utf-8"))
        assert data["schema_version"] == 1, (
            f"Expected schema_version=1, got {data['schema_version']!r}"
        )

    # ------------------------------------------------------------------
    # AC3: owlbear_path uses compute_owlbear_relpath() -- POSIX forward slashes
    # ------------------------------------------------------------------

    def test_owlbear_path_uses_forward_slashes(self, tmp_path: Path) -> None:
        from setup import create_project_json  # type: ignore[import]

        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_project_json(project_dir, owlbear_dir)
        data = json.loads((project_dir / "owlbear-project.json").read_text(encoding="utf-8"))
        owlbear_path = data["owlbear_path"]
        assert "\\" not in owlbear_path, (
            f"owlbear_path must use forward slashes only (POSIX), got: {owlbear_path!r}"
        )

    def test_owlbear_path_is_relative_not_absolute(self, tmp_path: Path) -> None:
        from setup import create_project_json  # type: ignore[import]

        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_project_json(project_dir, owlbear_dir)
        data = json.loads((project_dir / "owlbear-project.json").read_text(encoding="utf-8"))
        owlbear_path = data["owlbear_path"]
        assert not Path(owlbear_path).is_absolute(), (
            f"owlbear_path must be relative (via compute_owlbear_relpath), got absolute: {owlbear_path!r}"
        )

    # ------------------------------------------------------------------
    # AC4: name defaults to project_dir.name; project_type defaults to 'bare'
    # ------------------------------------------------------------------

    def test_name_defaults_to_project_dir_name(self, tmp_path: Path) -> None:
        from setup import create_project_json  # type: ignore[import]

        project_dir = tmp_path / "my-owlbear-project"
        project_dir.mkdir()
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_project_json(project_dir, owlbear_dir)
        data = json.loads((project_dir / "owlbear-project.json").read_text(encoding="utf-8"))
        assert data["name"] == "my-owlbear-project", (
            f"Expected name to default to directory name 'my-owlbear-project', got {data['name']!r}"
        )

    def test_project_type_defaults_to_bare(self, tmp_path: Path) -> None:
        from setup import create_project_json  # type: ignore[import]

        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_project_json(project_dir, owlbear_dir)
        data = json.loads((project_dir / "owlbear-project.json").read_text(encoding="utf-8"))
        assert data["type"] == "bare", (
            f"Expected type to default to 'bare', got {data['type']!r}"
        )

    def test_explicit_name_overrides_default(self, tmp_path: Path) -> None:
        from setup import create_project_json  # type: ignore[import]

        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_project_json(project_dir, owlbear_dir, name="my-custom-name")
        data = json.loads((project_dir / "owlbear-project.json").read_text(encoding="utf-8"))
        assert data["name"] == "my-custom-name", (
            f"Expected explicit name 'my-custom-name', got {data['name']!r}"
        )

    def test_explicit_project_type_overrides_default(self, tmp_path: Path) -> None:
        from setup import create_project_json  # type: ignore[import]

        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_project_json(project_dir, owlbear_dir, project_type="python-uv")
        data = json.loads((project_dir / "owlbear-project.json").read_text(encoding="utf-8"))
        assert data["type"] == "python-uv", (
            f"Expected explicit type 'python-uv', got {data['type']!r}"
        )

    # ------------------------------------------------------------------
    # AC5: created_at is timezone-aware UTC (datetime.now(tz=UTC))
    # ------------------------------------------------------------------

    def test_created_at_is_timezone_aware(self, tmp_path: Path) -> None:
        from setup import create_project_json  # type: ignore[import]

        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_project_json(project_dir, owlbear_dir)
        data = json.loads((project_dir / "owlbear-project.json").read_text(encoding="utf-8"))
        dt = datetime.fromisoformat(data["created_at"])
        assert dt.tzinfo is not None, (
            f"created_at must be timezone-aware (UTC), got naive: {data['created_at']!r}"
        )

    def test_created_at_is_utc_offset_zero(self, tmp_path: Path) -> None:
        from setup import create_project_json  # type: ignore[import]

        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_project_json(project_dir, owlbear_dir)
        data = json.loads((project_dir / "owlbear-project.json").read_text(encoding="utf-8"))
        dt = datetime.fromisoformat(data["created_at"])
        assert dt.tzinfo is not None, "created_at is naive -- cannot check UTC offset"
        assert dt.utcoffset().total_seconds() == 0, (  # type: ignore[union-attr]
            f"created_at must be UTC (offset=0s), got offset: {dt.utcoffset()}"
        )

    def test_created_at_is_valid_iso8601(self, tmp_path: Path) -> None:
        from setup import create_project_json  # type: ignore[import]

        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_project_json(project_dir, owlbear_dir)
        data = json.loads((project_dir / "owlbear-project.json").read_text(encoding="utf-8"))
        try:
            datetime.fromisoformat(data["created_at"])
        except ValueError as exc:
            pytest.fail(f"created_at is not valid ISO 8601: {data['created_at']!r} -- {exc}")

    # ------------------------------------------------------------------
    # AC6: Constructs OwlbearProjectFile for validation; round-trip validates
    # ------------------------------------------------------------------

    def test_output_validates_against_owlbear_project_file_model(self, tmp_path: Path) -> None:
        from setup import create_project_json  # type: ignore[import]

        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        create_project_json(project_dir, owlbear_dir)
        raw = (project_dir / "owlbear-project.json").read_text(encoding="utf-8")
        OwlbearProjectFile.model_validate_json(raw)  # must not raise

    # ------------------------------------------------------------------
    # AC7: Idempotent: skips if file already exists (no overwrite)
    # ------------------------------------------------------------------

    def test_idempotent_skips_if_file_exists(self, tmp_path: Path) -> None:
        from setup import create_project_json  # type: ignore[import]

        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        sentinel = '{"SENTINEL_PROJECT": true}'
        (project_dir / "owlbear-project.json").write_text(sentinel, encoding="utf-8")
        create_project_json(project_dir, owlbear_dir)
        content = (project_dir / "owlbear-project.json").read_text(encoding="utf-8")
        assert "SENTINEL_PROJECT" in content, (
            "owlbear-project.json was overwritten despite already existing -- idempotency broken"
        )

    # ------------------------------------------------------------------
    # AC8: Called from setup() function
    # ------------------------------------------------------------------

    def test_setup_creates_owlbear_project_json(self, tmp_path: Path) -> None:
        """setup() must call create_project_json -- owlbear-project.json must exist after setup()."""
        project_dir = _project_dir(tmp_path)
        owlbear_dir = _make_owlbear_dir(tmp_path)
        setup(project_dir=project_dir, owlbear_dir=owlbear_dir)
        assert (project_dir / "owlbear-project.json").exists(), (
            "setup() did not create owlbear-project.json -- create_project_json not called from setup()"
        )
