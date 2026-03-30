"""Failing tests for task #209: Add stop commit guard hooks to builder and writer agents (Phase 1).

AC contract under test:
1. scripts/hooks/stop-commit-guard.ps1 exists and:
   - Reads stdin JSON for hook context
   - Returns immediately (empty JSON) if stop_hook_active is true
   - Runs git status --short to detect uncommitted changes
   - If dirty: returns JSON with decision "block" and a reason
   - If clean: returns empty JSON {}
2. agents/builder.agent.md YAML frontmatter has a Stop hook section
   (type: command, windows: powershell ... stop-commit-guard.ps1)
3. agents/writer.agent.md YAML frontmatter has an identical hooks section
4. .vscode/settings.json has chat.useCustomAgentHooks: true
5. Both agent files have valid YAML frontmatter (verified via parse)
6. Script handles three behavioral cases: clean, dirty, stop_hook_active

All tests fail on current HEAD because:
- scripts/hooks/stop-commit-guard.ps1 does not exist yet
- Neither agent file has a hooks: section
- .vscode/settings.json does not contain chat.useCustomAgentHooks
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Repo-level paths
# ---------------------------------------------------------------------------
_REPO = Path(__file__).parent.parent
_SCRIPT = _REPO / "scripts" / "hooks" / "stop-commit-guard.ps1"
_BUILDER_AGENT = _REPO / "agents" / "builder.agent.md"
_WRITER_AGENT = _REPO / "agents" / "writer.agent.md"
_SETTINGS = _REPO / ".vscode" / "settings.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_frontmatter(agent_file: Path) -> str:
    """Return the raw YAML frontmatter text from a .agent.md file."""
    text = agent_file.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"No valid frontmatter delimiters in {agent_file}")
    return parts[1]


def _run_script(
    stdin_payload: dict[str, Any],
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Invoke stop-commit-guard.ps1 with the given stdin JSON."""
    return subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-File", str(_SCRIPT)],
        input=json.dumps(stdin_payload),
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
    )


# ---------------------------------------------------------------------------
# TestFromAC_StopCommitGuardScript
# AC1 (file + content) and AC6 (behavioral, three cases)
# ---------------------------------------------------------------------------


