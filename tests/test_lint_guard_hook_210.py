"""Tests for task #210: Add PostToolUse lint guard hook to builder agent (Phase 2).

Contract-level tests for:
1. scripts/hooks/lint-changed.ps1 script behavior (PowerShell, Windows only)
2. agents/builder.agent.md PostToolUse hooks: frontmatter

Assumed PostToolUse stdin JSON format (VS Code 3/25/2026 spec):
  {
    "tool_name": "<tool_name>",
    "tool_input": {
      "filePath": "<abs_path>",        # for create_file / replace_string_in_file
      "replacements": [                # for multi_replace_string_in_file
        {"filePath": "<abs_path>"},
        ...
      ]
    }
  }

AC coverage:
  AC1a: scripts/hooks/lint-changed.ps1 exists at the expected path
  AC1b: script file is non-empty
  AC2:  non-edit tool_name values (e.g. read_file) → returns {}
  AC3a: create_file + lint errors → {"systemMessage": "<ruff output>"} (non-empty)
  AC3b: create_file + clean file → {}
  AC3c: replace_string_in_file + lint errors → {"systemMessage": "..."}
  AC3d: replace_string_in_file + clean file → {}
  AC3e: multi_replace_string_in_file + lint errors → {"systemMessage": "..."}
  AC3f: multi_replace_string_in_file + clean files → {}
  AC5:  ruff invocation fails (file path does not exist on disk) → {}
  AC6a: script never exits with code 2 — clean file case
  AC6b: script never exits with code 2 — lint-error case
  AC6c: script never exits with code 2 — non-edit tool case
  AC6d: all script outputs are valid JSON
  AC7:  agents/builder.agent.md frontmatter contains a hooks: section
  AC8a: PostToolUse hook entry exists under hooks:
  AC8b: PostToolUse hook has type: command
  AC8c: PostToolUse hook command references lint-changed.ps1
  AC9:  builder.agent.md frontmatter has no duplicate YAML keys
  AC10: builder.agent.md frontmatter is parseable as valid YAML
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).parent.parent
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "hooks" / "lint-changed.ps1"
_BUILDER_AGENT = _REPO_ROOT / "share" / "agents" / "builder.agent.md"

# A Python source that reliably generates an F401 unused-import ruff error.
_LINT_ERROR_CONTENT = "import os\n"

# A Python source that is ruff-clean under the project's ruff config.
_CLEAN_CONTENT = "x: int = 1\n"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_hook(stdin_data: dict, *, timeout: int = 30) -> tuple[int, dict]:
    """Run lint-changed.ps1 with the given stdin JSON.

    Returns (exit_code, parsed_stdout_json).
    Raises FileNotFoundError if the script does not yet exist — this makes
    RED-phase failures explicit instead of silently returning {} on missing script.
    """
    if not _SCRIPT_PATH.exists():
        msg = (
            f"lint-changed.ps1 not found at {_SCRIPT_PATH}. "
            "Builder must create scripts/hooks/lint-changed.ps1 to make these tests pass."
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


def _extract_frontmatter(content: str) -> str:
    """Return the YAML text between the first --- ... --- block."""
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    assert match is not None, (
        "No valid YAML frontmatter (--- ... ---) found in builder.agent.md"
    )
    return match.group(1)


# ---------------------------------------------------------------------------
# AC1 — lint-changed.ps1 must exist
# ---------------------------------------------------------------------------


class TestFromAC_ScriptExists:
    """AC1: scripts/hooks/lint-changed.ps1 must be created by the builder."""

    def test_lint_changed_ps1_exists(self) -> None:
        """AC1a: scripts/hooks/lint-changed.ps1 must exist on disk."""
        assert _SCRIPT_PATH.exists(), (
            f"lint-changed.ps1 not found at {_SCRIPT_PATH}. "
            "Builder must create scripts/hooks/lint-changed.ps1."
        )

    def test_script_is_nonempty(self) -> None:
        """AC1b: script file must have content — an empty file is not a valid hook."""
        assert _SCRIPT_PATH.exists(), (
            f"lint-changed.ps1 not found at {_SCRIPT_PATH}."
        )
        assert _SCRIPT_PATH.stat().st_size > 0, (
            "lint-changed.ps1 exists but is empty — builder must implement it."
        )


# ---------------------------------------------------------------------------
# AC2/AC3/AC5/AC6 — script I/O behaviour (Windows/PowerShell required)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell hook requires Windows")
class TestFromAC_LintGuardBehavior:
    """Script behaviour tests exercised via subprocess on Windows.

    All tests use _run_hook() which raises FileNotFoundError if the script
    does not yet exist — making RED-phase failures clear.
    """

    # --- AC2: non-edit tools return {} ---

    def test_read_file_tool_returns_empty_json(self) -> None:
        """AC2: tool_name='read_file' is not an edit tool — must return {}."""
        _, output = _run_hook({"tool_name": "read_file", "tool_input": {}})
        assert output == {}

    def test_semantic_search_tool_returns_empty_json(self) -> None:
        """AC2: tool_name='semantic_search' is not an edit tool — must return {}."""
        _, output = _run_hook({"tool_name": "semantic_search", "tool_input": {}})
        assert output == {}

    def test_unknown_tool_name_returns_empty_json(self) -> None:
        """AC2: unknown/future tool_name values — must return {}."""
        _, output = _run_hook({"tool_name": "some_future_tool", "tool_input": {}})
        assert output == {}

    # --- AC3b/AC3d/AC3f: edit tools + clean files return {} ---

    def test_create_file_clean_returns_empty_json(self, tmp_path: Path) -> None:
        """AC3b: create_file with a ruff-clean file — must return {}."""
        clean_file = tmp_path / "clean1.py"
        clean_file.write_text(_CLEAN_CONTENT, encoding="utf-8")
        _, output = _run_hook(
            {"tool_name": "create_file", "tool_input": {"filePath": str(clean_file)}}
        )
        assert output == {}

    def test_replace_string_in_file_clean_returns_empty_json(self, tmp_path: Path) -> None:
        """AC3d: replace_string_in_file with a clean file — must return {}."""
        clean_file = tmp_path / "clean2.py"
        clean_file.write_text(_CLEAN_CONTENT, encoding="utf-8")
        _, output = _run_hook(
            {
                "tool_name": "replace_string_in_file",
                "tool_input": {"filePath": str(clean_file)},
            }
        )
        assert output == {}

    def test_multi_replace_clean_returns_empty_json(self, tmp_path: Path) -> None:
        """AC3f: multi_replace_string_in_file with all clean files — must return {}."""
        clean_file = tmp_path / "clean3.py"
        clean_file.write_text(_CLEAN_CONTENT, encoding="utf-8")
        _, output = _run_hook(
            {
                "tool_name": "multi_replace_string_in_file",
                "tool_input": {"replacements": [{"filePath": str(clean_file)}]},
            }
        )
        assert output == {}

    # --- AC3a/AC3c/AC3e: edit tools + lint errors return systemMessage ---

    def test_create_file_lint_errors_returns_system_message(self, tmp_path: Path) -> None:
        """AC3a: create_file with ruff errors — must return {"systemMessage": "..."}."""
        bad_file = tmp_path / "bad1.py"
        bad_file.write_text(_LINT_ERROR_CONTENT, encoding="utf-8")
        _, output = _run_hook(
            {"tool_name": "create_file", "tool_input": {"filePath": str(bad_file)}}
        )
        assert "systemMessage" in output, (
            f"Expected {{'systemMessage': '...'}}, got {output!r}"
        )
        assert output["systemMessage"], "systemMessage must be non-empty ruff output"

    def test_replace_string_in_file_lint_errors_returns_system_message(
        self, tmp_path: Path
    ) -> None:
        """AC3c: replace_string_in_file with ruff errors — must return {"systemMessage": "..."}."""
        bad_file = tmp_path / "bad2.py"
        bad_file.write_text(_LINT_ERROR_CONTENT, encoding="utf-8")
        _, output = _run_hook(
            {
                "tool_name": "replace_string_in_file",
                "tool_input": {"filePath": str(bad_file)},
            }
        )
        assert "systemMessage" in output, (
            f"Expected {{'systemMessage': '...'}}, got {output!r}"
        )

    def test_multi_replace_lint_errors_returns_system_message(self, tmp_path: Path) -> None:
        """AC3e: multi_replace_string_in_file with ruff errors — must return {"systemMessage": "..."}."""
        bad_file = tmp_path / "bad3.py"
        bad_file.write_text(_LINT_ERROR_CONTENT, encoding="utf-8")
        _, output = _run_hook(
            {
                "tool_name": "multi_replace_string_in_file",
                "tool_input": {"replacements": [{"filePath": str(bad_file)}]},
            }
        )
        assert "systemMessage" in output, (
            f"Expected {{'systemMessage': '...'}}, got {output!r}"
        )

    # --- AC5: ruff failure (file missing) → {} ---

    def test_ruff_failure_nonexistent_file_returns_empty_json(self) -> None:
        """AC5: file path doesn't exist on disk — ruff fails gracefully, returns {}."""
        stdin = {
            "tool_name": "create_file",
            "tool_input": {"filePath": "/nonexistent/path/no_such_file_abc123.py"},
        }
        _, output = _run_hook(stdin)
        assert output == {}

    # --- AC6: script never exits with code 2 ---

    def test_exit_code_never_2_for_clean_file(self, tmp_path: Path) -> None:
        """AC6a: exit code must never be 2 — clean file path."""
        clean_file = tmp_path / "clean4.py"
        clean_file.write_text(_CLEAN_CONTENT, encoding="utf-8")
        code, _ = _run_hook(
            {"tool_name": "create_file", "tool_input": {"filePath": str(clean_file)}}
        )
        assert code != 2, (
            f"Script must never exit with code 2 (non-blocking design), got {code}"
        )

    def test_exit_code_never_2_for_lint_errors(self, tmp_path: Path) -> None:
        """AC6b: exit code must never be 2 — lint errors must use systemMessage, not exit 2."""
        bad_file = tmp_path / "bad4.py"
        bad_file.write_text(_LINT_ERROR_CONTENT, encoding="utf-8")
        code, _ = _run_hook(
            {"tool_name": "create_file", "tool_input": {"filePath": str(bad_file)}}
        )
        assert code != 2, (
            f"Lint errors must not block builder via exit code 2 (non-blocking), got {code}"
        )

    def test_exit_code_never_2_for_non_edit_tool(self) -> None:
        """AC6c: exit code must never be 2 — non-edit tool path."""
        code, _ = _run_hook({"tool_name": "read_file", "tool_input": {}})
        assert code != 2, (
            f"Script must never exit with code 2 for non-edit tools, got {code}"
        )

    def test_output_is_always_valid_json(self, tmp_path: Path) -> None:
        """AC6d: stdout must always be parseable JSON (empty {} or {"systemMessage": "..."})."""
        if not _SCRIPT_PATH.exists():
            pytest.fail(
                f"lint-changed.ps1 not found at {_SCRIPT_PATH}. "
                "Builder must create scripts/hooks/lint-changed.ps1 to make this test pass."
            )
        bad_file = tmp_path / "bad5.py"
        bad_file.write_text(_LINT_ERROR_CONTENT, encoding="utf-8")
        # Invoke directly to check raw stdout without the _run_hook JSON fallback
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-File", str(_SCRIPT_PATH)],
            input=json.dumps(
                {"tool_name": "create_file", "tool_input": {"filePath": str(bad_file)}}
            ),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        stdout = result.stdout.strip()
        # Must be parseable JSON — no plain text allowed
        try:
            parsed = json.loads(stdout) if stdout else {}
        except json.JSONDecodeError as exc:
            pytest.fail(
                f"Script stdout is not valid JSON: {stdout!r}\nError: {exc}"
            )
        assert isinstance(parsed, dict), f"Output must be a JSON object, got: {parsed!r}"


