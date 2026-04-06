"""Tests for task #591: Add PreToolUse path guard hook to doc-writer agent (Phase 5).

Contract-level tests for:
1. .owlbear/hooks/deny-code-writes.ps1 — deny-list path guard (blocks source dirs)
2. share/agents/doc-writer.agent.md   — PreToolUse hook registration + tools list edit

Assumed PreToolUse stdin JSON format (VS Code hooks spec):
  {
    "tool_name": "<tool_name>",
    "tool_input": { ... }
  }

Path extraction fields (AC1):
  - tool_input.filePath                  (create_file, replace_string_in_file, apply_patch)
  - tool_input.dirPath                   (create_directory)
  - tool_input.replacements[*].filePath  (multi_replace_string_in_file)

Deny-list rule (AC1): extracted path must NOT start with a denied prefix (or equal
`conftest.py`) after normalizing \\ to / and stripping leading ./. If ANY extracted
path is denied, the whole tool call is denied.

Denied prefixes: serve/, v1/, tests/, setup/, seed/, store/, share/agents/, .git/,
                 .owlbear/hooks/, .owlbear/scripts/
Exact-deny:      conftest.py

AC coverage map:
  AC1-svc:    create_file serve/ path -> denied
  AC1-v1:     create_file v1/ path -> denied
  AC1-tests:  create_file tests/ path -> denied
  AC1-setup:  create_file setup/ path -> denied
  AC1-seed:   create_file seed/ path -> denied
  AC1-store:  create_file store/ path -> denied
  AC1-sa:     create_file share/agents/ path -> denied
  AC1-git:    create_file .git/ path -> denied
  AC1-hooks:  create_file .owlbear/hooks/ path -> denied
  AC1-scr:    create_file .owlbear/scripts/ path -> denied
  AC1-cf:     create_file conftest.py (exact) -> denied
  AC1-allow1: create_file README.md -> allowed
  AC1-allow2: create_file .github/copilot-instructions.md -> allowed
  AC1-allow3: create_file share/skills/foo.md -> allowed (not in deny-list)
  AC1-allow4: create_file .owlbear/research/foo.md -> allowed (.owlbear/ root ok)
  AC1-bslash: backslash path serve\\foo.py normalized to serve/foo.py -> denied
  AC1-dot:    ./serve/foo.py stripped to serve/foo.py -> denied
  AC1-dot-cf: ./conftest.py stripped to conftest.py -> denied (exact match)
  AC1-rsi:    replace_string_in_file with v1/ path -> denied
  AC1-mra:    multi_replace all-denied -> denied
  AC1-mrb:    multi_replace mix (one denied, one allowed) -> denied
  AC1-mrc:    multi_replace all-allowed -> allowed
  AC1-dir1:   create_directory tests/ dirPath -> denied
  AC1-dir2:   create_directory share/ dirPath -> allowed
  AC2a:       create_file in gate
  AC2b:       replace_string_in_file in gate
  AC2c:       multi_replace_string_in_file in gate
  AC2d:       create_directory in gate
  AC2e:       apply_patch IS gated (deny-code-writes differs from deny-src-writes)
  AC2f:       run_in_terminal -> {}
  AC2g:       read_file -> {}
  AC2h:       unknown tool -> {}
  AC3a:       doc-writer.agent.md frontmatter has hooks: section
  AC3b:       hooks: section contains PreToolUse entry
  AC3c:       PreToolUse hook specifies type: command
  AC3d:       PreToolUse command references deny-code-writes.ps1
  AC4:        tools list does not contain edit/editFiles
  AC5a:       malformed stdin JSON -> {}
  AC5b:       empty tool_name -> {}
  AC5c:       missing tool_name key -> {}
  AC5d:       write tool with no path fields in tool_input -> {}
  AC5e:       write tool with empty string filePath -> {}
  AC5f:       multi_replace with empty replacements array -> {}
  AC6a:       doc-writer.agent.md frontmatter parses as valid YAML with hooks
  AC6b:       frontmatter has no duplicate keys after edits
  AC7:        script contains maintenance comment header listing denied dirs
  Boundary1:  conftest.py.bak -> allowed (not exact 'conftest.py')
  Boundary2:  seedfile.py -> allowed ('seed' but not 'seed/')
  Boundary3:  share/agents sub-path blocked; share/skills/ allowed
  Boundary4:  deny response has hookSpecificOutput.permissionDecision=deny
  Boundary5:  deny response has non-empty permissionDecisionReason
  Boundary6:  stdout is always valid JSON
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).parent.parent
_SCRIPT_PATH = _REPO_ROOT / ".owlbear" / "hooks" / "deny-code-writes.ps1"
_AGENT_PATH = _REPO_ROOT / "share" / "agents" / "doc-writer.agent.md"

# Write tools that the hook must gate (AC2) -- apply_patch IS included here
# (differs from deny-src-writes.ps1 which excluded apply_patch)
_GATED_WRITE_TOOLS = [
    "create_file",
    "replace_string_in_file",
    "multi_replace_string_in_file",
    "create_directory",
    "apply_patch",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_hook(stdin_data: dict, *, timeout: int = 30) -> tuple[int, dict]:
    """Run deny-code-writes.ps1 with the given stdin JSON.

    Returns (exit_code, parsed_stdout_json).
    Raises FileNotFoundError if the script does not yet exist -- makes
    RED-phase failures explicit rather than silently returning {}.
    """
    if not _SCRIPT_PATH.exists():
        msg = (
            f"deny-code-writes.ps1 not found at {_SCRIPT_PATH}. "
            "Builder must create .owlbear/hooks/deny-code-writes.ps1 to make these tests pass."
        )
        raise FileNotFoundError(msg)

    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-File", str(_SCRIPT_PATH)],
        input=json.dumps(stdin_data),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    stdout = result.stdout.strip()
    try:
        output = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError:
        output = {"_raw": stdout}
    return result.returncode, output


def _is_denied(output: dict) -> bool:
    """Return True if the hook response contains a deny permissionDecision."""
    return (
        output.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"
    )


def _extract_frontmatter(content: str) -> str:
    """Return the YAML text between the first --- ... --- block."""
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    assert match is not None, (
        "No valid YAML frontmatter (--- ... ---) found in doc-writer.agent.md"
    )
    return match.group(1)


# ---------------------------------------------------------------------------
# Script existence -- fails RED until builder creates the file
# ---------------------------------------------------------------------------


class TestFromAC_ScriptExists:
    """Script must be created at the expected path with content (AC prerequisite)."""

    def test_deny_code_writes_ps1_exists(self) -> None:
        """deny-code-writes.ps1 must exist on disk."""
        assert _SCRIPT_PATH.exists(), (
            f"deny-code-writes.ps1 not found at {_SCRIPT_PATH}. "
            "Builder must create .owlbear/hooks/deny-code-writes.ps1."
        )

    def test_script_is_nonempty(self) -> None:
        """Script file must have content -- an empty file cannot implement the guard."""
        assert _SCRIPT_PATH.exists(), (
            f"deny-code-writes.ps1 not found at {_SCRIPT_PATH}."
        )
        assert _SCRIPT_PATH.stat().st_size > 0, (
            "deny-code-writes.ps1 exists but is empty -- builder must implement it."
        )


# ---------------------------------------------------------------------------
# Deny-list path guard -- Windows/PowerShell required
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell hook requires Windows")
class TestFromAC_DenyListBehavior:
    """Behavioural tests via subprocess. All fail RED because script does not exist yet."""

    # --- AC1-svc: serve/ ---

    def test_create_file_serve_path_is_denied(self) -> None:
        """AC1-svc: create_file with a serve/ path must be denied."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "serve/mcp-kanban/server.py"},
        })
        assert _is_denied(output), (
            f"create_file with serve/ path must be denied (deny-list), got: {output!r}"
        )

    # --- AC1-v1: v1/ ---

    def test_create_file_v1_path_is_denied(self) -> None:
        """AC1-v1: create_file with a v1/ path must be denied."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "v1/coverage_task60.txt"},
        })
        assert _is_denied(output), (
            f"create_file with v1/ path must be denied (deny-list), got: {output!r}"
        )

    # --- AC1-tests: tests/ ---

    def test_create_file_tests_path_is_denied(self) -> None:
        """AC1-tests: create_file with a tests/ path must be denied."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "tests/test_evil.py"},
        })
        assert _is_denied(output), (
            f"create_file with tests/ path must be denied (deny-list), got: {output!r}"
        )

    # --- AC1-setup: setup/ ---

    def test_create_file_setup_path_is_denied(self) -> None:
        """AC1-setup: create_file with a setup/ path must be denied."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "setup/init.py"},
        })
        assert _is_denied(output), (
            f"create_file with setup/ path must be denied (deny-list), got: {output!r}"
        )

    # --- AC1-seed: seed/ ---

    def test_create_file_seed_path_is_denied(self) -> None:
        """AC1-seed: create_file with a seed/ path must be denied."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "seed/owlbear-project.json"},
        })
        assert _is_denied(output), (
            f"create_file with seed/ path must be denied (deny-list), got: {output!r}"
        )

    # --- AC1-store: store/ ---

    def test_create_file_store_path_is_denied(self) -> None:
        """AC1-store: create_file with a store/ path must be denied."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "store/knowledge/doc.md"},
        })
        assert _is_denied(output), (
            f"create_file with store/ path must be denied (deny-list), got: {output!r}"
        )

    # --- AC1-sa: share/agents/ ---

    def test_create_file_share_agents_path_is_denied(self) -> None:
        """AC1-sa: create_file with share/agents/ path must be denied (self-modification guard)."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "share/agents/doc-writer.agent.md"},
        })
        assert _is_denied(output), (
            f"create_file with share/agents/ path must be denied (self-modification), got: {output!r}"
        )

    # --- AC1-git: .git/ ---

    def test_create_file_git_path_is_denied(self) -> None:
        """AC1-git: create_file with .git/ path must be denied (privilege escalation vector)."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": ".git/hooks/pre-commit"},
        })
        assert _is_denied(output), (
            f"create_file with .git/ path must be denied (privilege escalation), got: {output!r}"
        )

    # --- AC1-hooks: .owlbear/hooks/ ---

    def test_create_file_owlbear_hooks_path_is_denied(self) -> None:
        """AC1-hooks: create_file with .owlbear/hooks/ path must be denied."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": ".owlbear/hooks/deny-code-writes.ps1"},
        })
        assert _is_denied(output), (
            f"create_file with .owlbear/hooks/ path must be denied, got: {output!r}"
        )

    # --- AC1-scr: .owlbear/scripts/ ---

    def test_create_file_owlbear_scripts_path_is_denied(self) -> None:
        """AC1-scr: create_file with .owlbear/scripts/ path must be denied."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": ".owlbear/scripts/run.ps1"},
        })
        assert _is_denied(output), (
            f"create_file with .owlbear/scripts/ path must be denied, got: {output!r}"
        )

    # --- AC1-cf: conftest.py exact match ---

    def test_create_file_conftest_py_exact_is_denied(self) -> None:
        """AC1-cf: create_file with exact path conftest.py must be denied."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "conftest.py"},
        })
        assert _is_denied(output), (
            f"create_file with exact path 'conftest.py' must be denied, got: {output!r}"
        )

    # --- AC1-allow: allowed paths ---

    def test_create_file_readme_is_allowed(self) -> None:
        """AC1-allow1: create_file with README.md must return {} (not in deny-list)."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "README.md"},
        })
        assert output == {}, (
            f"create_file with README.md must be allowed (not in deny-list), got: {output!r}"
        )

    def test_create_file_github_copilot_instructions_is_allowed(self) -> None:
        """AC1-allow2: create_file with .github/copilot-instructions.md must return {}."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": ".github/copilot-instructions.md"},
        })
        assert output == {}, (
            f"create_file with .github/copilot-instructions.md must be allowed, got: {output!r}"
        )

    def test_create_file_share_skills_is_allowed(self) -> None:
        """AC1-allow3: create_file with share/skills/ path must return {} (not in deny-list)."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "share/skills/h-frontend-design/SKILL.md"},
        })
        assert output == {}, (
            f"create_file with share/skills/ path must be allowed, got: {output!r}"
        )

    def test_create_file_owlbear_research_is_allowed(self) -> None:
        """AC1-allow4: create_file with .owlbear/research/ path must return {} (not blocked)."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": ".owlbear/research/analysis-591.md"},
        })
        assert output == {}, (
            f"create_file with .owlbear/research/ path must be allowed, got: {output!r}"
        )

    # --- AC1-bslash: backslash normalization ---

    def test_backslash_serve_path_is_denied(self) -> None:
        """AC1-bslash: backslash path serve\\mcp\\server.py normalized to serve/ -> denied."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "serve\\mcp-kanban\\server.py"},
        })
        assert _is_denied(output), (
            f"Backslash serve\\ path must be denied after normalization, got: {output!r}"
        )

    def test_backslash_share_skills_is_allowed(self) -> None:
        """AC1-bslash boundary: backslash non-denied path normalized and allowed."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "share\\skills\\foo.md"},
        })
        assert output == {}, (
            f"Backslash share\\skills\\ path should be normalized and allowed, got: {output!r}"
        )

    # --- AC1-dot: ./ prefix stripping ---

    def test_dot_slash_serve_path_is_denied(self) -> None:
        """AC1-dot: ./serve/foo.py stripped to serve/foo.py -> denied."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "./serve/mcp-kanban/server.py"},
        })
        assert _is_denied(output), (
            f"./serve/ path must be denied after ./ stripping, got: {output!r}"
        )

    def test_dot_slash_conftest_is_denied(self) -> None:
        """AC1-dot-cf: ./conftest.py stripped to conftest.py -> denied (exact match)."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "./conftest.py"},
        })
        assert _is_denied(output), (
            f"./conftest.py must be denied after ./ stripping (exact match), got: {output!r}"
        )

    # --- AC1-rsi: replace_string_in_file routing ---

    def test_replace_string_in_file_v1_path_is_denied(self) -> None:
        """AC1-rsi: replace_string_in_file with v1/ filePath must be denied."""
        _, output = _run_hook({
            "tool_name": "replace_string_in_file",
            "tool_input": {"filePath": "v1/module.py", "oldString": "x", "newString": "y"},
        })
        assert _is_denied(output), (
            f"replace_string_in_file with v1/ path must be denied, got: {output!r}"
        )

    def test_replace_string_in_file_allowed_path_returns_empty(self) -> None:
        """AC1-rsi boundary: replace_string_in_file with allowed path returns {}."""
        _, output = _run_hook({
            "tool_name": "replace_string_in_file",
            "tool_input": {"filePath": "share/skills/SKILL.md", "oldString": "x", "newString": "y"},
        })
        assert output == {}, (
            f"replace_string_in_file with non-denied path must return {{}}, got: {output!r}"
        )

    # --- AC1-mra/AC1-mrb/AC1-mrc: multi_replace_string_in_file ---

    def test_multi_replace_all_denied_paths_is_denied(self) -> None:
        """AC1-mra: multi_replace with all denied paths must be denied."""
        _, output = _run_hook({
            "tool_name": "multi_replace_string_in_file",
            "tool_input": {
                "replacements": [
                    {"filePath": "serve/mcp-kanban/server.py", "oldString": "a", "newString": "b"},
                    {"filePath": "v1/module.py", "oldString": "c", "newString": "d"},
                ],
            },
        })
        assert _is_denied(output), (
            f"multi_replace with all denied paths must be denied, got: {output!r}"
        )

    def test_multi_replace_mixed_paths_is_denied(self) -> None:
        """AC1-mrb: any replacement targeting a denied path must deny the whole call."""
        _, output = _run_hook({
            "tool_name": "multi_replace_string_in_file",
            "tool_input": {
                "replacements": [
                    {"filePath": "share/skills/SKILL.md", "oldString": "a", "newString": "b"},
                    {"filePath": "serve/mcp-kanban/server.py", "oldString": "c", "newString": "d"},
                ],
            },
        })
        assert _is_denied(output), (
            f"multi_replace with any denied path must deny the whole call, got: {output!r}"
        )

    def test_multi_replace_all_allowed_paths_returns_empty(self) -> None:
        """AC1-mrc: multi_replace with all allowed paths must return {}."""
        _, output = _run_hook({
            "tool_name": "multi_replace_string_in_file",
            "tool_input": {
                "replacements": [
                    {"filePath": "share/skills/SKILL.md", "oldString": "a", "newString": "b"},
                    {"filePath": "README.md", "oldString": "c", "newString": "d"},
                ],
            },
        })
        assert output == {}, (
            f"multi_replace with all allowed paths must return {{}}, got: {output!r}"
        )

    # --- AC1-dir: create_directory dirPath routing ---

    def test_create_directory_tests_dirpath_is_denied(self) -> None:
        """AC1-dir1: create_directory with tests/ dirPath must be denied."""
        _, output = _run_hook({
            "tool_name": "create_directory",
            "tool_input": {"dirPath": "tests/new_subdir"},
        })
        assert _is_denied(output), (
            f"create_directory with tests/ dirPath must be denied, got: {output!r}"
        )

    def test_create_directory_allowed_dirpath_returns_empty(self) -> None:
        """AC1-dir2: create_directory with non-denied dirPath must return {}."""
        _, output = _run_hook({
            "tool_name": "create_directory",
            "tool_input": {"dirPath": "share/skills/new-skill"},
        })
        assert output == {}, (
            f"create_directory with non-denied dirPath must return {{}}, got: {output!r}"
        )

    # --- Boundary1: conftest.py.bak is not exact match ---

    def test_conftest_py_bak_is_allowed(self) -> None:
        """Boundary1: 'conftest.py.bak' is not exact 'conftest.py' -> allowed."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "conftest.py.bak"},
        })
        assert output == {}, (
            f"'conftest.py.bak' must be allowed (not exact match for 'conftest.py'), got: {output!r}"
        )

    # --- Boundary2: seed without trailing slash is allowed ---

    def test_seedfile_py_not_seed_dir_is_allowed(self) -> None:
        """Boundary2: 'seedfile.py' starts with 'seed' but not 'seed/' -> allowed."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "seedfile.py"},
        })
        assert output == {}, (
            f"'seedfile.py' must be allowed ('seed' but not 'seed/'), got: {output!r}"
        )

    # --- Boundary3: share/skills/ allowed but share/agents/ denied ---

    def test_share_skills_is_allowed_but_share_agents_is_denied(self) -> None:
        """Boundary3: share/agents/ denied; share/skills/ allowed -- prefix granularity."""
        _, denied_output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "share/agents/new-agent.agent.md"},
        })
        assert _is_denied(denied_output), (
            f"share/agents/ must be denied (self-modification), got: {denied_output!r}"
        )
        _, allowed_output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "share/skills/new-skill/SKILL.md"},
        })
        assert allowed_output == {}, (
            f"share/skills/ must be allowed (not in deny-list), got: {allowed_output!r}"
        )

    # --- Deny response structure (Boundary4/Boundary5) ---

    def test_deny_response_has_hook_specific_output_key(self) -> None:
        """Boundary4: deny response must nest under hookSpecificOutput."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "serve/mcp-kanban/server.py"},
        })
        assert "hookSpecificOutput" in output, (
            f"Deny response must contain 'hookSpecificOutput' key, got: {output!r}"
        )

    def test_deny_response_permission_decision_is_deny(self) -> None:
        """Boundary4: hookSpecificOutput.permissionDecision must equal 'deny'."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "serve/mcp-kanban/server.py"},
        })
        decision = output.get("hookSpecificOutput", {}).get("permissionDecision")
        assert decision == "deny", (
            f"permissionDecision must equal 'deny', got: {decision!r} in {output!r}"
        )

    def test_deny_reason_is_nonempty(self) -> None:
        """Boundary5: permissionDecisionReason must be a non-empty string when denying."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "serve/mcp-kanban/server.py"},
        })
        reason = output.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
        assert reason, (
            f"permissionDecisionReason must be non-empty when denying a write, got: {output!r}"
        )

    # --- Boundary6: stdout is always valid JSON ---

    def test_stdout_is_valid_json_for_allowed_call(self) -> None:
        """Boundary6: stdout must always be valid JSON -- allowed calls return {}."""
        if not _SCRIPT_PATH.exists():
            raise FileNotFoundError(
                f"deny-code-writes.ps1 not found at {_SCRIPT_PATH}."
            )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-File", str(_SCRIPT_PATH)],
            input=json.dumps({"tool_name": "create_file", "tool_input": {"filePath": "README.md"}}),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        stdout = result.stdout.strip()
        try:
            parsed = json.loads(stdout) if stdout else {}
        except json.JSONDecodeError as exc:
            pytest.fail(
                f"Script stdout is not valid JSON for allowed call: {stdout!r}\nError: {exc}"
            )
        assert isinstance(parsed, dict), f"Output must be a JSON object, got: {parsed!r}"

    def test_stdout_is_valid_json_for_denied_call(self) -> None:
        """Boundary6: stdout must always be valid JSON -- denied calls return deny object."""
        if not _SCRIPT_PATH.exists():
            raise FileNotFoundError(
                f"deny-code-writes.ps1 not found at {_SCRIPT_PATH}."
            )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-File", str(_SCRIPT_PATH)],
            input=json.dumps({"tool_name": "create_file", "tool_input": {"filePath": "serve/bad.py"}}),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        stdout = result.stdout.strip()
        try:
            parsed = json.loads(stdout) if stdout else {}
        except json.JSONDecodeError as exc:
            pytest.fail(
                f"Script stdout is not valid JSON for denied call: {stdout!r}\nError: {exc}"
            )
        assert isinstance(parsed, dict), f"Output must be a JSON object, got: {parsed!r}"


# ---------------------------------------------------------------------------
# Write-tool gate (AC2) -- Windows/PowerShell required
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell hook requires Windows")
class TestFromAC_WriteToolGate:
    """Only the gated write tools trigger path checks; all others pass through."""

    # --- AC2a-d: gated tools each deny denied paths ---

    def test_create_file_is_gated(self) -> None:
        """AC2a: create_file with denied path must be denied."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "serve/module.py"},
        })
        assert _is_denied(output), (
            f"create_file must be in the write-tool gate, got: {output!r}"
        )

    def test_replace_string_in_file_is_gated(self) -> None:
        """AC2b: replace_string_in_file with denied path must be denied."""
        _, output = _run_hook({
            "tool_name": "replace_string_in_file",
            "tool_input": {"filePath": "v1/module.py", "oldString": "a", "newString": "b"},
        })
        assert _is_denied(output), (
            f"replace_string_in_file must be in the write-tool gate, got: {output!r}"
        )

    def test_multi_replace_string_in_file_is_gated(self) -> None:
        """AC2c: multi_replace_string_in_file with denied paths must be denied."""
        _, output = _run_hook({
            "tool_name": "multi_replace_string_in_file",
            "tool_input": {"replacements": [
                {"filePath": "tests/test_foo.py", "oldString": "a", "newString": "b"},
            ]},
        })
        assert _is_denied(output), (
            f"multi_replace_string_in_file must be in the write-tool gate, got: {output!r}"
        )

    def test_create_directory_is_gated(self) -> None:
        """AC2d: create_directory with denied dirPath must be denied."""
        _, output = _run_hook({
            "tool_name": "create_directory",
            "tool_input": {"dirPath": "seed/new-dir"},
        })
        assert _is_denied(output), (
            f"create_directory must be in the write-tool gate, got: {output!r}"
        )

    def test_apply_patch_is_gated(self) -> None:
        """AC2e: apply_patch IS gated in deny-code-writes (unlike deny-src-writes)."""
        _, output = _run_hook({
            "tool_name": "apply_patch",
            "tool_input": {"filePath": "serve/mcp-kanban/server.py"},
        })
        assert _is_denied(output), (
            f"apply_patch must be gated in deny-code-writes.ps1 (differs from 589), got: {output!r}"
        )

    # --- AC2f-h: non-write tool pass-through ---

    def test_run_in_terminal_returns_empty_json(self) -> None:
        """AC2f: run_in_terminal bypasses PreToolUse hooks -- must return {}."""
        _, output = _run_hook({"tool_name": "run_in_terminal", "tool_input": {}})
        assert output == {}, (
            f"run_in_terminal must pass through (not gated), got: {output!r}"
        )

    def test_read_file_returns_empty_json(self) -> None:
        """AC2g: read_file is not a write tool -- must return {}."""
        _, output = _run_hook({"tool_name": "read_file", "tool_input": {}})
        assert output == {}, (
            f"read_file must pass through (not gated), got: {output!r}"
        )

    def test_unknown_tool_name_returns_empty_json(self) -> None:
        """AC2h: unknown/future tool_name values must pass through -- return {}."""
        _, output = _run_hook({"tool_name": "some_future_tool", "tool_input": {}})
        assert output == {}, (
            f"Unknown tool must pass through, got: {output!r}"
        )


