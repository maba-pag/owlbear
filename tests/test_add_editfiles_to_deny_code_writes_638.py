"""Tests for task #638: Add editFiles to deny-code-writes.ps1 write-tool gate.

Contract-level tests for:
1. .owlbear/scratch/editfiles-schema-*.json  -- captured schema verification artifact (AC1)
2. .owlbear/hooks/deny-code-writes.ps1       -- editFiles added to write-tool gate (AC2)
3. share/agents/doc-writer.agent.md          -- edit/editFiles re-added to tools list (AC3)

PreToolUse stdin JSON format for editFiles (VS Code hooks docs, confidence .82):
  {
    "tool_name": "editFiles",
    "tool_input": { "files": ["src/main.ts"] }
  }

Note: tool_name is camelCase ("editFiles") -- exact match required in write-tools array.

Path extraction (AC2):
  - tool_input.files[*] -- string elements or object-with-filePath elements (defensive)

Deny-list (inherited from deny-code-writes.ps1 built in #591):
  Prefixes: serve/, v1/, tests/, setup/, seed/, store/, share/agents/, .git/,
            .owlbear/hooks/, .owlbear/scripts/
  Exact:    conftest.py

Path normalization: \\ -> /, strip leading ./

AC coverage map:
  AC1:          .owlbear/scratch/editfiles-schema-*.json artifact exists and is valid JSON
  AC2-deny1:    editFiles files=["serve/..."] -> denied (string element, denied prefix)
  AC2-deny2:    editFiles files=["tests/..."] -> denied (string element, another deny prefix)
  AC2-allow1:   editFiles files=["README.md"] -> {} (string element, allowed path; AC4 allow)
  AC2-empty:    editFiles files=[] -> {} (edge: empty array, nothing to check)
  AC2-multi-allow: editFiles files=["README.md","share/skills/SKILL.md"] -> {} (all allowed)
  AC2-mixed:    editFiles files=["README.md","serve/foo.py"] -> denied (any denied = whole call)
  AC2-obj-deny: editFiles files=[{filePath:"serve/foo.py"}] -> denied (object form, denied)
  AC2-obj-allow: editFiles files=[{filePath:"README.md"}] -> {} (object form, allowed)
  AC2-no-files: editFiles with no 'files' key -> {} (nothing extractable, pass-through)
  AC2-bslash:   editFiles files=["serve\\foo.py"] -> denied (backslash normalized)
  AC2-dotslash: editFiles files=["./serve/foo.py"] -> denied (./ stripped)
  AC2-camel:    tool_name="editFiles" is gated (camelCase matched)
  AC2-lower:    tool_name="editfiles" (wrong case) -> {} (exact match only)
  AC3:          doc-writer.agent.md tools list contains edit/editFiles (hooks: also present)
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).parent.parent
_SCRIPT_PATH = _REPO_ROOT / ".owlbear" / "hooks" / "deny-code-writes.ps1"
_AGENT_PATH = _REPO_ROOT / "share" / "agents" / "doc-writer.agent.md"
_SCRATCH_DIR = _REPO_ROOT / ".owlbear" / "scratch"


# ---------------------------------------------------------------------------
# Helpers -- mirror the pattern from test_deny_code_writes_hook_591.py
# ---------------------------------------------------------------------------


def _run_hook(stdin_data: dict, *, timeout: int = 30) -> tuple[int, dict]:
    """Run deny-code-writes.ps1 with the given stdin JSON.

    Returns (exit_code, parsed_stdout_json).
    Raises FileNotFoundError if the script does not yet exist.
    """
    if not _SCRIPT_PATH.exists():
        msg = (
            f"deny-code-writes.ps1 not found at {_SCRIPT_PATH}. "
            "Builder must create .owlbear/hooks/deny-code-writes.ps1 (#591) "
            "before #638 can be implemented."
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
    return output.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


def _schema_artifacts() -> list[Path]:
    """Return all editfiles-schema-*.json files in .owlbear/scratch/."""
    return list(_SCRATCH_DIR.glob("editfiles-schema-*.json"))


# ---------------------------------------------------------------------------
# AC1 -- Schema verification artifact
# ---------------------------------------------------------------------------


class TestFromAC_EditFilesSchemaArtifact:
    """Builder must capture actual editFiles PreToolUse stdin and save as JSON (AC1)."""

    def test_schema_capture_artifact_exists(self) -> None:
        """AC1: At least one editfiles-schema-*.json must exist in .owlbear/scratch/."""
        artifacts = _schema_artifacts()
        assert artifacts, (
            f"No editfiles-schema-*.json found in {_SCRATCH_DIR}. "
            "Builder must deploy the logging hook (research doc section 4), invoke editFiles "
            "via doc-writer, and capture the hook stdin to "
            ".owlbear/scratch/editfiles-schema-*.json."
        )

    def test_schema_artifact_is_valid_json(self) -> None:
        """AC1: Captured schema artifact must be valid JSON (parseable hook stdin)."""
        artifacts = _schema_artifacts()
        assert artifacts, (
            f"No editfiles-schema-*.json found in {_SCRATCH_DIR}. "
            "Builder must create the schema capture artifact first (see AC1)."
        )
        artifact = artifacts[0]
        content = artifact.read_text(encoding="utf-8")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            pytest.fail(
                f"Schema artifact {artifact.name} is not valid JSON: {exc}\n"
                f"Content: {content!r}"
            )
        assert isinstance(parsed, dict), (
            f"Schema artifact must be a JSON object, got: {type(parsed)}"
        )


# ---------------------------------------------------------------------------
# AC2 + AC4 -- editFiles path extraction (requires Windows/PowerShell)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell hook requires Windows")
class TestFromAC_EditFilesPathExtraction:
    """editFiles must be added to write-tools gate with files[] extraction (AC2, AC4)."""

    # --- AC2-deny1: string element, denied prefix (serve/) ---

    def test_editfiles_string_element_serve_path_is_denied(self) -> None:
        """AC2-deny1: editFiles with files=["serve/..."] must be denied."""
        _, output = _run_hook({
            "tool_name": "editFiles",
            "tool_input": {"files": ["serve/mcp-kanban/server.py"]},
        })
        assert _is_denied(output), (
            f"editFiles with serve/ path must be denied, got: {output!r}. "
            "Builder must add 'editFiles' to write-tools array and extract tool_input.files[*]."
        )

    # --- AC2-deny2: string element, another denied prefix (tests/) ---

    def test_editfiles_string_element_tests_path_is_denied(self) -> None:
        """AC2-deny2: editFiles with files=["tests/..."] must be denied."""
        _, output = _run_hook({
            "tool_name": "editFiles",
            "tool_input": {"files": ["tests/test_evil.py"]},
        })
        assert _is_denied(output), (
            f"editFiles with tests/ path must be denied, got: {output!r}."
        )

    # --- AC2-allow1: string element, allowed path (AC4 allow case) ---

    def test_editfiles_string_element_allowed_path_returns_empty(self) -> None:
        """AC2-allow1 / AC4 allow: editFiles with files=["README.md"] must return {}."""
        _, output = _run_hook({
            "tool_name": "editFiles",
            "tool_input": {"files": ["README.md"]},
        })
        assert output == {}, (
            f"editFiles with allowed path must return {{}}, got: {output!r}."
        )

    # --- AC2-empty: empty files array ---

    def test_editfiles_empty_files_array_returns_empty(self) -> None:
        """AC2-empty: editFiles with files=[] has no paths to check -- must return {}."""
        _, output = _run_hook({
            "tool_name": "editFiles",
            "tool_input": {"files": []},
        })
        assert output == {}, (
            f"editFiles with empty files array must return {{}} (nothing to deny), "
            f"got: {output!r}."
        )

    # --- AC2-multi-allow: multiple files, all allowed ---

    def test_editfiles_multiple_all_allowed_returns_empty(self) -> None:
        """AC2-multi-allow: editFiles with all allowed paths must return {}."""
        _, output = _run_hook({
            "tool_name": "editFiles",
            "tool_input": {"files": ["README.md", "share/skills/h-pytest-and-linting/SKILL.md"]},
        })
        assert output == {}, (
            f"editFiles with all allowed paths must return {{}}, got: {output!r}."
        )

    # --- AC2-mixed: any denied path denies whole call ---

    def test_editfiles_mixed_files_any_denied_is_denied(self) -> None:
        """AC2-mixed: editFiles with one denied path in files[] must deny the whole call."""
        _, output = _run_hook({
            "tool_name": "editFiles",
            "tool_input": {"files": ["README.md", "serve/mcp-kanban/server.py"]},
        })
        assert _is_denied(output), (
            f"editFiles with any denied path must deny the whole call, got: {output!r}."
        )

    # --- AC2-obj-deny: object element (defensive form), denied path ---

    def test_editfiles_object_element_denied_path_is_denied(self) -> None:
        """AC2-obj-deny: editFiles files=[{filePath:"serve/..."}] denied (defensive form)."""
        _, output = _run_hook({
            "tool_name": "editFiles",
            "tool_input": {"files": [{"filePath": "serve/mcp-kanban/server.py"}]},
        })
        assert _is_denied(output), (
            f"editFiles with object-element denied path must be denied, got: {output!r}. "
            "Builder must handle both string and object-with-filePath elements (AC2 defensive)."
        )

    # --- AC2-obj-allow: object element (defensive form), allowed path ---

    def test_editfiles_object_element_allowed_path_returns_empty(self) -> None:
        """AC2-obj-allow: editFiles files=[{filePath:"README.md"}] -> {} (defensive form)."""
        _, output = _run_hook({
            "tool_name": "editFiles",
            "tool_input": {"files": [{"filePath": "README.md"}]},
        })
        assert output == {}, (
            f"editFiles with object-element allowed path must return {{}}, got: {output!r}."
        )

    # --- AC2-no-files: missing 'files' key ---

    def test_editfiles_missing_files_key_returns_empty(self) -> None:
        """AC2-no-files: editFiles with no 'files' key in tool_input -> {} (pass-through)."""
        _, output = _run_hook({
            "tool_name": "editFiles",
            "tool_input": {"content": "some content"},
        })
        assert output == {}, (
            f"editFiles with no 'files' key must return {{}} (pass-through), got: {output!r}."
        )

    # --- AC2-bslash: backslash path normalization ---

    def test_editfiles_backslash_path_normalized_and_denied(self) -> None:
        r"""AC2-bslash: editFiles files=["serve\foo.py"] normalized to serve/ -> denied."""
        _, output = _run_hook({
            "tool_name": "editFiles",
            "tool_input": {"files": ["serve\\mcp-kanban\\server.py"]},
        })
        assert _is_denied(output), (
            r"editFiles with backslash serve\ path must be denied after normalization, "
            f"got: {output!r}."
        )

    # --- AC2-dotslash: ./ prefix stripping ---

    def test_editfiles_dot_slash_path_stripped_and_denied(self) -> None:
        """AC2-dotslash: editFiles files=["./serve/foo.py"] stripped to serve/ -> denied."""
        _, output = _run_hook({
            "tool_name": "editFiles",
            "tool_input": {"files": ["./serve/mcp-kanban/server.py"]},
        })
        assert _is_denied(output), (
            f"editFiles with ./serve/ path must be denied after ./ stripping, got: {output!r}."
        )

    # --- AC2-camel: camelCase tool_name is gated ---

    def test_editfiles_camelcase_tool_name_is_gated(self) -> None:
        """AC2-camel: tool_name="editFiles" (camelCase) must trigger the path guard."""
        _, output = _run_hook({
            "tool_name": "editFiles",
            "tool_input": {"files": ["serve/mcp-kanban/server.py"]},
        })
        assert _is_denied(output), (
            f"tool_name='editFiles' (camelCase) must be gated; got: {output!r}. "
            "Builder must use exact camelCase string 'editFiles' in the write-tools array."
        )

    # --- AC2-lower: wrong case passes through (exact match only) ---

    def test_editfiles_lowercase_tool_name_not_gated(self) -> None:
        """AC2-lower: tool_name="editfiles" (lowercase) passes through -- exact match only."""
        _, output = _run_hook({
            "tool_name": "editfiles",
            "tool_input": {"files": ["serve/mcp-kanban/server.py"]},
        })
        assert output == {}, (
            f"tool_name='editfiles' (wrong case) must pass through (exact-match gate), "
            f"got: {output!r}."
        )


# ---------------------------------------------------------------------------
# AC3 -- edit/editFiles re-added to doc-writer.agent.md tools list
# ---------------------------------------------------------------------------


class TestFromAC_DocWriterEditFilesToolEntry:
    """edit/editFiles must be re-added to doc-writer.agent.md tools list after #591 (AC3)."""

    def _frontmatter(self) -> str:
        assert _AGENT_PATH.exists(), f"doc-writer.agent.md not found at {_AGENT_PATH}"
        import re  # noqa: PLC0415
        content = _AGENT_PATH.read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        assert match is not None, "No valid YAML frontmatter in doc-writer.agent.md"
        return match.group(1)

    def test_tools_list_contains_edit_slash_editfiles(self) -> None:
        """AC3: edit/editFiles must be present in doc-writer.agent.md tools list.

        This test also requires that hooks: is present in frontmatter -- verifying
        that #591 has been completed (added hooks, removed editFiles) and that #638
        has since re-added it. A hooks: section without editFiles is RED for #638.
        """
        fm = self._frontmatter()
        # Prerequisite: #591 must be complete (hooks section must exist)
        assert "hooks:" in fm, (
            "doc-writer.agent.md is missing the 'hooks:' section. "
            "#591 must be completed (hooks added, editFiles removed) before "
            "#638 can re-add it."
        )
        # AC3: editFiles must be re-added by #638 builder
        assert "edit/editFiles" in fm, (
            "doc-writer.agent.md tools list must contain 'edit/editFiles'. "
            "Builder must re-add it after #591 removed it (AC3)."
        )