class TestFromAC_StopCommitGuardScript:
    """AC1 + AC6: stop-commit-guard.ps1 must exist and handle all three hook cases."""

    # --- Happy: file and content structure ---

    def test_script_file_exists(self) -> None:
        """AC1: script file must exist at scripts/hooks/stop-commit-guard.ps1."""
        assert _SCRIPT.exists(), f"Script not found: {_SCRIPT}"

    def test_script_reads_stdin(self) -> None:
        """AC1: script must read stdin to obtain the hook context JSON."""
        assert _SCRIPT.exists(), f"Script not found: {_SCRIPT}"
        text = _SCRIPT.read_text(encoding="utf-8")
        stdin_keywords = ("stdin", "ReadToEnd", "$input", "Read-Host", "[Console]::In")
        assert any(kw.lower() in text.lower() for kw in stdin_keywords), (
            "Script must read stdin JSON for hook context"
        )

    def test_script_contains_stop_hook_active_guard(self) -> None:
        """AC1: script must check stop_hook_active to prevent infinite re-fires."""
        assert _SCRIPT.exists(), f"Script not found: {_SCRIPT}"
        text = _SCRIPT.read_text(encoding="utf-8")
        assert "stop_hook_active" in text, (
            "Script must check stop_hook_active to prevent looping (AC1 loop prevention)"
        )

    def test_script_runs_git_status_short(self) -> None:
        """AC1: script must run 'git status --short' to detect uncommitted changes."""
        assert _SCRIPT.exists(), f"Script not found: {_SCRIPT}"
        text = _SCRIPT.read_text(encoding="utf-8")
        assert "git status" in text.lower(), (
            "Script must call 'git status' to check for uncommitted changes"
        )
        assert "--short" in text, (
            "Script must use 'git status --short' (not the verbose form)"
        )

    def test_script_produces_block_decision_key(self) -> None:
        """AC1: dirty-tree output must contain a 'decision' key with value 'block'."""
        assert _SCRIPT.exists(), f"Script not found: {_SCRIPT}"
        text = _SCRIPT.read_text(encoding="utf-8")
        assert "decision" in text, (
            "Script must produce JSON with a 'decision' key when tree is dirty"
        )
        assert "block" in text.lower(), (
            "Script must set decision to 'block' to prevent session from ending"
        )

    def test_script_produces_reason_key(self) -> None:
        """AC1: dirty-tree output must include a 'reason' explaining the block."""
        assert _SCRIPT.exists(), f"Script not found: {_SCRIPT}"
        text = _SCRIPT.read_text(encoding="utf-8")
        assert "reason" in text, (
            "Script must include a 'reason' key in the block JSON output"
        )

    # --- Behavioral: AC6 three cases (subprocess, uses temp git repos) ---

    @pytest.mark.slow
    def test_script_stop_hook_active_returns_empty_json(self) -> None:
        """AC6c: when stop_hook_active is true, script returns empty JSON immediately."""
        result = _run_script({"stop_hook_active": True})
        assert result.returncode == 0, (
            f"Script exited with code {result.returncode}. stderr: {result.stderr!r}"
        )
        output = result.stdout.strip()
        parsed: dict[str, Any] = json.loads(output) if output else {}
        assert parsed == {}, (
            f"Expected empty JSON {{}} when stop_hook_active is true, got: {parsed!r}"
        )

    @pytest.mark.slow
    def test_script_clean_tree_returns_empty_json(self, tmp_path: Path) -> None:
        """AC6a: when working tree is clean, script returns empty JSON {}."""
        subprocess.run(
            ["git", "init", str(tmp_path)], capture_output=True, check=True
        )
        # Configure git identity so git commands don't fail
        subprocess.run(
            ["git", "-C", str(tmp_path), "config", "user.email", "test@test.com"],
            capture_output=True,
            check=True,
        )
        result = _run_script({"stop_hook_active": False}, cwd=tmp_path)
        assert result.returncode == 0, (
            f"Script exited with code {result.returncode}. stderr: {result.stderr!r}"
        )
        output = result.stdout.strip()
        parsed: dict[str, Any] = json.loads(output) if output else {}
        assert parsed == {}, (
            f"Expected empty JSON for clean tree, got: {parsed!r}"
        )

    @pytest.mark.slow
    def test_script_dirty_tree_returns_block_decision(self, tmp_path: Path) -> None:
        """AC6b: when working tree is dirty, script returns block decision JSON."""
        subprocess.run(
            ["git", "init", str(tmp_path)], capture_output=True, check=True
        )
        subprocess.run(
            ["git", "-C", str(tmp_path), "config", "user.email", "test@test.com"],
            capture_output=True,
            check=True,
        )
        # Create an untracked file to make the tree dirty
        (tmp_path / "uncommitted.py").write_text("# dirty\n", encoding="utf-8")
        result = _run_script({"stop_hook_active": False}, cwd=tmp_path)
        assert result.returncode == 0, (
            f"Script exited with code {result.returncode}. stderr: {result.stderr!r}"
        )
        output = result.stdout.strip()
        assert output, "Script must produce output for dirty tree"
        parsed: dict[str, Any] = json.loads(output)
        assert parsed.get("decision") == "block", (
            f"Expected decision='block' for dirty tree, got: {parsed!r}"
        )
        assert "reason" in parsed, (
            f"Block JSON must include a 'reason' key, got: {parsed!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_BuilderAgentHooks
# AC2 + AC5: builder.agent.md must have the correct Stop hook section
# ---------------------------------------------------------------------------


class TestFromAC_BuilderAgentHooks:
    """AC2 + AC5: builder.agent.md frontmatter must contain a Stop hook with type: command."""

    def test_builder_frontmatter_has_hooks_section(self) -> None:
        """AC2: builder.agent.md frontmatter must contain a 'hooks:' key."""
        fm = _extract_frontmatter(_BUILDER_AGENT)
        assert "hooks:" in fm, (
            "builder.agent.md frontmatter missing 'hooks:' section (AC2)"
        )

    def test_builder_stop_hook_event_name_is_pascal_case(self) -> None:
        """AC2: Stop event must be PascalCase 'Stop:' per VS Code hooks API (3/25/2026)."""
        fm = _extract_frontmatter(_BUILDER_AGENT)
        assert "Stop:" in fm, (
            "builder.agent.md must have 'Stop:' (PascalCase) hook event name"
        )

    def test_builder_stop_hook_type_is_command(self) -> None:
        """AC2: Stop hook must use 'type: command' (not prompt-injection model)."""
        fm = _extract_frontmatter(_BUILDER_AGENT)
        assert "type: command" in fm, (
            "builder.agent.md Stop hook must have 'type: command' entry"
        )

    def test_builder_stop_hook_has_windows_key(self) -> None:
        """AC2: Stop hook must have a 'windows:' execution key for the PowerShell command."""
        fm = _extract_frontmatter(_BUILDER_AGENT)
        assert "windows:" in fm, (
            "builder.agent.md Stop hook must have a 'windows:' key with the PS command"
        )

    def test_builder_stop_hook_windows_references_script(self) -> None:
        """AC2: windows command must reference stop-commit-guard.ps1."""
        fm = _extract_frontmatter(_BUILDER_AGENT)
        assert "stop-commit-guard.ps1" in fm, (
            "builder.agent.md windows command must reference scripts/hooks/stop-commit-guard.ps1"
        )


# ---------------------------------------------------------------------------
# TestFromAC_WriterAgentHooks
# AC3 + AC5: writer.agent.md must have an identical Stop hook section
# ---------------------------------------------------------------------------


class TestFromAC_WriterAgentHooks:
    """AC3 + AC5: writer.agent.md frontmatter must have an identical Stop hook section."""

    def test_writer_frontmatter_has_hooks_section(self) -> None:
        """AC3: writer.agent.md frontmatter must contain a 'hooks:' key."""
        fm = _extract_frontmatter(_WRITER_AGENT)
        assert "hooks:" in fm, (
            "writer.agent.md frontmatter missing 'hooks:' section (AC3)"
        )

    def test_writer_stop_hook_event_name_is_pascal_case(self) -> None:
        """AC3: Stop event must be PascalCase 'Stop:' per VS Code hooks API (3/25/2026)."""
        fm = _extract_frontmatter(_WRITER_AGENT)
        assert "Stop:" in fm, (
            "writer.agent.md must have 'Stop:' (PascalCase) hook event name"
        )

    def test_writer_stop_hook_type_is_command(self) -> None:
        """AC3: Stop hook must use 'type: command'."""
        fm = _extract_frontmatter(_WRITER_AGENT)
        assert "type: command" in fm, (
            "writer.agent.md Stop hook must have 'type: command' entry"
        )

    def test_writer_stop_hook_has_windows_key(self) -> None:
        """AC3: Stop hook must have a 'windows:' execution key."""
        fm = _extract_frontmatter(_WRITER_AGENT)
        assert "windows:" in fm, (
            "writer.agent.md Stop hook must have a 'windows:' key with the PS command"
        )

    def test_writer_stop_hook_windows_references_script(self) -> None:
        """AC3: windows command must reference the same shared stop-commit-guard.ps1."""
        fm = _extract_frontmatter(_WRITER_AGENT)
        assert "stop-commit-guard.ps1" in fm, (
            "writer.agent.md windows command must reference scripts/hooks/stop-commit-guard.ps1"
        )

    def test_writer_hooks_section_matches_builder(self) -> None:
        """AC3: writer's hooks section must be identical to builder's (DRY enforcement)."""
        builder_fm = _extract_frontmatter(_BUILDER_AGENT)
        writer_fm = _extract_frontmatter(_WRITER_AGENT)

        def _extract_hooks_block(fm: str) -> str:
            """Extract the hooks: block lines from a frontmatter string."""
            lines = fm.splitlines()
            hooks_lines: list[str] = []
            in_hooks = False
            for line in lines:
                if line.strip().startswith("hooks:"):
                    in_hooks = True
                elif in_hooks and line and not line[0].isspace():
                    break
                if in_hooks:
                    hooks_lines.append(line)
            return "\n".join(hooks_lines)

        builder_hooks = _extract_hooks_block(builder_fm)
        writer_hooks = _extract_hooks_block(writer_fm)
        assert builder_hooks, "builder.agent.md has no hooks block (AC2 must pass first)"
        assert writer_hooks == builder_hooks, (
            "writer.agent.md hooks section must be identical to builder.agent.md (AC3)"
        )


# ---------------------------------------------------------------------------
# TestFromAC_VscodeSettings
# AC4: .vscode/settings.json must have chat.useCustomAgentHooks: true
# ---------------------------------------------------------------------------


class TestFromAC_VscodeSettings:
    """AC4: .vscode/settings.json must contain chat.useCustomAgentHooks: true."""

    @pytest.fixture
    def vscode_settings(self) -> dict[str, Any]:
        """Load .vscode/settings.json as a dict."""
        return json.loads(_SETTINGS.read_text(encoding="utf-8"))  # type: ignore[no-any-return]

    def test_settings_has_custom_agent_hooks_key(
        self, vscode_settings: dict[str, Any]
    ) -> None:
        """AC4: settings.json must contain the chat.useCustomAgentHooks key."""
        assert "chat.useCustomAgentHooks" in vscode_settings, (
            "settings.json missing 'chat.useCustomAgentHooks' key (AC4)"
        )

    def test_settings_custom_agent_hooks_is_true(
        self, vscode_settings: dict[str, Any]
    ) -> None:
        """AC4: chat.useCustomAgentHooks must be set to true."""
        assert vscode_settings.get("chat.useCustomAgentHooks") is True, (
            f"Expected chat.useCustomAgentHooks=true, got: "
            f"{vscode_settings.get('chat.useCustomAgentHooks')!r}"
        )

    def test_settings_is_valid_json_with_agent_hooks_enabled(
        self, vscode_settings: dict[str, Any]
    ) -> None:
        """AC4: file is valid JSON (fixture parses it) and the key is true.

        The fixture performs the JSON parse; this test verifies the combined contract.
        """
        assert isinstance(vscode_settings, dict), "settings.json must parse as a JSON object"
        assert vscode_settings.get("chat.useCustomAgentHooks") is True, (
            "chat.useCustomAgentHooks must be true after the fix"
        )