# ---------------------------------------------------------------------------
# AC7/AC8/AC9/AC10 — builder.agent.md frontmatter
# ---------------------------------------------------------------------------


class TestFromAC_BuilderAgentHooks:
    """builder.agent.md must gain a valid hooks: section for the PostToolUse lint guard."""

    def _frontmatter(self) -> str:
        content = _BUILDER_AGENT.read_text(encoding="utf-8")
        return _extract_frontmatter(content)

    def test_frontmatter_has_hooks_section(self) -> None:
        """AC7: builder.agent.md frontmatter must contain a hooks: key."""
        fm = self._frontmatter()
        assert re.search(r"^hooks:", fm, re.MULTILINE), (
            "builder.agent.md frontmatter is missing the 'hooks:' key. "
            "Builder must add a PostToolUse hooks section."
        )

    def test_frontmatter_has_posttooluse_entry(self) -> None:
        """AC8a: hooks: section must contain a PostToolUse entry."""
        fm = self._frontmatter()
        # hooks: must be present and PostToolUse must appear somewhere after it
        assert "PostToolUse" in fm, (
            "builder.agent.md frontmatter hooks: section is missing a PostToolUse entry."
        )

    def test_posttooluse_hook_type_is_command(self) -> None:
        """AC8b: PostToolUse hook must specify type: command."""
        fm = self._frontmatter()
        # 'type: command' must appear in the YAML (within hooks context)
        assert re.search(r"type:\s*command", fm), (
            "builder.agent.md PostToolUse hook must have 'type: command'"
        )

    def test_posttooluse_hook_command_references_lint_changed(self) -> None:
        """AC8c: PostToolUse hook command: value must reference lint-changed.ps1."""
        fm = self._frontmatter()
        assert "lint-changed.ps1" in fm, (
            "builder.agent.md PostToolUse hook command must point to lint-changed.ps1"
        )

    def test_frontmatter_no_duplicate_keys(self) -> None:
        """AC9: builder.agent.md frontmatter must have no duplicate YAML keys.

        Fails pre-impl (hooks: absent) by requiring the section is present before
        the duplicate-key regression check is meaningful.
        """
        fm = self._frontmatter()
        # Fail if hooks: not present yet — duplicate check is only meaningful post-addition
        assert "hooks:" in fm, (
            "Builder must add the hooks: section — no duplicate-key check is meaningful "
            "before the PostToolUse hook is added."
        )
        # Extract all top-level YAML keys (lines starting with a word followed by :)
        top_level_keys = re.findall(r"^([a-zA-Z][a-zA-Z0-9_-]*):", fm, re.MULTILINE)
        seen: set[str] = set()
        duplicates: list[str] = []
        for key in top_level_keys:
            if key in seen:
                duplicates.append(key)
            seen.add(key)
        assert not duplicates, (
            f"Duplicate YAML keys found in builder.agent.md frontmatter: {duplicates}"
        )

    def test_frontmatter_is_parseable_yaml_with_posttooluse_hook(self) -> None:
        """AC10: builder.agent.md frontmatter must parse as valid YAML after hook addition.

        Asserts both YAML validity AND presence of hooks/PostToolUse keys so this
        test fails pre-impl (no hooks yet) and passes once the builder is done.
        """
        import yaml  # noqa: PLC0415

        fm = self._frontmatter()
        try:
            parsed = yaml.safe_load(fm)
        except yaml.YAMLError as exc:
            pytest.fail(
                f"builder.agent.md frontmatter is not valid YAML: {exc}"
            )
        assert isinstance(parsed, dict), (
            f"Parsed YAML frontmatter must be a dict, got: {type(parsed)}"
        )
        # Compound check: hooks must be present for AC10 to be meaningful
        assert "hooks" in parsed, (
            "Frontmatter parsed successfully but is missing 'hooks:' key — "
            "builder must add the PostToolUse hooks section."
        )
        hooks = parsed["hooks"]
        assert "PostToolUse" in hooks, (
            "hooks: section is missing a PostToolUse entry — "
            "builder must add the PostToolUse lint guard hook."
        )