# ---------------------------------------------------------------------------
# Safety fallbacks for malformed/empty input (AC5) -- Windows/PowerShell required
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell hook requires Windows")
class TestFromAC_SafetyFallbacks:
    """Script must not crash or deny on malformed/incomplete stdin."""

    def test_malformed_stdin_json_returns_empty_json(self) -> None:
        """AC5a: malformed stdin must not crash the script -- returns {}."""
        if not _SCRIPT_PATH.exists():
            raise FileNotFoundError(
                f"deny-code-writes.ps1 not found at {_SCRIPT_PATH}."
            )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-File", str(_SCRIPT_PATH)],
            input="not-valid-json{{{",
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        stdout = result.stdout.strip()
        try:
            output = json.loads(stdout) if stdout else {}
        except json.JSONDecodeError:
            output = {"_raw": stdout}
        assert output == {}, (
            f"Malformed JSON input must produce {{}} output, got: {output!r}"
        )

    def test_empty_tool_name_returns_empty_json(self) -> None:
        """AC5b: empty string tool_name is not gated -- must return {}."""
        _, output = _run_hook({"tool_name": "", "tool_input": {}})
        assert output == {}, (
            f"Empty tool_name must return {{}}, got: {output!r}"
        )

    def test_missing_tool_name_key_returns_empty_json(self) -> None:
        """AC5c: stdin JSON with no tool_name key -- must not crash, returns {}."""
        _, output = _run_hook({"tool_input": {}})
        assert output == {}, (
            f"Missing tool_name key must return {{}}, got: {output!r}"
        )

    def test_write_tool_with_no_paths_returns_empty_json(self) -> None:
        """AC5d: write tool with no path fields in tool_input -> {} (nothing to deny)."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"content": "hello"},
        })
        assert output == {}, (
            f"create_file with no filePath must return {{}} (nothing to deny), got: {output!r}"
        )

    def test_write_tool_with_empty_string_filepath_returns_empty_json(self) -> None:
        """AC5e: write tool with filePath='' -- empty path -> {} (pass-through)."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": ""},
        })
        assert output == {}, (
            f"create_file with empty filePath must return {{}} (pass-through), got: {output!r}"
        )

    def test_multi_replace_empty_replacements_returns_empty_json(self) -> None:
        """AC5f: multi_replace with empty replacements array -> no paths -> {}."""
        _, output = _run_hook({
            "tool_name": "multi_replace_string_in_file",
            "tool_input": {"replacements": []},
        })
        assert output == {}, (
            f"multi_replace with empty replacements must return {{}} (no paths to check), got: {output!r}"
        )


