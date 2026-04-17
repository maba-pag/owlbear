"""Tests for task #891: PreToolUse guard hooks equivalence (5 Python hooks).

Contract-level tests for the Python port of 5 PreToolUse guard hooks.
Tests invoke .owlbear/hooks/{name}.py via subprocess to verify the full I/O
contract: stdin JSON → stdout JSON, exit 0, fail-open on malformed input.

Hooks under test:
  - deny-writes.py             — tool-name guard (read-only agents)
  - deny-code-writes.py        — deny-list path guard (doc-writer)
  - deny-src-writes.py         — allow-list path guard (test-writer, tests/ only)
  - deny-scratch-only-writes.py — allow-list path guard (quality-runner, .owlbear/scratch/ only)
  - allow-stances-only.py      — allow-list path guard (ideation panelists, /stances/ only)

Shared I/O contract (all 5 hooks):
  stdin:    {"tool_name": "<name>", "tool_input": {...}}
  allow:    {} with exit 0
  deny:     {"hookSpecificOutput": {"permissionDecision": "deny",
             "permissionDecisionReason": "<reason>"}} with exit 0
  fail-open: malformed/empty/binary stdin → {} with exit 0

Write tools gated by all 5 hooks:
  create_file, replace_string_in_file, multi_replace_string_in_file,
  apply_patch, create_directory, editFiles

Path extraction fields (path-checking hooks only):
  tool_input.filePath                  — create_file, replace_string_in_file, apply_patch
  tool_input.dirPath                   — create_directory
  tool_input.replacements[*].filePath  — multi_replace_string_in_file
  tool_input.files[*]                  — editFiles (string elements or {filePath:…} objects)

AC coverage map:
  AC-existence-{hook}:     each of 5 .py scripts exists at .owlbear/hooks/{name}.py
  AC-existence-nonempty:   each script is non-empty
  AC-deny-writes-{tool}:   each of 6 write tools → denied
  AC-deny-writes-allow:    non-write tools → allowed
  AC-deny-writes-missing:  missing/empty tool_name → allowed (fail-open)
  AC-deny-writes-response: hookSpecificOutput structure correct
  AC-dcw-deny-{prefix}:    each of 10 deny-list prefixes + conftest.py exact → denied
  AC-dcw-allow-{path}:     README.md, .github/, share/skills/, .owlbear/research/ → allowed
  AC-dcw-dirPath:          create_directory with denied dirPath → denied
  AC-dcw-replacements:     multi_replace with denied replacements[].filePath → denied
  AC-dcw-editFiles:        editFiles with denied files[] → denied
  AC-dcw-mixed:            one denied + one allowed in replacements → denied
  AC-dcw-all-allowed:      all replacements in allowed paths → allowed
  AC-dcw-backslash:        serve\\foo.py normalized → denied
  AC-dcw-dot-strip:        ./serve/foo.py stripped → denied
  AC-dcw-dot-conftest:     ./conftest.py stripped to exact match → denied
  AC-dcw-no-paths:         write tool with no paths → allowed (fail-open)
  AC-dcw-nonwrite:         non-write tool → allowed
  AC-dcw-boundary-cfbak:   conftest.py.bak → allowed (not exact conftest.py)
  AC-dcw-boundary-seed:    seedfile.py → allowed (not seed/)
  AC-dcw-boundary-skills:  share/skills/ allowed, share/agents/ denied
  AC-dsw-allow:            tests/ paths → allowed (create_file, multi_replace, create_directory)
  AC-dsw-deny:             non-tests/ paths → denied
  AC-dsw-backslash:        tests\\foo.py → allowed
  AC-dsw-editFiles-allow:  editFiles with tests/ → allowed
  AC-dsw-editFiles-deny:   editFiles with serve/ → denied
  AC-dsw-mixed:            one non-tests/ in replacements → denied
  AC-dsw-no-paths:         write tool no paths → allowed
  AC-dsw-boundary-prefix:  testsite.py (no slash) → denied
  AC-dsw-apply-patch:      apply_patch gated
  AC-dsow-allow:           .owlbear/scratch/ paths → allowed
  AC-dsow-deny:            non-scratch paths → denied
  AC-dsow-backslash:       .owlbear\\scratch\\x → allowed
  AC-dsow-hooks-denied:    .owlbear/hooks/ → denied (not scratch)
  AC-dsow-editFiles:       editFiles with scratch path → allowed
  AC-dsow-no-paths:        write tool no paths → allowed
  AC-dsow-boundary-pad:    .owlbear/scratchpad/ → denied (not scratch/)
  AC-dsow-mixed:           one non-scratch in editFiles → denied
  AC-aso-allow:            stances/arch.md → allowed
  AC-aso-deny:             non-stances paths → denied
  AC-aso-dot-strip:        ./stances/arch.md → allowed
  AC-aso-backslash:        stances\\arch.md → allowed
  AC-aso-nested:           foo/stances/bar.md → allowed
  AC-aso-no-paths:         write tool no paths → allowed
  AC-aso-editFiles-allow:  editFiles with stances/ → allowed
  AC-aso-editFiles-deny:   editFiles with non-stances → denied
  AC-aso-replacements:     multi_replace with stances/ paths → allowed
  AC-malformed-truncated:  truncated JSON → {} exit 0 (all 5 hooks)
  AC-malformed-empty:      empty stdin → {} exit 0 (all 5 hooks)
  AC-malformed-bom:        BOM-prefixed input → {} exit 0 (all 5 hooks)
  AC-malformed-binary:     binary data → {} exit 0 (all 5 hooks)
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

_REPO_ROOT = Path(__file__).parent.parent
_HOOKS_DIR = _REPO_ROOT / ".owlbear" / "hooks"

_ALL_HOOK_NAMES = [
    "deny-writes",
    "deny-code-writes",
    "deny-src-writes",
    "deny-scratch-only-writes",
    "allow-stances-only",
]

# All 6 write tools gated by every hook (from PS1 sources + VS Code docs)
_GATED_WRITE_TOOLS = [
    "create_file",
    "replace_string_in_file",
    "multi_replace_string_in_file",
    "apply_patch",
    "create_directory",
    "editFiles",
]

# deny-code-writes deny-list (prefixes + one exact-match)
_DCW_DENIED_PREFIX_PATHS = [
    "serve/mcp-kanban/server.py",
    "v1/legacy/module.py",
    "tests/test_example.py",
    "setup/init.py",
    "seed/scratch-pad.txt",
    "store/knowledge/index.json",
    "share/agents/doc-writer.agent.md",
    ".git/config",
    ".owlbear/hooks/deny-writes.py",
    ".owlbear/scripts/pre-commit.sh",
    "conftest.py",  # exact match
]

_DCW_ALLOWED_PATHS = [
    "README.md",
    ".github/copilot-instructions.md",
    "share/skills/h-some-skill/SKILL.md",
    ".owlbear/research/123-findings.md",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_hook(
    hook_name: str,
    stdin_data: dict | str | bytes,
    *,
    timeout: int = 30,
) -> tuple[int, dict]:
    """Invoke .owlbear/hooks/{hook_name}.py via sys.executable.

    Returns (exit_code, parsed_stdout_json).
    Raises FileNotFoundError if the script does not yet exist — makes
    RED-phase failures explicit rather than silently returning {}.
    """
    script = _HOOKS_DIR / f"{hook_name}.py"
    if not script.exists():
        msg = (
            f"{hook_name}.py not found at {script}. "
            "Builder must create the Python port to make these tests pass."
        )
        raise FileNotFoundError(msg)

    if isinstance(stdin_data, dict):
        input_bytes = json.dumps(stdin_data).encode("utf-8")
    elif isinstance(stdin_data, str):
        input_bytes = stdin_data.encode("utf-8")
    else:
        input_bytes = stdin_data  # already bytes (binary/BOM tests)

    result = subprocess.run(
        [sys.executable, str(script)],
        input=input_bytes,
        capture_output=True,
        timeout=timeout,
        cwd=str(_REPO_ROOT),
    )
    stdout_text = result.stdout.decode("utf-8", errors="replace").strip()
    try:
        output = json.loads(stdout_text) if stdout_text else {}
    except json.JSONDecodeError:
        output = {"_raw": stdout_text}
    return result.returncode, output


def _is_denied(output: dict) -> bool:
    """Return True if the hook output contains a deny permissionDecision."""
    return output.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


# ---------------------------------------------------------------------------
# Script existence — all 5 .py files must be created before behavior passes
# ---------------------------------------------------------------------------


class TestFromAC_ScriptExistence:
    """All 5 Python hook scripts must exist and be non-empty (AC prerequisite)."""

    @pytest.mark.parametrize("hook_name", _ALL_HOOK_NAMES)
    def test_py_hook_exists(self, hook_name: str) -> None:
        """AC-existence-{hook}: each hook script must exist at .owlbear/hooks/{name}.py."""
        script = _HOOKS_DIR / f"{hook_name}.py"
        assert script.exists(), (
            f"{hook_name}.py not found at {script}. "
            "Builder must create the Python port of this PreToolUse guard hook."
        )

    @pytest.mark.parametrize("hook_name", _ALL_HOOK_NAMES)
    def test_py_hook_nonempty(self, hook_name: str) -> None:
        """AC-existence-nonempty: each hook script must have content."""
        script = _HOOKS_DIR / f"{hook_name}.py"
        assert script.exists(), f"{hook_name}.py not found at {script}."
        assert script.stat().st_size > 0, (
            f"{hook_name}.py exists but is empty — builder must implement it."
        )


# ---------------------------------------------------------------------------
# deny-writes — tool-name guard (no path extraction)
# ---------------------------------------------------------------------------


class TestFromAC_DenyWrites:
    """deny-writes.py: deny write tools by tool_name; pass through all others."""

    @pytest.mark.parametrize("tool", _GATED_WRITE_TOOLS)
    def test_each_write_tool_is_denied(self, tool: str) -> None:
        """AC-deny-writes-{tool}: each of the 6 write tools must be denied."""
        _, output = _run_hook("deny-writes", {"tool_name": tool, "tool_input": {}})
        assert _is_denied(output), (
            f"deny-writes must deny '{tool}' but got: {output!r}"
        )

    def test_read_file_is_allowed(self) -> None:
        """AC-deny-writes-allow: read_file (non-write tool) must return {} (allowed)."""
        _, output = _run_hook("deny-writes", {"tool_name": "read_file", "tool_input": {}})
        assert output == {}, f"deny-writes must allow 'read_file', got: {output!r}"

    def test_run_in_terminal_is_allowed(self) -> None:
        """AC-deny-writes-allow: run_in_terminal must return {} (allowed)."""
        _, output = _run_hook("deny-writes", {"tool_name": "run_in_terminal", "tool_input": {}})
        assert output == {}, f"deny-writes must allow 'run_in_terminal', got: {output!r}"

    def test_unknown_tool_is_allowed(self) -> None:
        """AC-deny-writes-allow: unknown future tool_name must return {} (allowed)."""
        _, output = _run_hook("deny-writes", {"tool_name": "some_future_tool", "tool_input": {}})
        assert output == {}, f"deny-writes must allow unknown tools, got: {output!r}"

    def test_missing_tool_name_key_is_allowed(self) -> None:
        """AC-deny-writes-missing: absent tool_name key must return {} (fail-open)."""
        _, output = _run_hook("deny-writes", {"tool_input": {}})
        assert output == {}, (
            f"deny-writes must return {{}} when tool_name is absent, got: {output!r}"
        )

    def test_empty_tool_name_is_allowed(self) -> None:
        """AC-deny-writes-missing: empty string tool_name must return {} (fail-open)."""
        _, output = _run_hook("deny-writes", {"tool_name": "", "tool_input": {}})
        assert output == {}, (
            f"deny-writes must return {{}} when tool_name is empty string, got: {output!r}"
        )

    def test_deny_response_nests_under_hook_specific_output(self) -> None:
        """AC-deny-writes-response: deny must use hookSpecificOutput.permissionDecision."""
        _, output = _run_hook("deny-writes", {"tool_name": "create_file", "tool_input": {}})
        hso = output.get("hookSpecificOutput", {})
        assert hso.get("permissionDecision") == "deny", (
            f"deny response must have hookSpecificOutput.permissionDecision='deny', got: {output!r}"
        )

    def test_deny_response_has_nonempty_reason(self) -> None:
        """AC-deny-writes-response: deny must include a non-empty permissionDecisionReason."""
        _, output = _run_hook("deny-writes", {"tool_name": "create_file", "tool_input": {}})
        reason = output.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
        assert reason, (
            f"deny response must have non-empty permissionDecisionReason, got: {output!r}"
        )

    def test_exit_code_is_always_zero_on_deny(self) -> None:
        """All hooks must exit 0 even when denying (VS Code contract)."""
        exit_code, _ = _run_hook("deny-writes", {"tool_name": "create_file", "tool_input": {}})
        assert exit_code == 0, (
            f"deny-writes must exit 0 on deny, got exit code: {exit_code}"
        )


# ---------------------------------------------------------------------------
# deny-code-writes — deny-list path guard (doc-writer agent)
# ---------------------------------------------------------------------------


class TestFromAC_DenyCodeWrites:
    """deny-code-writes.py: deny writes to source dirs; allow other paths."""

    @pytest.mark.parametrize("path", _DCW_DENIED_PREFIX_PATHS)
    def test_denied_path_blocks_write(self, path: str) -> None:
        """AC-dcw-deny-{prefix}: write to a path in the deny-list must be blocked."""
        _, output = _run_hook(
            "deny-code-writes",
            {"tool_name": "create_file", "tool_input": {"filePath": path}},
        )
        assert _is_denied(output), (
            f"deny-code-writes must deny path '{path}', got: {output!r}"
        )

    @pytest.mark.parametrize("path", _DCW_ALLOWED_PATHS)
    def test_allowed_path_permits_write(self, path: str) -> None:
        """AC-dcw-allow-{path}: write to a non-denied path must return {} (allowed)."""
        _, output = _run_hook(
            "deny-code-writes",
            {"tool_name": "create_file", "tool_input": {"filePath": path}},
        )
        assert output == {}, (
            f"deny-code-writes must allow path '{path}', got: {output!r}"
        )

    def test_dirpath_field_is_checked(self) -> None:
        """AC-dcw-dirPath: create_directory with denied dirPath must be denied."""
        _, output = _run_hook(
            "deny-code-writes",
            {"tool_name": "create_directory", "tool_input": {"dirPath": "tests/subdir"}},
        )
        assert _is_denied(output), (
            f"deny-code-writes must check dirPath, got: {output!r}"
        )

    def test_allowed_dirpath_is_permitted(self) -> None:
        """AC-dcw-dirPath: create_directory with allowed dirPath must return {}."""
        _, output = _run_hook(
            "deny-code-writes",
            {"tool_name": "create_directory", "tool_input": {"dirPath": "share/skills/new-skill"}},
        )
        assert output == {}, (
            f"deny-code-writes must allow dirPath 'share/skills/new-skill', got: {output!r}"
        )

    def test_replacements_field_is_checked(self) -> None:
        """AC-dcw-replacements: multi_replace with denied replacements[].filePath → denied."""
        _, output = _run_hook(
            "deny-code-writes",
            {
                "tool_name": "multi_replace_string_in_file",
                "tool_input": {
                    "replacements": [
                        {"filePath": "serve/module.py", "oldString": "x", "newString": "y"}
                    ]
                },
            },
        )
        assert _is_denied(output), (
            f"deny-code-writes must check replacements[].filePath, got: {output!r}"
        )

    def test_editfiles_field_is_checked(self) -> None:
        """AC-dcw-editFiles: editFiles with denied files[] string element → denied."""
        _, output = _run_hook(
            "deny-code-writes",
            {"tool_name": "editFiles", "tool_input": {"files": ["serve/module.py"]}},
        )
        assert _is_denied(output), (
            f"deny-code-writes must check editFiles files[], got: {output!r}"
        )

    def test_mixed_replacements_one_denied_blocks_all(self) -> None:
        """AC-dcw-mixed: one denied replacement with one allowed → deny the whole call."""
        _, output = _run_hook(
            "deny-code-writes",
            {
                "tool_name": "multi_replace_string_in_file",
                "tool_input": {
                    "replacements": [
                        {"filePath": "share/skills/foo.md", "oldString": "a", "newString": "b"},
                        {"filePath": "serve/module.py", "oldString": "x", "newString": "y"},
                    ]
                },
            },
        )
        assert _is_denied(output), (
            f"deny-code-writes must deny when any replacement path is in deny-list, got: {output!r}"
        )

    def test_all_allowed_replacements_is_permitted(self) -> None:
        """AC-dcw-all-allowed: all replacements in allowed paths → allowed."""
        _, output = _run_hook(
            "deny-code-writes",
            {
                "tool_name": "multi_replace_string_in_file",
                "tool_input": {
                    "replacements": [
                        {"filePath": "share/skills/foo.md", "oldString": "a", "newString": "b"},
                        {"filePath": "README.md", "oldString": "x", "newString": "y"},
                    ]
                },
            },
        )
        assert output == {}, (
            f"deny-code-writes must allow when all replacements are in allowed paths, got: {output!r}"
        )

    def test_backslash_path_normalized_and_denied(self) -> None:
        """AC-dcw-backslash: serve\\foo.py must be normalized to serve/foo.py → denied."""
        _, output = _run_hook(
            "deny-code-writes",
            {"tool_name": "create_file", "tool_input": {"filePath": "serve\\mcp\\server.py"}},
        )
        assert _is_denied(output), (
            f"deny-code-writes must normalize backslashes and deny serve\\ path, got: {output!r}"
        )

    def test_leading_dot_slash_stripped_and_denied(self) -> None:
        """AC-dcw-dot-strip: ./serve/foo.py must be stripped to serve/foo.py → denied."""
        _, output = _run_hook(
            "deny-code-writes",
            {"tool_name": "create_file", "tool_input": {"filePath": "./serve/module.py"}},
        )
        assert _is_denied(output), (
            f"deny-code-writes must strip ./ prefix and deny, got: {output!r}"
        )

    def test_leading_dot_slash_conftest_exact_match_denied(self) -> None:
        """AC-dcw-dot-conftest: ./conftest.py stripped to conftest.py → exact-match denied."""
        _, output = _run_hook(
            "deny-code-writes",
            {"tool_name": "create_file", "tool_input": {"filePath": "./conftest.py"}},
        )
        assert _is_denied(output), (
            f"deny-code-writes must deny ./conftest.py (stripped to exact match), got: {output!r}"
        )

    def test_no_paths_in_tool_input_is_allowed(self) -> None:
        """AC-dcw-no-paths: write tool with empty tool_input → {} (fail-open, no paths)."""
        _, output = _run_hook(
            "deny-code-writes",
            {"tool_name": "create_file", "tool_input": {}},
        )
        assert output == {}, (
            f"deny-code-writes must return {{}} when no paths extracted, got: {output!r}"
        )

    def test_nonwrite_tool_is_allowed(self) -> None:
        """AC-dcw-nonwrite: non-write tool (read_file) must pass through regardless of path."""
        _, output = _run_hook(
            "deny-code-writes",
            {"tool_name": "read_file", "tool_input": {"filePath": "serve/module.py"}},
        )
        assert output == {}, (
            f"deny-code-writes must not gate read_file, got: {output!r}"
        )

    def test_conftest_bak_not_denied(self) -> None:
        """AC-dcw-boundary-cfbak: conftest.py.bak is not exact 'conftest.py' → allowed."""
        _, output = _run_hook(
            "deny-code-writes",
            {"tool_name": "create_file", "tool_input": {"filePath": "conftest.py.bak"}},
        )
        assert output == {}, (
            f"conftest.py.bak must not be denied (not exact 'conftest.py'), got: {output!r}"
        )

    def test_seedfile_prefix_not_denied(self) -> None:
        """AC-dcw-boundary-seed: seedfile.py starts with 'seed' but not 'seed/' → allowed."""
        _, output = _run_hook(
            "deny-code-writes",
            {"tool_name": "create_file", "tool_input": {"filePath": "seedfile.py"}},
        )
        assert output == {}, (
            f"seedfile.py must not be denied ('seed' without trailing /), got: {output!r}"
        )

    def test_share_skills_allowed_while_share_agents_denied(self) -> None:
        """AC-dcw-boundary-skills: share/skills/ is allowed; share/agents/ is denied."""
        _, allowed = _run_hook(
            "deny-code-writes",
            {"tool_name": "create_file", "tool_input": {"filePath": "share/skills/foo.md"}},
        )
        _, denied = _run_hook(
            "deny-code-writes",
            {"tool_name": "create_file", "tool_input": {"filePath": "share/agents/doc-writer.agent.md"}},
        )
        assert allowed == {}, (
            f"share/skills/ must be allowed (only share/agents/ is denied), got: {allowed!r}"
        )
        assert _is_denied(denied), (
            f"share/agents/ must be denied, got: {denied!r}"
        )


# ---------------------------------------------------------------------------
# deny-src-writes — allow-list path guard (test-writer, tests/ only)
# ---------------------------------------------------------------------------


class TestFromAC_DenySrcWrites:
    """deny-src-writes.py: only writes to tests/ are permitted."""

    @pytest.mark.parametrize(
        ("tool", "field", "path"),
        [
            ("create_file", "filePath", "tests/test_foo.py"),
            ("replace_string_in_file", "filePath", "tests/test_bar.py"),
            ("create_directory", "dirPath", "tests/subdir"),
        ],
    )
    def test_tests_path_is_allowed(self, tool: str, field: str, path: str) -> None:
        """AC-dsw-allow: write to tests/ path must return {} (allowed)."""
        _, output = _run_hook(
            "deny-src-writes",
            {"tool_name": tool, "tool_input": {field: path}},
        )
        assert output == {}, (
            f"deny-src-writes must allow '{path}' for {tool}, got: {output!r}"
        )

    @pytest.mark.parametrize("path", ["serve/module.py", "setup/init.py", "README.md"])
    def test_non_tests_path_is_denied(self, path: str) -> None:
        """AC-dsw-deny: write outside tests/ must be denied."""
        _, output = _run_hook(
            "deny-src-writes",
            {"tool_name": "create_file", "tool_input": {"filePath": path}},
        )
        assert _is_denied(output), (
            f"deny-src-writes must deny '{path}' (outside tests/), got: {output!r}"
        )

    def test_backslash_tests_path_is_allowed(self) -> None:
        """AC-dsw-backslash: tests\\foo.py normalized to tests/foo.py → allowed."""
        _, output = _run_hook(
            "deny-src-writes",
            {"tool_name": "create_file", "tool_input": {"filePath": "tests\\test_bar.py"}},
        )
        assert output == {}, (
            f"deny-src-writes must normalize backslashes: tests\\\\ path should be allowed, got: {output!r}"
        )

    def test_editfiles_tests_path_is_allowed(self) -> None:
        """AC-dsw-editFiles-allow: editFiles with tests/ in files[] → allowed."""
        _, output = _run_hook(
            "deny-src-writes",
            {"tool_name": "editFiles", "tool_input": {"files": ["tests/test_foo.py"]}},
        )
        assert output == {}, (
            f"deny-src-writes must allow editFiles with tests/ path, got: {output!r}"
        )

    def test_editfiles_non_tests_path_is_denied(self) -> None:
        """AC-dsw-editFiles-deny: editFiles with serve/ in files[] → denied."""
        _, output = _run_hook(
            "deny-src-writes",
            {"tool_name": "editFiles", "tool_input": {"files": ["serve/module.py"]}},
        )
        assert _is_denied(output), (
            f"deny-src-writes must deny editFiles with serve/ path, got: {output!r}"
        )

    def test_mixed_replacements_one_outside_tests_is_denied(self) -> None:
        """AC-dsw-mixed: one replacement outside tests/ → deny the whole call."""
        _, output = _run_hook(
            "deny-src-writes",
            {
                "tool_name": "multi_replace_string_in_file",
                "tool_input": {
                    "replacements": [
                        {"filePath": "tests/test_foo.py", "oldString": "a", "newString": "b"},
                        {"filePath": "serve/module.py", "oldString": "x", "newString": "y"},
                    ]
                },
            },
        )
        assert _is_denied(output), (
            f"deny-src-writes must deny when any replacement is outside tests/, got: {output!r}"
        )

    def test_no_paths_extracted_is_allowed(self) -> None:
        """AC-dsw-no-paths: write tool with no path fields → {} (fail-open)."""
        _, output = _run_hook(
            "deny-src-writes",
            {"tool_name": "create_file", "tool_input": {}},
        )
        assert output == {}, (
            f"deny-src-writes must return {{}} when no paths extracted, got: {output!r}"
        )

    def test_path_starting_with_tests_no_slash_is_denied(self) -> None:
        """AC-dsw-boundary-prefix: 'testsite.py' starts with 'tests' but not 'tests/' → denied."""
        _, output = _run_hook(
            "deny-src-writes",
            {"tool_name": "create_file", "tool_input": {"filePath": "testsite.py"}},
        )
        assert _is_denied(output), (
            f"deny-src-writes: 'testsite.py' must be denied (not inside tests/), got: {output!r}"
        )

    def test_apply_patch_is_gated(self) -> None:
        """AC-dsw-apply-patch: apply_patch with non-tests/ path must be denied."""
        _, output = _run_hook(
            "deny-src-writes",
            {"tool_name": "apply_patch", "tool_input": {"filePath": "serve/module.py"}},
        )
        assert _is_denied(output), (
            f"deny-src-writes must gate apply_patch, got: {output!r}"
        )

    def test_run_in_terminal_passes_through(self) -> None:
        """AC-dsw: run_in_terminal must return {} (non-write pass-through)."""
        _, output = _run_hook(
            "deny-src-writes",
            {"tool_name": "run_in_terminal", "tool_input": {"command": "echo hi"}},
        )
        assert output == {}, f"deny-src-writes must allow run_in_terminal, got: {output!r}"


# ---------------------------------------------------------------------------
# deny-scratch-only-writes — allow-list path guard (.owlbear/scratch/ only)
# ---------------------------------------------------------------------------


class TestFromAC_DenyScratchOnlyWrites:
    """deny-scratch-only-writes.py: only writes to .owlbear/scratch/ are permitted."""

    @pytest.mark.parametrize(
        "path",
        [
            ".owlbear/scratch/report.txt",
            ".owlbear/scratch/pytest-output-123.txt",
        ],
    )
    def test_scratch_path_is_allowed(self, path: str) -> None:
        """AC-dsow-allow: write to .owlbear/scratch/ must return {} (allowed)."""
        _, output = _run_hook(
            "deny-scratch-only-writes",
            {"tool_name": "create_file", "tool_input": {"filePath": path}},
        )
        assert output == {}, (
            f"deny-scratch-only-writes must allow '{path}', got: {output!r}"
        )

    @pytest.mark.parametrize("path", ["serve/module.py", "tests/test_foo.py"])
    def test_non_scratch_path_is_denied(self, path: str) -> None:
        """AC-dsow-deny: write outside .owlbear/scratch/ must be denied."""
        _, output = _run_hook(
            "deny-scratch-only-writes",
            {"tool_name": "create_file", "tool_input": {"filePath": path}},
        )
        assert _is_denied(output), (
            f"deny-scratch-only-writes must deny '{path}', got: {output!r}"
        )

    def test_backslash_scratch_path_is_allowed(self) -> None:
        """AC-dsow-backslash: .owlbear\\scratch\\x normalized → allowed."""
        _, output = _run_hook(
            "deny-scratch-only-writes",
            {"tool_name": "create_file", "tool_input": {"filePath": ".owlbear\\scratch\\report.txt"}},
        )
        assert output == {}, (
            f"deny-scratch-only-writes must normalize backslashes: .owlbear\\\\scratch → allowed, got: {output!r}"
        )

    def test_owlbear_hooks_dir_is_denied(self) -> None:
        """AC-dsow-hooks-denied: .owlbear/hooks/ is NOT .owlbear/scratch/ → denied."""
        _, output = _run_hook(
            "deny-scratch-only-writes",
            {"tool_name": "create_file", "tool_input": {"filePath": ".owlbear/hooks/new-hook.py"}},
        )
        assert _is_denied(output), (
            f"deny-scratch-only-writes must deny .owlbear/hooks/ (not scratch/), got: {output!r}"
        )

    def test_editfiles_scratch_path_is_allowed(self) -> None:
        """AC-dsow-editFiles: editFiles with .owlbear/scratch/ in files[] → allowed."""
        _, output = _run_hook(
            "deny-scratch-only-writes",
            {"tool_name": "editFiles", "tool_input": {"files": [".owlbear/scratch/out.txt"]}},
        )
        assert output == {}, (
            f"deny-scratch-only-writes must allow editFiles with scratch path, got: {output!r}"
        )

    def test_no_paths_extracted_is_allowed(self) -> None:
        """AC-dsow-no-paths: write tool with no path fields → {} (fail-open)."""
        _, output = _run_hook(
            "deny-scratch-only-writes",
            {"tool_name": "create_file", "tool_input": {}},
        )
        assert output == {}, (
            f"deny-scratch-only-writes must return {{}} when no paths extracted, got: {output!r}"
        )

    def test_owlbear_scratchpad_is_denied(self) -> None:
        """AC-dsow-boundary-pad: .owlbear/scratchpad/ is NOT .owlbear/scratch/ → denied."""
        _, output = _run_hook(
            "deny-scratch-only-writes",
            {"tool_name": "create_file", "tool_input": {"filePath": ".owlbear/scratchpad/notes.txt"}},
        )
        assert _is_denied(output), (
            f"deny-scratch-only-writes must deny .owlbear/scratchpad/ (not scratch/), got: {output!r}"
        )

    def test_mixed_editfiles_one_non_scratch_is_denied(self) -> None:
        """AC-dsow-mixed: editFiles with one non-scratch + one scratch path → deny all."""
        _, output = _run_hook(
            "deny-scratch-only-writes",
            {
                "tool_name": "editFiles",
                "tool_input": {
                    "files": [
                        ".owlbear/scratch/ok.txt",
                        "serve/module.py",
                    ]
                },
            },
        )
        assert _is_denied(output), (
            f"deny-scratch-only-writes must deny when any path is outside scratch, got: {output!r}"
        )


# ---------------------------------------------------------------------------
# allow-stances-only — allow-list path guard (ideation panelists, /stances/ only)
# ---------------------------------------------------------------------------


class TestFromAC_AllowStancesOnly:
    """allow-stances-only.py: only writes containing /stances/ as a path component are permitted."""

    def test_stances_path_is_allowed(self) -> None:
        """AC-aso-allow: create_file in stances/ must return {} (allowed)."""
        _, output = _run_hook(
            "allow-stances-only",
            {"tool_name": "create_file", "tool_input": {"filePath": "stances/architect.md"}},
        )
        assert output == {}, (
            f"allow-stances-only must allow 'stances/architect.md', got: {output!r}"
        )

    @pytest.mark.parametrize("path", ["serve/module.py", "README.md", ".owlbear/research/foo.md"])
    def test_non_stances_path_is_denied(self, path: str) -> None:
        """AC-aso-deny: write outside /stances/ must be denied."""
        _, output = _run_hook(
            "allow-stances-only",
            {"tool_name": "create_file", "tool_input": {"filePath": path}},
        )
        assert _is_denied(output), (
            f"allow-stances-only must deny '{path}', got: {output!r}"
        )

    def test_leading_dot_slash_stances_is_allowed(self) -> None:
        """AC-aso-dot-strip: ./stances/arch.md stripped to stances/arch.md → allowed."""
        _, output = _run_hook(
            "allow-stances-only",
            {"tool_name": "create_file", "tool_input": {"filePath": "./stances/arch.md"}},
        )
        assert output == {}, (
            f"allow-stances-only must strip ./ and allow stances/ path, got: {output!r}"
        )

    def test_backslash_stances_path_is_allowed(self) -> None:
        """AC-aso-backslash: stances\\arch.md normalized to stances/arch.md → allowed."""
        _, output = _run_hook(
            "allow-stances-only",
            {"tool_name": "create_file", "tool_input": {"filePath": "stances\\arch.md"}},
        )
        assert output == {}, (
            f"allow-stances-only must normalize backslashes and allow stances\\\\ path, got: {output!r}"
        )

    def test_nested_stances_path_component_is_allowed(self) -> None:
        """AC-aso-nested: foo/stances/bar.md — /stances/ appears mid-path → allowed."""
        _, output = _run_hook(
            "allow-stances-only",
            {
                "tool_name": "create_file",
                "tool_input": {"filePath": "issues/7/stances/challenger.md"},
            },
        )
        assert output == {}, (
            f"allow-stances-only must allow paths containing /stances/ anywhere, got: {output!r}"
        )

    def test_no_paths_extracted_is_allowed(self) -> None:
        """AC-aso-no-paths: write tool with no path fields → {} (fail-open)."""
        _, output = _run_hook(
            "allow-stances-only",
            {"tool_name": "create_file", "tool_input": {}},
        )
        assert output == {}, (
            f"allow-stances-only must return {{}} when no paths extracted, got: {output!r}"
        )

    def test_editfiles_stances_path_is_allowed(self) -> None:
        """AC-aso-editFiles-allow: editFiles with stances/ in files[] → allowed."""
        _, output = _run_hook(
            "allow-stances-only",
            {"tool_name": "editFiles", "tool_input": {"files": ["stances/data.md"]}},
        )
        assert output == {}, (
            f"allow-stances-only must allow editFiles with stances/ path, got: {output!r}"
        )

    def test_editfiles_non_stances_path_is_denied(self) -> None:
        """AC-aso-editFiles-deny: editFiles with non-stances path → denied."""
        _, output = _run_hook(
            "allow-stances-only",
            {"tool_name": "editFiles", "tool_input": {"files": ["share/skills/foo.md"]}},
        )
        assert _is_denied(output), (
            f"allow-stances-only must deny editFiles outside stances/, got: {output!r}"
        )

    def test_multi_replace_stances_paths_is_allowed(self) -> None:
        """AC-aso-replacements: multi_replace with all stances/ replacements → allowed."""
        _, output = _run_hook(
            "allow-stances-only",
            {
                "tool_name": "multi_replace_string_in_file",
                "tool_input": {
                    "replacements": [
                        {"filePath": "stances/arch.md", "oldString": "a", "newString": "b"}
                    ]
                },
            },
        )
        assert output == {}, (
            f"allow-stances-only must allow multi_replace with all stances/ paths, got: {output!r}"
        )

    def test_run_in_terminal_passes_through(self) -> None:
        """AC-aso: run_in_terminal must return {} (non-write pass-through)."""
        _, output = _run_hook(
            "allow-stances-only",
            {"tool_name": "run_in_terminal", "tool_input": {"command": "echo hi"}},
        )
        assert output == {}, (
            f"allow-stances-only must allow run_in_terminal, got: {output!r}"
        )


# ---------------------------------------------------------------------------
# Malformed input — all 5 hooks must fail-open (return {} exit 0)
# ---------------------------------------------------------------------------


class TestFromAC_MalformedInput:
    """All 5 hooks must return {} with exit 0 for any malformed stdin (fail-open contract)."""

    @pytest.mark.parametrize("hook_name", _ALL_HOOK_NAMES)
    def test_truncated_json_returns_empty(self, hook_name: str) -> None:
        """AC-malformed-truncated: truncated JSON → {} exit 0 for each hook."""
        exit_code, output = _run_hook(
            hook_name, '{"tool_name": "create_file", "tool_input":'
        )
        assert exit_code == 0, f"{hook_name}: truncated JSON must exit 0, got: {exit_code}"
        assert output == {}, f"{hook_name}: truncated JSON must return {{}}, got: {output!r}"

    @pytest.mark.parametrize("hook_name", _ALL_HOOK_NAMES)
    def test_empty_stdin_returns_empty(self, hook_name: str) -> None:
        """AC-malformed-empty: empty stdin → {} exit 0 for each hook."""
        exit_code, output = _run_hook(hook_name, "")
        assert exit_code == 0, f"{hook_name}: empty stdin must exit 0, got: {exit_code}"
        assert output == {}, f"{hook_name}: empty stdin must return {{}}, got: {output!r}"

    @pytest.mark.parametrize("hook_name", _ALL_HOOK_NAMES)
    def test_bom_prefix_returns_empty(self, hook_name: str) -> None:
        """AC-malformed-bom: UTF-8 BOM-prefixed non-JSON → {} exit 0 for each hook."""
        bom_data = b"\xef\xbb\xbfnot valid json"
        exit_code, output = _run_hook(hook_name, bom_data)
        assert exit_code == 0, f"{hook_name}: BOM input must exit 0, got: {exit_code}"
        assert output == {}, f"{hook_name}: BOM input must return {{}}, got: {output!r}"

    @pytest.mark.parametrize("hook_name", _ALL_HOOK_NAMES)
    def test_binary_data_returns_empty(self, hook_name: str) -> None:
        """AC-malformed-binary: arbitrary binary data → {} exit 0 for each hook."""
        binary_data = bytes(range(256))
        exit_code, output = _run_hook(hook_name, binary_data)
        assert exit_code == 0, f"{hook_name}: binary data must exit 0, got: {exit_code}"
        assert output == {}, f"{hook_name}: binary data must return {{}}, got: {output!r}"
