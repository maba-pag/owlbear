"""Tests for task #590: Add SessionStart context injection hook to pipeline agents (Phase 4).

Contract-level tests for:
1. scripts/hooks/session-context.ps1 — reads stdin JSON, extracts git context, outputs additionalContext
2. share/agents/builder.agent.md — SessionStart hook added alongside existing PostToolUse
3. share/agents/test-writer.agent.md — hooks: section with SessionStart
4. share/agents/doc-writer.agent.md — hooks: section with SessionStart

SessionStart stdin JSON format (VS Code hooks spec):
  { "source": "new", "cwd": "...", ... }  (any valid JSON; script handles gracefully)

Expected output format (AC2):
  {
    "hookSpecificOutput": {
      "hookEventName": "SessionStart",
      "additionalContext": "Branch: <name> | Commits: <hash1> <subj1> | <hash2> <subj2> | <hash3> <subj3>"
    }
  }
  — pipe-separated, abbreviated hashes (not full 40-char SHA), max 3 commits

AC coverage:
  AC1a: session-context.ps1 exists at scripts/hooks/session-context.ps1
  AC1b: script is non-empty
  AC2a: happy-path output has hookSpecificOutput key
  AC2b: hookSpecificOutput.hookEventName == "SessionStart"
  AC2c: additionalContext starts with "Branch: "
  AC2d: additionalContext contains " | Commits: " separator
  AC2e: commit hashes are abbreviated (not full 40-char SHA)
  AC2f: at most 3 commits in additionalContext (Boundary1)
  AC2g: commit entries are non-empty pipe-separated strings (Boundary2)
  AC2h: stdout is always valid JSON (no plaintext noise)
  AC3a: builder.agent.md has SessionStart in hooks: section
  AC3b: builder.agent.md SessionStart command references session-context.ps1
  AC3c: builder.agent.md SessionStart hook has type: command
  AC3d: test-writer.agent.md has SessionStart in hooks: section
  AC3e: test-writer.agent.md SessionStart command references session-context.ps1
  AC3f: test-writer.agent.md SessionStart hook has type: command
  AC3g: doc-writer.agent.md has SessionStart in hooks: section
  AC3h: doc-writer.agent.md SessionStart command references session-context.ps1
  AC3i: doc-writer.agent.md SessionStart hook has type: command
  AC4a: builder.agent.md hooks: section has both SessionStart (new) and PostToolUse (preserved)
  AC4b: test-writer.agent.md has hooks: section (new or updated from #589)
  AC4c: doc-writer.agent.md has hooks: section (new)
  AC5a: malformed stdin JSON → {}
  AC5b: empty stdin → {}
  AC5c: non-git directory → {}
  AC6:  script executes in under 5 seconds
  AC7a: builder.agent.md frontmatter parses as valid YAML with no duplicate keys
  AC7b: test-writer.agent.md frontmatter parses as valid YAML with no duplicate keys
  AC7c: doc-writer.agent.md frontmatter parses as valid YAML with no duplicate keys
  Boundary3: abbreviated hashes are < 20 chars (not full 40-char SHA)
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from time import monotonic

import pytest

_REPO_ROOT = Path(__file__).parent.parent
_SCRIPT_PATH = _REPO_ROOT / ".owlbear" / "hooks" / "session-context.ps1"
_BUILDER_AGENT = _REPO_ROOT / "share" / "agents" / "builder.agent.md"
_TEST_WRITER_AGENT = _REPO_ROOT / "share" / "agents" / "test-writer.agent.md"
_DOC_WRITER_AGENT = _REPO_ROOT / "share" / "agents" / "doc-writer.agent.md"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_context_hook(
    stdin_data: dict,
    *,
    timeout: int = 30,
    cwd: Path | None = None,
) -> tuple[int, dict]:
    """Run session-context.ps1 with the given stdin JSON.

    Returns (exit_code, parsed_stdout_json).
    Raises FileNotFoundError if the script does not yet exist — makes
    RED-phase failures explicit rather than silently returning {}.
    """
    if not _SCRIPT_PATH.exists():
        msg = (
            f"session-context.ps1 not found at {_SCRIPT_PATH}. "
            "Builder must create scripts/hooks/session-context.ps1 to make these tests pass."
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
        cwd=cwd,
    )
    stdout = result.stdout.strip()
    try:
        output = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError:
        output = {"_raw": stdout}
    return result.returncode, output


def _extract_frontmatter(content: str, agent_name: str = "agent") -> str:
    """Return the YAML text between the first --- ... --- block."""
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    assert match is not None, (
        f"No valid YAML frontmatter (--- ... ---) found in {agent_name}.agent.md"
    )
    return match.group(1)


def _parse_commit_entries(additional_context: str) -> list[str]:
    """Extract the list of commit strings from an additionalContext value.

    Given: "Branch: main | Commits: abc1234 Fix X | def5678 Add Y"
    Returns: ["abc1234 Fix X", "def5678 Add Y"]
    """
    commits_marker = " | Commits: "
    if commits_marker not in additional_context:
        return []
    commits_part = additional_context.split(commits_marker, 1)[1]
    return [entry for entry in commits_part.split(" | ") if entry.strip()]


# ---------------------------------------------------------------------------
# Script existence — fails RED until builder creates the file (AC1)
# ---------------------------------------------------------------------------


class TestFromAC_ScriptExists:
    """AC1: session-context.ps1 must be created at scripts/hooks/session-context.ps1."""

    def test_session_context_ps1_exists(self) -> None:
        """AC1a: session-context.ps1 must exist at the expected path."""
        assert _SCRIPT_PATH.exists(), (
            f"session-context.ps1 not found at {_SCRIPT_PATH}. "
            "Builder must create scripts/hooks/session-context.ps1."
        )

    def test_script_is_nonempty(self) -> None:
        """AC1b: script file must have content — an empty file cannot implement context injection."""
        assert _SCRIPT_PATH.exists(), (
            f"session-context.ps1 not found at {_SCRIPT_PATH}."
        )
        assert _SCRIPT_PATH.stat().st_size > 0, (
            "session-context.ps1 exists but is empty — builder must implement it."
        )


# ---------------------------------------------------------------------------
# Output format (AC2) — Windows/PowerShell required
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell hook requires Windows")
class TestFromAC_OutputFormat:
    """AC2: script must output hookSpecificOutput with SessionStart context."""

    def test_output_has_hook_specific_output_key(self) -> None:
        """AC2a: happy-path output must contain a hookSpecificOutput key."""
        _, output = _run_context_hook({})
        assert "hookSpecificOutput" in output, (
            f"Expected 'hookSpecificOutput' key in response, got: {output!r}"
        )

    def test_hook_event_name_is_session_start(self) -> None:
        """AC2b: hookSpecificOutput.hookEventName must be 'SessionStart'."""
        _, output = _run_context_hook({})
        hook_out = output.get("hookSpecificOutput", {})
        assert hook_out.get("hookEventName") == "SessionStart", (
            f"hookEventName must be 'SessionStart', got: {hook_out!r}"
        )

    def test_additional_context_has_branch_prefix(self) -> None:
        """AC2c: additionalContext must start with 'Branch: '."""
        _, output = _run_context_hook({})
        ctx = output.get("hookSpecificOutput", {}).get("additionalContext", "")
        assert ctx.startswith("Branch: "), (
            f"additionalContext must start with 'Branch: ', got: {ctx!r}"
        )

    def test_additional_context_has_commits_separator(self) -> None:
        """AC2d: additionalContext must contain ' | Commits: ' separator."""
        _, output = _run_context_hook({})
        ctx = output.get("hookSpecificOutput", {}).get("additionalContext", "")
        assert " | Commits: " in ctx, (
            f"additionalContext must contain ' | Commits: ' separator, got: {ctx!r}"
        )

    def test_commit_hashes_are_abbreviated(self) -> None:
        """AC2e/Boundary3: each commit hash must be abbreviated (not a full 40-char SHA)."""
        _, output = _run_context_hook({})
        ctx = output.get("hookSpecificOutput", {}).get("additionalContext", "")
        commit_entries = _parse_commit_entries(ctx)
        assert commit_entries, (
            f"No commit entries found in additionalContext to check hashes: {ctx!r}"
        )
        for entry in commit_entries:
            parts = entry.split()
            if not parts:
                continue
            hash_part = parts[0]
            assert len(hash_part) < 20, (
                f"Commit hash '{hash_part}' appears to be a full SHA-1 (len={len(hash_part)}). "
                f"AC2 requires abbreviated hashes from 'git log --oneline'."
            )

    def test_at_most_three_commits_in_output(self) -> None:
        """AC2f/Boundary1: additionalContext must contain at most 3 commit entries."""
        _, output = _run_context_hook({})
        ctx = output.get("hookSpecificOutput", {}).get("additionalContext", "")
        commit_entries = _parse_commit_entries(ctx)
        assert len(commit_entries) <= 3, (
            f"Expected at most 3 commit entries, got {len(commit_entries)}: {commit_entries!r}"
        )

    def test_commit_entries_are_nonempty(self) -> None:
        """AC2g/Boundary2: each pipe-separated commit entry must be non-empty."""
        _, output = _run_context_hook({})
        ctx = output.get("hookSpecificOutput", {}).get("additionalContext", "")
        commit_entries = _parse_commit_entries(ctx)
        assert commit_entries, (
            f"No commit entries parsed from additionalContext: {ctx!r}"
        )
        for entry in commit_entries:
            assert entry.strip(), (
                f"Empty commit entry found when splitting by ' | ' from: {ctx!r}"
            )

    def test_stdout_is_always_valid_json(self) -> None:
        """AC2h: stdout must always be a valid JSON object — no plaintext noise allowed."""
        if not _SCRIPT_PATH.exists():
            raise FileNotFoundError(
                f"session-context.ps1 not found at {_SCRIPT_PATH}."
            )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-File", str(_SCRIPT_PATH)],
            input=json.dumps({}),
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
                f"Script stdout is not valid JSON: {stdout!r}\nError: {exc}"
            )
        assert isinstance(parsed, dict), f"Output must be a JSON object, got: {parsed!r}"


# ---------------------------------------------------------------------------
# Error handling (AC5) — Windows/PowerShell required
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell hook requires Windows")
class TestFromAC_ErrorHandling:
    """AC5: script returns {} on any failure — non-blocking in all cases."""

    def test_malformed_stdin_json_returns_empty_json(self) -> None:
        """AC5a: malformed stdin JSON must not crash the script — returns {}."""
        if not _SCRIPT_PATH.exists():
            raise FileNotFoundError(
                f"session-context.ps1 not found at {_SCRIPT_PATH}."
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
            f"Malformed stdin JSON must produce {{}} output (non-blocking, AC5), got: {output!r}"
        )

    def test_empty_stdin_returns_empty_json(self) -> None:
        """AC5b: empty stdin must not crash the script — returns {}."""
        if not _SCRIPT_PATH.exists():
            raise FileNotFoundError(
                f"session-context.ps1 not found at {_SCRIPT_PATH}."
            )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-File", str(_SCRIPT_PATH)],
            input="",
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
            f"Empty stdin must produce {{}} output (non-blocking, AC5), got: {output!r}"
        )

    def test_non_git_directory_returns_empty_json(self, tmp_path: Path) -> None:
        """AC5c: script run from a non-git directory must return {} (git error, non-blocking)."""
        _, output = _run_context_hook({}, cwd=tmp_path)
        assert output == {}, (
            f"Non-git directory must produce {{}} output (non-blocking, AC5), got: {output!r}"
        )


# ---------------------------------------------------------------------------
# Performance (AC6) — Windows/PowerShell required
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell hook requires Windows")
class TestFromAC_Performance:
    """AC6: script must execute in under 5 seconds."""

    def test_script_executes_under_five_seconds(self) -> None:
        """AC6: session-context.ps1 must complete within 5 seconds (expected ~30ms per research §3.4)."""
        if not _SCRIPT_PATH.exists():
            raise FileNotFoundError(
                f"session-context.ps1 not found at {_SCRIPT_PATH}."
            )
        start = monotonic()
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-File", str(_SCRIPT_PATH)],
            input=json.dumps({}),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        elapsed = monotonic() - start
        assert elapsed < 5.0, (
            f"session-context.ps1 took {elapsed:.2f}s — exceeds 5-second limit (AC6). "
            f"Expected ~30ms (git branch + git log -3)."
        )


# ---------------------------------------------------------------------------
# Agent config — builder.agent.md (AC3, AC4, AC7)
# ---------------------------------------------------------------------------


class TestFromAC_BuilderAgentHooks:
    """builder.agent.md must gain SessionStart hook alongside existing PostToolUse (AC3, AC4, AC7)."""

    def _content(self) -> str:
        assert _BUILDER_AGENT.exists(), f"Agent file not found at {_BUILDER_AGENT}"
        return _BUILDER_AGENT.read_text(encoding="utf-8")

    def _frontmatter(self) -> str:
        return _extract_frontmatter(self._content(), "builder")

    def test_builder_has_session_start_hook(self) -> None:
        """AC3a: builder.agent.md hooks: section must contain SessionStart."""
        fm = self._frontmatter()
        assert "SessionStart" in fm, (
            "builder.agent.md is missing SessionStart in the hooks: section. "
            "Builder must add it alongside existing PostToolUse."
        )

    def test_builder_session_start_references_correct_script(self) -> None:
        """AC3b: builder.agent.md SessionStart command must reference session-context.ps1."""
        fm = self._frontmatter()
        assert "session-context.ps1" in fm, (
            "builder.agent.md hooks: section must reference 'session-context.ps1' "
            "in the SessionStart command."
        )

    def test_builder_session_start_hook_type_is_command(self) -> None:
        """AC3c: SessionStart hook must specify type: command."""
        fm = self._frontmatter()
        assert "SessionStart" in fm, (
            "builder.agent.md is missing SessionStart — type: command check is premature."
        )
        # type: command must appear in the frontmatter (also satisfied by PostToolUse, but
        # the YAML validity test below confirms it is nested under SessionStart)
        assert re.search(r"type:\s*command", fm), (
            "builder.agent.md SessionStart entry must specify 'type: command'."
        )

    def test_builder_hooks_section_has_both_events(self) -> None:
        """AC4a: hooks: must contain both SessionStart (new) and PostToolUse (must be preserved)."""
        import yaml  # noqa: PLC0415

        fm = self._frontmatter()
        try:
            parsed = yaml.safe_load(fm)
        except yaml.YAMLError as exc:
            pytest.fail(f"builder.agent.md frontmatter is not valid YAML: {exc}")
        hooks = parsed.get("hooks", {})
        assert "SessionStart" in hooks, (
            f"hooks: section must contain SessionStart (AC3). "
            f"Current hook events: {list(hooks.keys())!r}"
        )
        assert "PostToolUse" in hooks, (
            f"hooks: section must still contain PostToolUse (AC4 — must not be replaced). "
            f"Current hook events: {list(hooks.keys())!r}"
        )

    def test_builder_frontmatter_is_valid_yaml(self) -> None:
        """AC7a: builder.agent.md frontmatter must parse as valid YAML with SessionStart hook."""
        import yaml  # noqa: PLC0415

        fm = self._frontmatter()
        try:
            parsed = yaml.safe_load(fm)
        except yaml.YAMLError as exc:
            pytest.fail(f"builder.agent.md frontmatter is not valid YAML: {exc}")
        assert isinstance(parsed, dict), (
            f"Parsed YAML frontmatter must be a dict, got: {type(parsed)}"
        )
        hooks = parsed.get("hooks", {})
        assert "SessionStart" in hooks, (
            f"Frontmatter parsed but hooks: section missing SessionStart. "
            f"Got hooks events: {list(hooks.keys())!r}"
        )

    def test_builder_frontmatter_has_no_duplicate_keys(self) -> None:
        """AC7a regression: builder.agent.md frontmatter must not have duplicate YAML keys."""
        fm = self._frontmatter()
        assert "SessionStart" in fm, (
            "Builder must add SessionStart first — duplicate-key check is premature."
        )
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


# ---------------------------------------------------------------------------
# Agent config — test-writer.agent.md (AC3, AC4, AC7)
# ---------------------------------------------------------------------------


class TestFromAC_TestWriterAgentHooks:
    """test-writer.agent.md must have a hooks: section with SessionStart (AC3, AC4, AC7)."""

    def _content(self) -> str:
        assert _TEST_WRITER_AGENT.exists(), f"Agent file not found at {_TEST_WRITER_AGENT}"
        return _TEST_WRITER_AGENT.read_text(encoding="utf-8")

    def _frontmatter(self) -> str:
        return _extract_frontmatter(self._content(), "test-writer")

    def test_test_writer_has_hooks_section(self) -> None:
        """AC4b: test-writer.agent.md must have a hooks: section (new, or merged with #589)."""
        fm = self._frontmatter()
        assert re.search(r"^hooks:", fm, re.MULTILINE), (
            "test-writer.agent.md is missing the 'hooks:' key. "
            "Builder must add a hooks: section containing SessionStart."
        )

    def test_test_writer_has_session_start_hook(self) -> None:
        """AC3d: test-writer.agent.md hooks: section must contain SessionStart."""
        fm = self._frontmatter()
        assert "SessionStart" in fm, (
            "test-writer.agent.md hooks: section is missing SessionStart."
        )

    def test_test_writer_session_start_references_correct_script(self) -> None:
        """AC3e: test-writer.agent.md SessionStart command must reference session-context.ps1."""
        fm = self._frontmatter()
        assert "session-context.ps1" in fm, (
            "test-writer.agent.md SessionStart hook command must reference 'session-context.ps1'."
        )

    def test_test_writer_session_start_hook_type_is_command(self) -> None:
        """AC3f: test-writer.agent.md SessionStart hook must specify type: command."""
        fm = self._frontmatter()
        assert "SessionStart" in fm, (
            "test-writer.agent.md is missing SessionStart — type: command check is premature."
        )
        assert re.search(r"type:\s*command", fm), (
            "test-writer.agent.md SessionStart hook must specify 'type: command'."
        )

    def test_test_writer_frontmatter_is_valid_yaml(self) -> None:
        """AC7b: test-writer.agent.md frontmatter must parse as valid YAML with SessionStart."""
        import yaml  # noqa: PLC0415

        fm = self._frontmatter()
        try:
            parsed = yaml.safe_load(fm)
        except yaml.YAMLError as exc:
            pytest.fail(f"test-writer.agent.md frontmatter is not valid YAML: {exc}")
        assert isinstance(parsed, dict), (
            f"Parsed YAML frontmatter must be a dict, got: {type(parsed)}"
        )
        hooks = parsed.get("hooks", {})
        assert "SessionStart" in hooks, (
            f"Frontmatter parsed but hooks: section missing SessionStart. "
            f"Got hooks events: {list(hooks.keys())!r}"
        )

    def test_test_writer_frontmatter_has_no_duplicate_keys(self) -> None:
        """AC7b regression: test-writer.agent.md frontmatter must not have duplicate YAML keys."""
        fm = self._frontmatter()
        assert "SessionStart" in fm, (
            "Builder must add SessionStart first — duplicate-key check is premature."
        )
        top_level_keys = re.findall(r"^([a-zA-Z][a-zA-Z0-9_-]*):", fm, re.MULTILINE)
        seen: set[str] = set()
        duplicates: list[str] = []
        for key in top_level_keys:
            if key in seen:
                duplicates.append(key)
            seen.add(key)
        assert not duplicates, (
            f"Duplicate YAML keys found in test-writer.agent.md frontmatter: {duplicates}"
        )


# ---------------------------------------------------------------------------
# Agent config — doc-writer.agent.md (AC3, AC4, AC7)
# ---------------------------------------------------------------------------


class TestFromAC_DocWriterAgentHooks:
    """doc-writer.agent.md must gain a new hooks: section with SessionStart (AC3, AC4, AC7)."""

    def _content(self) -> str:
        assert _DOC_WRITER_AGENT.exists(), f"Agent file not found at {_DOC_WRITER_AGENT}"
        return _DOC_WRITER_AGENT.read_text(encoding="utf-8")

    def _frontmatter(self) -> str:
        return _extract_frontmatter(self._content(), "doc-writer")

    def test_doc_writer_has_hooks_section(self) -> None:
        """AC4c: doc-writer.agent.md must have a hooks: section."""
        fm = self._frontmatter()
        assert re.search(r"^hooks:", fm, re.MULTILINE), (
            "doc-writer.agent.md is missing the 'hooks:' key. "
            "Builder must add a new hooks: section containing SessionStart."
        )

    def test_doc_writer_has_session_start_hook(self) -> None:
        """AC3g: doc-writer.agent.md hooks: section must contain SessionStart."""
        fm = self._frontmatter()
        assert "SessionStart" in fm, (
            "doc-writer.agent.md hooks: section is missing SessionStart."
        )

    def test_doc_writer_session_start_references_correct_script(self) -> None:
        """AC3h: doc-writer.agent.md SessionStart command must reference session-context.ps1."""
        fm = self._frontmatter()
        assert "session-context.ps1" in fm, (
            "doc-writer.agent.md SessionStart hook command must reference 'session-context.ps1'."
        )

    def test_doc_writer_session_start_hook_type_is_command(self) -> None:
        """AC3i: doc-writer.agent.md SessionStart hook must specify type: command."""
        fm = self._frontmatter()
        assert "SessionStart" in fm, (
            "doc-writer.agent.md is missing SessionStart — type: command check is premature."
        )
        assert re.search(r"type:\s*command", fm), (
            "doc-writer.agent.md SessionStart hook must specify 'type: command'."
        )

    def test_doc_writer_frontmatter_is_valid_yaml(self) -> None:
        """AC7c: doc-writer.agent.md frontmatter must parse as valid YAML with SessionStart."""
        import yaml  # noqa: PLC0415

        fm = self._frontmatter()
        try:
            parsed = yaml.safe_load(fm)
        except yaml.YAMLError as exc:
            pytest.fail(f"doc-writer.agent.md frontmatter is not valid YAML: {exc}")
        assert isinstance(parsed, dict), (
            f"Parsed YAML frontmatter must be a dict, got: {type(parsed)}"
        )
        hooks = parsed.get("hooks", {})
        assert "SessionStart" in hooks, (
            f"Frontmatter parsed but hooks: section missing SessionStart. "
            f"Got hooks events: {list(hooks.keys())!r}"
        )

    def test_doc_writer_frontmatter_has_no_duplicate_keys(self) -> None:
        """AC7c regression: doc-writer.agent.md frontmatter must not have duplicate YAML keys."""
        fm = self._frontmatter()
        assert "SessionStart" in fm, (
            "Builder must add SessionStart first — duplicate-key check is premature."
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