# ---------------------------------------------------------------------------
# doc-writer.agent.md frontmatter changes -- AC3, AC4, AC6
# ---------------------------------------------------------------------------


class TestFromAC_DocWriterAgentHooks:
    """doc-writer.agent.md must gain a deny-code-writes PreToolUse hook and lose edit/editFiles."""

    def _content(self) -> str:
        assert _AGENT_PATH.exists(), f"Agent file not found at {_AGENT_PATH}"
        return _AGENT_PATH.read_text(encoding="utf-8")

    def _frontmatter(self) -> str:
        return _extract_frontmatter(self._content())

    # --- AC3: hooks section ---

    def test_frontmatter_has_hooks_section(self) -> None:
        """AC3a: doc-writer.agent.md frontmatter must contain a hooks: key."""
        fm = self._frontmatter()
        assert re.search(r"^hooks:", fm, re.MULTILINE), (
            "doc-writer.agent.md frontmatter is missing the 'hooks:' key. "
            "Builder must add a PreToolUse hooks section."
        )

    def test_frontmatter_has_pretooluse_entry(self) -> None:
        """AC3b: hooks: section must contain a PreToolUse entry."""
        fm = self._frontmatter()
        assert "PreToolUse" in fm, (
            "doc-writer.agent.md hooks: section is missing a PreToolUse entry."
        )

    def test_pretooluse_hook_type_is_command(self) -> None:
        """AC3c: PreToolUse hook must specify type: command."""
        fm = self._frontmatter()
        assert re.search(r"type:\s*command", fm), (
            "doc-writer.agent.md PreToolUse hook must specify 'type: command'."
        )

    def test_pretooluse_hook_command_references_deny_code_writes(self) -> None:
        """AC3d: PreToolUse hook command must reference deny-code-writes.ps1."""
        fm = self._frontmatter()
        assert "deny-code-writes.ps1" in fm, (
            "doc-writer.agent.md PreToolUse hook command must point to deny-code-writes.ps1."
        )

    # --- AC4: edit/editFiles removed ---

    def test_tools_list_does_not_contain_edit_slash_edit_files(self) -> None:
        """AC4: edit/editFiles must be removed from doc-writer tools list."""
        fm = self._frontmatter()
        assert "edit/editFiles" not in fm, (
            "doc-writer.agent.md tools list must not contain 'edit/editFiles'. "
            "Builder must remove it to prevent bypass of the path guard."
        )

    # --- AC6: valid YAML frontmatter with no duplicate keys ---

    def test_frontmatter_is_parseable_yaml_with_pretooluse_hook(self) -> None:
        """AC6a: frontmatter must parse as valid YAML and contain hooks after builder changes."""
        import yaml  # noqa: PLC0415

        fm = self._frontmatter()
        try:
            parsed = yaml.safe_load(fm)
        except yaml.YAMLError as exc:
            pytest.fail(
                f"doc-writer.agent.md frontmatter is not valid YAML: {exc}"
            )
        assert isinstance(parsed, dict), (
            f"Parsed YAML frontmatter must be a dict, got: {type(parsed)}"
        )
        assert "hooks" in parsed, (
            "Frontmatter parsed but missing 'hooks:' key -- "
            "builder must add the PreToolUse hooks section."
        )
        hooks = parsed["hooks"]
        assert "PreToolUse" in hooks, (
            f"hooks section must contain PreToolUse key, got: {hooks!r}"
        )

    def test_frontmatter_no_duplicate_keys(self) -> None:
        """AC6b: frontmatter must not gain duplicate YAML keys after edits."""
        fm = self._frontmatter()
        assert "hooks:" in fm, (
            "Builder must add the hooks: section -- no duplicate-key check is meaningful "
            "before the hook is added."
        )
        top_level_keys = re.findall(r"^([a-zA-Z][a-zA-Z0-9_-]*):", fm, re.MULTILINE)
        seen: set[str] = set()
        duplicates: list[str] = []
        for key in top_level_keys:
            if key in seen:
                duplicates.append(key)
            seen.add(key)
        assert not duplicates, (
            f"Duplicate YAML keys found in doc-writer.agent.md frontmatter: {duplicates}"
        )


