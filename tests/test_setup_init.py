"""Failing tests for task #604 — Create seed/ templates and setup/init.py.

Covers:
  AC1  — seed/.vscode/settings.json: three chat.*Locations keys with {{owlbear_path}} placeholders
  AC2  — seed/.vscode/mcp.json: 3 owlbear kebab-case servers + ddgs + markitdown, --project placeholder in owlbear args
  AC3  — seed/.owlbear/kanban/config.yml: next_id: 1, standard statuses
  AC5  — seed/.owlbear/hooks/deny-writes.ps1 and lint-changed.ps1: static files present
  AC6  — seed/.owlbear/knowledge/.gitkeep: empty directory marker
  AC7  — seed/owlbear-project.json: {{name}} placeholder,
          NO computed-field placeholders (owlbear_path, created_at)
  AC8  — init(target_dir, owlbear_dir, *, name): seed/ walk, placeholder replacement,
          computed fields, idempotency, scratch-pad exclusion, __main__ guard, CLI args
  AC9  — init() does NOT create .github/ in target
  AC12 — settings.json deep merge: inner-dict union for chat.*Locations,
          user value wins on conflict, shallow merge for non-Location keys
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_OWLBEAR_DIR = Path(__file__).parent.parent
_SEED_DIR = _OWLBEAR_DIR / "seed"
_SETUP_DIR = _OWLBEAR_DIR / "setup"

# Insert setup/ on path so `from init import init` resolves once the builder creates it.
sys.path.insert(0, str(_SETUP_DIR))


# ---------------------------------------------------------------------------
# AC1 — seed/.vscode/settings.json template
# ---------------------------------------------------------------------------


class TestFromAC_SeedSettingsTemplate:
    """AC1: seed/.vscode/settings.json must exist with all three chat.*Locations keys."""

    def test_seed_vscode_settings_json_exists(self) -> None:
        assert (_SEED_DIR / ".vscode" / "settings.json").exists(), "seed/.vscode/settings.json does not exist"

    def test_seed_settings_has_agent_files_locations_key(self) -> None:
        data = json.loads((_SEED_DIR / ".vscode" / "settings.json").read_text(encoding="utf-8"))
        assert "chat.agentFilesLocations" in data

    def test_seed_settings_has_agent_skills_locations_key(self) -> None:
        data = json.loads((_SEED_DIR / ".vscode" / "settings.json").read_text(encoding="utf-8"))
        assert "chat.agentSkillsLocations" in data

    def test_seed_settings_has_instructions_files_locations_key(self) -> None:
        data = json.loads((_SEED_DIR / ".vscode" / "settings.json").read_text(encoding="utf-8"))
        assert "chat.instructionsFilesLocations" in data

    def test_seed_settings_path_values_use_owlbear_path_placeholder(self) -> None:
        """Every chat.*Locations entry must reference {{owlbear_path}} in at least one path key."""
        data = json.loads((_SEED_DIR / ".vscode" / "settings.json").read_text(encoding="utf-8"))
        all_path_keys: list[str] = []
        for key in (
            "chat.agentFilesLocations",
            "chat.agentSkillsLocations",
            "chat.instructionsFilesLocations",
        ):
            all_path_keys.extend(data[key].keys())
        assert any("{{owlbear_path}}" in p for p in all_path_keys), (
            f"No {{{{owlbear_path}}}} placeholder found in chat.*Locations path keys: {all_path_keys}"
        )


# ---------------------------------------------------------------------------
# AC2 — seed/.vscode/mcp.json template
# ---------------------------------------------------------------------------


class TestFromAC_SeedMcpTemplate:
    """AC2: seed/.vscode/mcp.json with owlbear servers + ddgs + markitdown; --project placeholder."""

    def test_seed_mcp_json_exists(self) -> None:
        assert (_SEED_DIR / ".vscode" / "mcp.json").exists(), "seed/.vscode/mcp.json does not exist"

    def test_seed_mcp_has_all_owlbear_kebab_case_servers(self) -> None:
        data = json.loads((_SEED_DIR / ".vscode" / "mcp.json").read_text(encoding="utf-8"))
        expected = {"owlbear-kanban", "owlbear-knowledge", "owlbear-memory"}
        missing = expected - set(data["servers"].keys())
        assert not missing, (
            f"Seed mcp.json missing kebab-case server keys: {missing}. Found: {list(data['servers'].keys())}"
        )

    def test_seed_mcp_owlbear_stdio_servers_include_project_flag(self) -> None:
        """AC2: owlbear stdio servers must have --project in args array."""
        data = json.loads((_SEED_DIR / ".vscode" / "mcp.json").read_text(encoding="utf-8"))
        for name, entry in data["servers"].items():
            if entry.get("type") == "stdio" and name.startswith("owlbear-"):
                args = entry.get("args", [])
                assert "--project" in args, f"stdio server '{name}' missing --project in args: {args}"

    def test_seed_mcp_owlbear_stdio_servers_include_owlbear_path_placeholder(self) -> None:
        """AC2: owlbear stdio server args must include {{owlbear_path}} placeholder for replacement."""
        data = json.loads((_SEED_DIR / ".vscode" / "mcp.json").read_text(encoding="utf-8"))
        for name, entry in data["servers"].items():
            if entry.get("type") == "stdio" and name.startswith("owlbear-"):
                args = entry.get("args", [])
                assert "{{owlbear_path}}" in args, (
                    f"stdio server '{name}' missing {{{{owlbear_path}}}} placeholder in args: {args}"
                )


# ---------------------------------------------------------------------------
# AC3 — seed/.owlbear/kanban/config.yml
# ---------------------------------------------------------------------------


class TestFromAC_SeedKanbanConfig:
    """AC3: seed/.owlbear/kanban/config.yml with next_id: 1 and standard statuses."""

    def test_seed_kanban_config_yml_exists(self) -> None:
        assert (_SEED_DIR / ".owlbear" / "kanban" / "config.yml").exists(), (
            "seed/.owlbear/kanban/config.yml does not exist"
        )

    def test_seed_kanban_config_has_next_id_one(self) -> None:
        content = (_SEED_DIR / ".owlbear" / "kanban" / "config.yml").read_text(encoding="utf-8")
        assert "next_id: 1" in content, f"seed kanban/config.yml must have 'next_id: 1' — got:\n{content}"

    def test_seed_kanban_config_has_standard_statuses(self) -> None:
        """Standard pipeline statuses must match the current board statuses."""
        content = (_SEED_DIR / ".owlbear" / "kanban" / "config.yml").read_text(encoding="utf-8")
        for status in ("todo", "in-progress", "done"):
            assert status in content, f"Standard status '{status}' missing from seed kanban/config.yml"


# ---------------------------------------------------------------------------
# AC5 — seed/.owlbear/hooks/deny-writes.ps1 and lint-changed.ps1
# ---------------------------------------------------------------------------


class TestFromAC_SeedHooks:
    """AC5: both hook scripts must exist under seed/.owlbear/hooks/."""

    def test_seed_deny_writes_ps1_exists(self) -> None:
        assert (_SEED_DIR / ".owlbear" / "hooks" / "deny-writes.ps1").exists(), (
            "seed/.owlbear/hooks/deny-writes.ps1 does not exist"
        )

    def test_seed_lint_changed_ps1_exists(self) -> None:
        assert (_SEED_DIR / ".owlbear" / "hooks" / "lint-changed.ps1").exists(), (
            "seed/.owlbear/hooks/lint-changed.ps1 does not exist"
        )


# ---------------------------------------------------------------------------
# AC6 — seed/.owlbear/knowledge/.gitkeep
# ---------------------------------------------------------------------------


class TestFromAC_SeedKnowledgeGitkeep:
    """AC6: seed/.owlbear/knowledge/.gitkeep directory marker must exist."""

    def test_seed_knowledge_gitkeep_exists(self) -> None:
        assert (_SEED_DIR / ".owlbear" / "knowledge" / ".gitkeep").exists(), (
            "seed/.owlbear/knowledge/.gitkeep does not exist"
        )


# ---------------------------------------------------------------------------
# Store directories for MCP servers
# ---------------------------------------------------------------------------


class TestSeedStoreDirs:
    """MCP servers need store/ directories for their SQLite databases."""

    def test_seed_store_knowledge_gitkeep_exists(self) -> None:
        assert (_SEED_DIR / "store" / "knowledge" / ".gitkeep").exists(), (
            "seed/store/knowledge/.gitkeep does not exist — knowledge MCP server needs this directory"
        )

    def test_seed_store_memory_gitkeep_exists(self) -> None:
        assert (_SEED_DIR / "store" / "memory" / ".gitkeep").exists(), (
            "seed/store/memory/.gitkeep does not exist — memory MCP server needs this directory"
        )

    def test_init_creates_store_knowledge_dir(self, tmp_path: Path) -> None:
        from init import init  # type: ignore[import]

        target = tmp_path / "target"
        target.mkdir()
        init(target, _OWLBEAR_DIR)
        assert (target / "store" / "knowledge" / ".gitkeep").exists()

    def test_init_creates_store_memory_dir(self, tmp_path: Path) -> None:
        from init import init  # type: ignore[import]

        target = tmp_path / "target"
        target.mkdir()
        init(target, _OWLBEAR_DIR)
        assert (target / "store" / "memory" / ".gitkeep").exists()


# ---------------------------------------------------------------------------
# AC7 — seed/owlbear-project.json template
# ---------------------------------------------------------------------------


class TestFromAC_SeedOwlbearProjectJson:
    """AC7: seed/owlbear-project.json with {{name}} placeholder."""

    def test_seed_owlbear_project_json_exists(self) -> None:
        assert (_SEED_DIR / "owlbear-project.json").exists(), "seed/owlbear-project.json does not exist"

    def test_seed_owlbear_project_json_has_name_placeholder(self) -> None:
        content = (_SEED_DIR / "owlbear-project.json").read_text(encoding="utf-8")
        assert "{{name}}" in content, "seed/owlbear-project.json missing {{name}} placeholder"

    def test_seed_owlbear_project_json_has_no_computed_field_placeholders(self) -> None:
        """owlbear_path and created_at are computed at runtime — must NOT be template placeholders."""
        content = (_SEED_DIR / "owlbear-project.json").read_text(encoding="utf-8")
        assert "{{owlbear_path}}" not in content, (
            "owlbear_path must be computed by init.py, not a seed template placeholder"
        )
        assert "{{created_at}}" not in content, (
            "created_at must be computed by init.py, not a seed template placeholder"
        )


# ---------------------------------------------------------------------------
# AC8 — init() function contract
# ---------------------------------------------------------------------------


class TestFromAC_InitFunction:
    """AC8: init(target_dir, owlbear_dir, *, name) walks seed/, replaces placeholders."""

    def test_init_creates_vscode_settings_json(self, tmp_path: Path) -> None:
        from init import init  # type: ignore[import]  # ImportError until builder creates setup/init.py

        target = tmp_path / "target"
        target.mkdir()
        init(target, _OWLBEAR_DIR)
        assert (target / ".vscode" / "settings.json").exists(), "init() did not create .vscode/settings.json"

    def test_init_creates_mcp_json(self, tmp_path: Path) -> None:
        from init import init  # type: ignore[import]

        target = tmp_path / "target"
        target.mkdir()
        init(target, _OWLBEAR_DIR)
        assert (target / ".vscode" / "mcp.json").exists(), "init() did not create .vscode/mcp.json"

    def test_init_settings_json_has_no_raw_placeholder_left(self, tmp_path: Path) -> None:
        """After init(), settings.json must have {{owlbear_path}} fully replaced."""
        from init import init  # type: ignore[import]

        target = tmp_path / "target"
        target.mkdir()
        init(target, _OWLBEAR_DIR)
        content = (target / ".vscode" / "settings.json").read_text(encoding="utf-8")
        assert "{{owlbear_path}}" not in content, (
            "settings.json still contains {{owlbear_path}} after init() — placeholder not replaced"
        )

    def test_init_mcp_json_has_no_raw_placeholder_left(self, tmp_path: Path) -> None:
        """After init(), mcp.json must have {{owlbear_path}} fully replaced."""
        from init import init  # type: ignore[import]

        target = tmp_path / "target"
        target.mkdir()
        init(target, _OWLBEAR_DIR)
        content = (target / ".vscode" / "mcp.json").read_text(encoding="utf-8")
        assert "{{owlbear_path}}" not in content, (
            "mcp.json still contains {{owlbear_path}} after init() — placeholder not replaced"
        )

    def test_init_creates_owlbear_project_json(self, tmp_path: Path) -> None:
        from init import init  # type: ignore[import]

        target = tmp_path / "target"
        target.mkdir()
        init(target, _OWLBEAR_DIR)
        assert (target / "owlbear-project.json").exists(), "init() did not create owlbear-project.json"

    def test_init_owlbear_project_json_name_defaults_to_target_dir_name(self, tmp_path: Path) -> None:
        from init import init  # type: ignore[import]

        target = tmp_path / "my-project-dir"
        target.mkdir()
        init(target, _OWLBEAR_DIR)
        data = json.loads((target / "owlbear-project.json").read_text(encoding="utf-8"))
        assert data["name"] == "my-project-dir", (
            f"name should default to target dir name 'my-project-dir', got {data['name']!r}"
        )

    def test_init_owlbear_project_json_name_accepts_kwarg(self, tmp_path: Path) -> None:
        from init import init  # type: ignore[import]

        target = tmp_path / "target"
        target.mkdir()
        init(target, _OWLBEAR_DIR, name="custom-project-name")
        data = json.loads((target / "owlbear-project.json").read_text(encoding="utf-8"))
        assert data["name"] == "custom-project-name", f"explicit name kwarg not respected, got {data['name']!r}"

    def test_init_owlbear_project_json_owlbear_path_is_relative_posix(self, tmp_path: Path) -> None:
        from init import init  # type: ignore[import]

        target = tmp_path / "target"
        target.mkdir()
        init(target, _OWLBEAR_DIR)
        data = json.loads((target / "owlbear-project.json").read_text(encoding="utf-8"))
        owlbear_path = data["owlbear_path"]
        assert "\\" not in owlbear_path, f"owlbear_path must use forward slashes (POSIX), got: {owlbear_path!r}"
        assert not Path(owlbear_path).is_absolute(), (
            f"owlbear_path must be relative (via os.path.relpath), got absolute: {owlbear_path!r}"
        )

    def test_init_owlbear_project_json_created_at_is_utc_aware(self, tmp_path: Path) -> None:
        from init import init  # type: ignore[import]

        target = tmp_path / "target"
        target.mkdir()
        init(target, _OWLBEAR_DIR)
        data = json.loads((target / "owlbear-project.json").read_text(encoding="utf-8"))
        dt = datetime.fromisoformat(data["created_at"])
        assert dt.tzinfo is not None, "created_at must be timezone-aware (UTC)"
        assert dt.utcoffset() is not None, "created_at utcoffset must not be None"
        assert dt.utcoffset().total_seconds() == 0, (  # type: ignore[union-attr]
            f"created_at must be UTC (offset=0), got {dt.utcoffset()}"
        )

    def test_init_excludes_scratch_pad_txt_from_target(self, tmp_path: Path) -> None:
        """seed/scratch-pad.txt must NOT be copied to the target directory."""
        from init import init  # type: ignore[import]

        target = tmp_path / "target"
        target.mkdir()
        init(target, _OWLBEAR_DIR)
        assert not (target / "scratch-pad.txt").exists(), (
            "scratch-pad.txt was copied to target — init() must exclude it"
        )

    def test_init_idempotent_merges_mcp_json_preserving_user_servers(self, tmp_path: Path) -> None:
        """Pre-existing user servers in mcp.json must survive the merge."""
        from init import init  # type: ignore[import]

        target = tmp_path / "target"
        target.mkdir()
        vscode_dir = target / ".vscode"
        vscode_dir.mkdir(parents=True)
        (vscode_dir / "mcp.json").write_text(
            json.dumps({"servers": {"my-custom-server": {"type": "stdio", "command": "echo"}}}),
            encoding="utf-8",
        )
        init(target, _OWLBEAR_DIR)
        data = json.loads((target / ".vscode" / "mcp.json").read_text(encoding="utf-8"))
        assert "my-custom-server" in data["servers"], (
            "User server 'my-custom-server' was lost during mcp.json merge"
        )
        # Owlbear servers should also be present
        assert "owlbear-kanban" in data["servers"], (
            "Owlbear server 'owlbear-kanban' was not added during mcp.json merge"
        )

    def test_init_idempotent_skips_owlbear_project_json_if_exists(self, tmp_path: Path) -> None:
        """owlbear-project.json must not be overwritten on second call."""
        from init import init  # type: ignore[import]

        target = tmp_path / "target"
        target.mkdir()
        (target / "owlbear-project.json").write_text('{"SENTINEL_PROJECT": true}', encoding="utf-8")
        init(target, _OWLBEAR_DIR)
        content = (target / "owlbear-project.json").read_text(encoding="utf-8")
        assert "SENTINEL_PROJECT" in content, (
            "owlbear-project.json was overwritten despite existing — idempotency broken"
        )

    def test_init_creates_directories_idempotently(self, tmp_path: Path) -> None:
        """Calling init() twice must not raise any exception."""
        from init import init  # type: ignore[import]

        target = tmp_path / "target"
        target.mkdir()
        init(target, _OWLBEAR_DIR)
        init(target, _OWLBEAR_DIR)  # must not raise


# ---------------------------------------------------------------------------
# AC9 — init() must NOT create .github/
# ---------------------------------------------------------------------------


class TestFromAC_NoGithubDir:
    """AC9: init() must not create .github/ directory in the target project."""

    def test_no_github_directory_created(self, tmp_path: Path) -> None:
        from init import init  # type: ignore[import]

        target = tmp_path / "target"
        target.mkdir()
        init(target, _OWLBEAR_DIR)
        assert not (target / ".github").exists(), (
            ".github/ was created by init() — AC9 explicitly prohibits this "
            "(target projects create their own copilot-instructions.md)"
        )


# ---------------------------------------------------------------------------
# AC12 — settings.json deep merge
# ---------------------------------------------------------------------------


class TestFromAC_SettingsDeepMerge:
    """AC12: chat.*Locations deep merge — inner-dict union; user value wins on conflict."""

    def test_deep_merge_preserves_user_chat_agent_paths(self, tmp_path: Path) -> None:
        """User-defined paths in chat.agentFilesLocations must survive the merge."""
        from init import init  # type: ignore[import]

        target = tmp_path / "target"
        target.mkdir()
        vscode = target / ".vscode"
        vscode.mkdir(parents=True)
        (vscode / "settings.json").write_text(
            json.dumps({"chat.agentFilesLocations": {"my/custom/agents": True}}),
            encoding="utf-8",
        )
        init(target, _OWLBEAR_DIR)
        data = json.loads((target / ".vscode" / "settings.json").read_text(encoding="utf-8"))
        assert "my/custom/agents" in data["chat.agentFilesLocations"], (
            "User path 'my/custom/agents' was lost during deep merge of chat.agentFilesLocations"
        )

    def test_deep_merge_all_three_chat_location_keys_unioned(self, tmp_path: Path) -> None:
        """User paths for all three chat.*Locations keys must coexist with owlbear paths."""
        from init import init  # type: ignore[import]

        target = tmp_path / "target"
        target.mkdir()
        vscode = target / ".vscode"
        vscode.mkdir(parents=True)
        existing = {
            "chat.agentFilesLocations": {"user/agents": True},
            "chat.agentSkillsLocations": {"user/skills": True},
            "chat.instructionsFilesLocations": {"user/instructions": True},
        }
        (vscode / "settings.json").write_text(json.dumps(existing), encoding="utf-8")
        init(target, _OWLBEAR_DIR)
        data = json.loads((target / ".vscode" / "settings.json").read_text(encoding="utf-8"))
        for key, user_path in (
            ("chat.agentFilesLocations", "user/agents"),
            ("chat.agentSkillsLocations", "user/skills"),
            ("chat.instructionsFilesLocations", "user/instructions"),
        ):
            assert user_path in data[key], f"User path '{user_path}' in {key} was lost during deep merge"

    def test_deep_merge_user_value_wins_on_same_path_conflict(self, tmp_path: Path) -> None:
        """When user and owlbear have the same path key, user's value (bool) takes priority."""
        from init import init  # type: ignore[import]

        # Probe: run init once to discover what owlbear path keys will be set
        probe = tmp_path / "probe"
        probe.mkdir()
        init(probe, _OWLBEAR_DIR)
        probe_data = json.loads((probe / ".vscode" / "settings.json").read_text(encoding="utf-8"))
        agent_paths = list(probe_data.get("chat.agentFilesLocations", {}).keys())
        if not agent_paths:
            pytest.skip("No agentFilesLocations paths resolved — cannot test conflict")
        conflict_path = agent_paths[0]

        # Target: user pre-sets the same path to False
        target = tmp_path / "target"
        target.mkdir()
        vscode = target / ".vscode"
        vscode.mkdir(parents=True)
        (vscode / "settings.json").write_text(
            json.dumps({"chat.agentFilesLocations": {conflict_path: False}}),
            encoding="utf-8",
        )
        init(target, _OWLBEAR_DIR)
        data = json.loads((target / ".vscode" / "settings.json").read_text(encoding="utf-8"))
        assert data["chat.agentFilesLocations"].get(conflict_path) is False, (
            f"User value False should override owlbear default True for path {conflict_path!r}"
        )

    def test_deep_merge_non_location_keys_shallow_merged_user_wins(self, tmp_path: Path) -> None:
        """Non-chat.*Locations keys: existing user values override owlbear defaults."""
        from init import init  # type: ignore[import]

        target = tmp_path / "target"
        target.mkdir()
        vscode = target / ".vscode"
        vscode.mkdir(parents=True)
        (vscode / "settings.json").write_text(
            json.dumps({"editor.fontSize": 18, "editor.wordWrap": "wordWrapColumn"}),
            encoding="utf-8",
        )
        init(target, _OWLBEAR_DIR)
        data = json.loads((target / ".vscode" / "settings.json").read_text(encoding="utf-8"))
        assert data.get("editor.fontSize") == 18, (
            "editor.fontSize was overwritten — user values must win in shallow merge"
        )
        assert data.get("editor.wordWrap") == "wordWrapColumn", (
            "editor.wordWrap was overwritten — user values must win in shallow merge"
        )

    def test_deep_merge_adds_owlbear_paths_to_existing_chat_location_entries(self, tmp_path: Path) -> None:
        """After merge, chat.agentFilesLocations must contain more than just the user's single path."""
        from init import init  # type: ignore[import]

        target = tmp_path / "target"
        target.mkdir()
        vscode = target / ".vscode"
        vscode.mkdir(parents=True)
        (vscode / "settings.json").write_text(
            json.dumps({"chat.agentFilesLocations": {"my/solo/agents": True}}),
            encoding="utf-8",
        )
        init(target, _OWLBEAR_DIR)
        data = json.loads((target / ".vscode" / "settings.json").read_text(encoding="utf-8"))
        all_paths = data.get("chat.agentFilesLocations", {})
        assert len(all_paths) >= 2, (
            f"Deep merge should add owlbear paths alongside user path, "
            f"but agentFilesLocations has only {len(all_paths)} entry/entries: {list(all_paths.keys())}"
        )


# ---------------------------------------------------------------------------
# AC8 — CLI interface (setup/init.py as __main__)
# ---------------------------------------------------------------------------


class TestFromAC_CliInterface:
    """AC8: CLI `python ../owlbear/setup/init.py [--name NAME] [--type TYPE]` must work."""

    def test_init_script_has_main_guard(self) -> None:
        """setup/init.py must have an `if __name__ == '__main__':` guard to be directly runnable."""
        script = _SETUP_DIR / "init.py"
        content = script.read_text(encoding="utf-8")
        assert '__name__ == "__main__"' in content, (
            "setup/init.py has no if __name__ == '__main__' guard — running `python setup/init.py` would be a no-op"
        )

    def test_cli_accepts_name_argument(self, tmp_path: Path) -> None:
        """CLI must accept --name NAME and write it to owlbear-project.json."""
        script = _SETUP_DIR / "init.py"
        target = tmp_path / "target"
        target.mkdir()
        result = subprocess.run(
            [sys.executable, str(script), "--name", "cli-project-name"],
            cwd=str(target),
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"CLI exited non-zero ({result.returncode})\nstderr: {result.stderr}"
        data = json.loads((target / "owlbear-project.json").read_text(encoding="utf-8"))
        assert data["name"] == "cli-project-name", (
            f"--name kwarg not written to owlbear-project.json, got {data['name']!r}"
        )


# ---------------------------------------------------------------------------
# JSONC comment handling in settings.json
# ---------------------------------------------------------------------------


class TestSettingsJsoncMerge:
    """settings.json with JSONC comments must be parsed and merged, not overwritten."""

    def test_jsonc_comments_are_stripped_and_settings_merged(self, tmp_path: Path) -> None:
        """Existing settings.json with // comments must be parsed correctly."""
        from init import init  # type: ignore[import]

        target = tmp_path / "target"
        target.mkdir()
        vscode = target / ".vscode"
        vscode.mkdir(parents=True)
        (vscode / "settings.json").write_text(
            '{\n  "editor.fontSize": 16, // my preferred size\n  "editor.tabSize": 4\n}\n',
            encoding="utf-8",
        )
        init(target, _OWLBEAR_DIR)
        data = json.loads((target / ".vscode" / "settings.json").read_text(encoding="utf-8"))
        assert data.get("editor.fontSize") == 16, "User setting lost during JSONC merge"
        assert data.get("editor.tabSize") == 4, "User setting lost during JSONC merge"
        assert "chat.agentFilesLocations" in data, "Owlbear settings not added during merge"

    def test_jsonc_trailing_comments_after_booleans(self, tmp_path: Path) -> None:
        """Common pattern: `true, // false` trailing comments must not break parsing."""
        from init import init  # type: ignore[import]

        target = tmp_path / "target"
        target.mkdir()
        vscode = target / ".vscode"
        vscode.mkdir(parents=True)
        (vscode / "settings.json").write_text(
            '{\n  "editor.wordWrap": "on", // off\n  "chat.agent.maxRequests": 250\n}\n',
            encoding="utf-8",
        )
        init(target, _OWLBEAR_DIR)
        data = json.loads((target / ".vscode" / "settings.json").read_text(encoding="utf-8"))
        assert data.get("editor.wordWrap") == "on", "JSONC trailing comment broke parsing"
        assert data.get("chat.agent.maxRequests") == 250, "User setting lost during JSONC merge"


# ---------------------------------------------------------------------------
# mcp.json merge logic
# ---------------------------------------------------------------------------


class TestMcpJsonMerge:
    """mcp.json must be merged, not skipped or overwritten."""

    def test_mcp_merge_adds_owlbear_servers_to_existing(self, tmp_path: Path) -> None:
        from init import init  # type: ignore[import]

        target = tmp_path / "target"
        target.mkdir()
        vscode = target / ".vscode"
        vscode.mkdir(parents=True)
        (vscode / "mcp.json").write_text(
            json.dumps({"servers": {"my-server": {"type": "stdio", "command": "echo"}}}),
            encoding="utf-8",
        )
        init(target, _OWLBEAR_DIR)
        data = json.loads((target / ".vscode" / "mcp.json").read_text(encoding="utf-8"))
        assert "my-server" in data["servers"], "User server lost"
        assert "owlbear-kanban" in data["servers"], "Owlbear server not added"
        assert "owlbear-memory" in data["servers"], "Owlbear server not added"

    def test_mcp_merge_user_server_wins_on_key_conflict(self, tmp_path: Path) -> None:
        """If user has an owlbear-kanban entry already, user's version wins."""
        from init import init  # type: ignore[import]

        target = tmp_path / "target"
        target.mkdir()
        vscode = target / ".vscode"
        vscode.mkdir(parents=True)
        user_entry = {"type": "stdio", "command": "my-custom-kanban"}
        (vscode / "mcp.json").write_text(
            json.dumps({"servers": {"owlbear-kanban": user_entry}}),
            encoding="utf-8",
        )
        init(target, _OWLBEAR_DIR)
        data = json.loads((target / ".vscode" / "mcp.json").read_text(encoding="utf-8"))
        assert data["servers"]["owlbear-kanban"]["command"] == "my-custom-kanban", (
            "User's owlbear-kanban entry should win on conflict"
        )

    def test_mcp_merge_fresh_project_gets_all_servers(self, tmp_path: Path) -> None:
        """Fresh project with no existing mcp.json gets all owlbear servers."""
        from init import init  # type: ignore[import]

        target = tmp_path / "target"
        target.mkdir()
        init(target, _OWLBEAR_DIR)
        data = json.loads((target / ".vscode" / "mcp.json").read_text(encoding="utf-8"))
        for expected in ("owlbear-kanban", "owlbear-knowledge", "owlbear-memory", "ddgs"):
            assert expected in data["servers"], f"Server '{expected}' missing from fresh mcp.json"

    def test_mcp_merge_no_raw_placeholders_remain(self, tmp_path: Path) -> None:
        """After merge, no {{owlbear_path}} placeholders should remain."""
        from init import init  # type: ignore[import]

        target = tmp_path / "target"
        target.mkdir()
        init(target, _OWLBEAR_DIR)
        content = (target / ".vscode" / "mcp.json").read_text(encoding="utf-8")
        assert "{{owlbear_path}}" not in content, "mcp.json still contains raw placeholder"


# ---------------------------------------------------------------------------
# Dict-merge for non-Location dict keys (files.exclude, autoApprove, etc.)
# ---------------------------------------------------------------------------


class TestDictKeyMerge:
    """Dict-valued settings like files.exclude must be union-merged, not replaced."""

    def test_files_exclude_union_merged(self, tmp_path: Path) -> None:
        """User's files.exclude entries survive alongside owlbear defaults."""
        from init import init  # type: ignore[import]

        target = tmp_path / "target"
        target.mkdir()
        vscode = target / ".vscode"
        vscode.mkdir(parents=True)
        (vscode / "settings.json").write_text(
            json.dumps({"files.exclude": {"dist": True, "build": True}}),
            encoding="utf-8",
        )
        init(target, _OWLBEAR_DIR)
        data = json.loads((target / ".vscode" / "settings.json").read_text(encoding="utf-8"))
        fe = data.get("files.exclude", {})
        assert "dist" in fe, "User files.exclude entry 'dist' lost during merge"
        assert ".venv" in fe, "Owlbear files.exclude entry '.venv' not added"

    def test_terminal_auto_approve_union_merged(self, tmp_path: Path) -> None:
        """User's terminal auto-approve patterns coexist with owlbear defaults."""
        from init import init  # type: ignore[import]

        target = tmp_path / "target"
        target.mkdir()
        vscode = target / ".vscode"
        vscode.mkdir(parents=True)
        (vscode / "settings.json").write_text(
            json.dumps({"chat.tools.terminal.autoApprove": {"npm test": True}}),
            encoding="utf-8",
        )
        init(target, _OWLBEAR_DIR)
        data = json.loads((target / ".vscode" / "settings.json").read_text(encoding="utf-8"))
        ta = data.get("chat.tools.terminal.autoApprove", {})
        assert "npm test" in ta, "User auto-approve pattern lost"
        assert "uv run pytest" in ta, "Owlbear auto-approve pattern not added"

    def test_language_scoped_keys_union_merged(self, tmp_path: Path) -> None:
        """Language-scoped keys like [json] must be dict-merged."""
        from init import init  # type: ignore[import]

        target = tmp_path / "target"
        target.mkdir()
        vscode = target / ".vscode"
        vscode.mkdir(parents=True)
        (vscode / "settings.json").write_text(
            json.dumps({"[json]": {"editor.tabSize": 2}}),
            encoding="utf-8",
        )
        init(target, _OWLBEAR_DIR)
        data = json.loads((target / ".vscode" / "settings.json").read_text(encoding="utf-8"))
        json_settings = data.get("[json]", {})
        assert json_settings.get("editor.tabSize") == 2, "User [json] setting lost"
        assert "editor.formatOnSave" in json_settings, "Owlbear [json] setting not added"


# ---------------------------------------------------------------------------
# Dotfile seeding
# ---------------------------------------------------------------------------


class TestSeedDotfiles:
    """Dotfiles must exist in seed and be handled correctly by init()."""

    @pytest.mark.parametrize(
        "filename",
        [".editorconfig", ".gitattributes", ".gitignore", ".markdownlint.json",
         ".markdownlint-cli2.jsonc", ".markdownlintignore"],
    )
    def test_seed_dotfile_exists(self, filename: str) -> None:
        assert (_SEED_DIR / filename).exists(), f"seed/{filename} does not exist"

    @pytest.mark.parametrize(
        "filename",
        [".editorconfig", ".gitattributes", ".markdownlint.json",
         ".markdownlint-cli2.jsonc", ".markdownlintignore"],
    )
    def test_skip_if_exists_dotfiles_not_overwritten(self, filename: str, tmp_path: Path) -> None:
        """Dotfiles in _SKIP_IF_EXISTS_REL must not be overwritten."""
        from init import init  # type: ignore[import]

        target = tmp_path / "target"
        target.mkdir()
        (target / filename).write_text("SENTINEL", encoding="utf-8")
        init(target, _OWLBEAR_DIR)
        assert (target / filename).read_text(encoding="utf-8") == "SENTINEL", (
            f"{filename} was overwritten despite already existing"
        )

    def test_fresh_project_gets_gitignore(self, tmp_path: Path) -> None:
        from init import init  # type: ignore[import]

        target = tmp_path / "target"
        target.mkdir()
        init(target, _OWLBEAR_DIR)
        assert (target / ".gitignore").exists(), ".gitignore not created for fresh project"
        content = (target / ".gitignore").read_text(encoding="utf-8")
        assert "# --- OwlBear managed paths ---" in content

    def test_gitignore_appends_owlbear_section_to_existing(self, tmp_path: Path) -> None:
        """If .gitignore exists without the owlbear marker, the owlbear section is appended."""
        from init import init  # type: ignore[import]

        target = tmp_path / "target"
        target.mkdir()
        (target / ".gitignore").write_text("node_modules/\n*.log\n", encoding="utf-8")
        init(target, _OWLBEAR_DIR)
        content = (target / ".gitignore").read_text(encoding="utf-8")
        assert "node_modules/" in content, "Original .gitignore content lost"
        assert "# --- OwlBear managed paths ---" in content, "OwlBear section not appended"
        assert ".owlbear/scratch/*" in content, "OwlBear scratch pattern not appended"

    def test_gitignore_idempotent_with_marker(self, tmp_path: Path) -> None:
        """If the owlbear marker is already present, nothing is appended."""
        from init import init  # type: ignore[import]

        target = tmp_path / "target"
        target.mkdir()
        original = "*.log\n# --- OwlBear managed paths ---\n.owlbear/scratch/*\n"
        (target / ".gitignore").write_text(original, encoding="utf-8")
        init(target, _OWLBEAR_DIR)
        assert (target / ".gitignore").read_text(encoding="utf-8") == original, (
            ".gitignore was modified despite already having the owlbear marker"
        )