# ---------------------------------------------------------------------------
# Maintenance comment header (AC7)
# ---------------------------------------------------------------------------


class TestFromAC_MaintenanceHeader:
    """Script must contain a maintenance comment header listing denied dirs (AC7)."""

    def test_script_contains_comment_header(self) -> None:
        """AC7: deny-code-writes.ps1 must contain a comment header section."""
        assert _SCRIPT_PATH.exists(), (
            f"deny-code-writes.ps1 not found at {_SCRIPT_PATH}."
        )
        content = _SCRIPT_PATH.read_text(encoding="utf-8")
        # PowerShell comment blocks start with # or <# ... #>
        assert re.search(r"(#|<#)", content), (
            "deny-code-writes.ps1 must contain a comment header -- "
            "builder must add maintenance comments listing the deny-list."
        )

    def test_script_header_mentions_denied_dirs(self) -> None:
        """AC7: maintenance comment must enumerate the denied directories."""
        assert _SCRIPT_PATH.exists(), (
            f"deny-code-writes.ps1 not found at {_SCRIPT_PATH}."
        )
        content = _SCRIPT_PATH.read_text(encoding="utf-8")
        # At least some of the key denied dirs must appear in comments
        denied_mentioned = any(
            d in content for d in ["serve/", "share/agents/", ".git/", "deny-list"]
        )
        assert denied_mentioned, (
            "deny-code-writes.ps1 maintenance comment must mention denied dirs "
            "(e.g., 'serve/', 'share/agents/', '.git/', or 'deny-list'). "
            "Builder must add a comment header."
        )
