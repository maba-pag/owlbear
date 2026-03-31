"""Failing tests for task #134: validate_agents.py pre-commit hook.

Covers:
  - AC1: scripts/validate_agents.py reads agents/*.agent.md frontmatter,
         fails if tools: contains bare todo (not todos)
  - AC2: Script also fails if resolveMemoryFileUri appears anywhere in any
         agent file
  - AC3: repo: local hook added to .pre-commit-config.yaml with
         id: validate-agents and files: ^agents/.*\\.agent\\.md$
  - AC4: Script exits 0 on all current HEAD agent files
  - AC5: Hook runs in less than 1s
  - AC6: README has a brief note about the hook and the VS Code auto-staging
         trap

All tests fail on current HEAD because scripts/validate_agents.py does not
exist yet.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Import target — will raise ModuleNotFoundError until script exists (RED)
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from validate_agents import validate_agent  # noqa: E402  # type: ignore[import]

# ---------------------------------------------------------------------------
# Repo-level paths — resolved relative to this test file
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).parent.parent
_SCRIPT = _SCRIPTS_DIR / "validate_agents.py"
_AGENTS_DIR = _REPO_ROOT / "agents"
_PRECOMMIT_CONFIG = _REPO_ROOT / ".pre-commit-config.yaml"
_README = _REPO_ROOT / "README.md"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _write_agent(agent_file: Path, content: str) -> None:
    """Write full content to an agent file path, creating parents as needed."""
    agent_file.parent.mkdir(parents=True, exist_ok=True)
    agent_file.write_text(content, encoding="utf-8")


def _agent_content(frontmatter: str, body: str = "# Body\n") -> str:
    """Produce a well-formed agent.md file string with YAML frontmatter."""
    return f"---\n{frontmatter}\n---\n\n{body}"


# ---------------------------------------------------------------------------
# TestFromAC_ValidateAgentsTodoCheck
# ---------------------------------------------------------------------------
class TestFromAC_ValidateAgentsTodoCheck:
    """AC1: validate_agents detects bare 'todo' on tools: line and reports errors."""

    # --- Happy paths ---

    def test_no_tools_field_passes(self, tmp_path: Path) -> None:
        """AC1: agent file with no tools: field at all returns no errors."""
        agent_file = tmp_path / "no-tools.agent.md"
        _write_agent(
            agent_file,
            _agent_content("name: no-tools\ndescription: Agent without tools."),
        )
        assert validate_agent(agent_file) == []

    # --- Error paths ---

    def test_bare_todo_in_tools_fails(self, tmp_path: Path) -> None:
        """AC1: tools: [todo, read/readFile] returns at least one error."""
        agent_file = tmp_path / "bad-todo.agent.md"
        _write_agent(
            agent_file,
            _agent_content("name: bad-todo\ntools: [todo, read/readFile]"),
        )
        errors = validate_agent(agent_file)
        assert errors, "Expected errors for bare 'todo' in tools:"

    def test_bare_todo_alone_in_tools_fails(self, tmp_path: Path) -> None:
        """AC1: tools: [todo] (bare, alone) returns at least one error."""
        agent_file = tmp_path / "todo-only.agent.md"
        _write_agent(
            agent_file,
            _agent_content("name: todo-only\ntools: [todo]"),
        )
        errors = validate_agent(agent_file)
        assert errors, "Expected errors for tools: [todo]"

    def test_todo_mixed_with_todos_still_fails(self, tmp_path: Path) -> None:
        """AC1: tools: [todos, todo] (both present) still returns errors."""
        agent_file = tmp_path / "mixed.agent.md"
        _write_agent(
            agent_file,
            _agent_content("name: mixed\ntools: [todos, todo, vscode/memory]"),
        )
        errors = validate_agent(agent_file)
        assert errors, "Expected errors when bare 'todo' present alongside 'todos'"

    # --- Boundary / precision ---

    def test_todo_prefix_substring_does_not_trigger(self, tmp_path: Path) -> None:
        """AC1: 'todo_extra' is not bare todo — word boundary \\btodo\\b must be used.

        '_' is a word character in Python regex, so 'todo_extra' does not match
        \\btodo\\b. An implementation using a plain 'todo' substring would fail this.

        Note: only the bare-todo ban check is scoped here. 'todo_extra' is not a
        valid VS Code built-in or MCP pattern — a separate unknown-tool check (#198)
        may produce errors for it. This test asserts only that NO bare-todo ban error
        fires, not that the errors list is empty.
        """
        agent_file = tmp_path / "substr.agent.md"
        _write_agent(
            agent_file,
            _agent_content("name: substr\ntools: [read/readFile, todo_extra]"),
        )
        errors = validate_agent(agent_file)
        bare_todo_errors = [e for e in errors if "bare 'todo'" in e or "bare todo" in e.lower()]
        assert not bare_todo_errors, (
            f"'todo_extra' should not trigger the bare-todo ban check; got: {bare_todo_errors}"
        )

    def test_argument_hint_with_todos_does_not_trigger(self, tmp_path: Path) -> None:
        """AC1: 'todos' in argument-hint does not trigger failure.

        The check applies only to the tools: line, not all frontmatter.
        planner.agent.md contains 'status:todos' in argument-hint — this must
        not be a false positive.
        """
        agent_file = tmp_path / "planner-like.agent.md"
        _write_agent(
            agent_file,
            _agent_content(
                "name: planner-like\n"
                "argument-hint: 'Orchestrate: {status:todos}'\n"
                "tools: [read/readFile]",
            ),
        )
        assert validate_agent(agent_file) == []


# ---------------------------------------------------------------------------
# TestFromAC_ValidateAgentsResolveCheck
# ---------------------------------------------------------------------------
class TestFromAC_ValidateAgentsResolveCheck:
    """AC2: validate_agents fails if resolveMemoryFileUri appears anywhere in file."""

    # --- Happy path ---

    def test_no_resolve_uri_passes(self, tmp_path: Path) -> None:
        """AC2: file without resolveMemoryFileUri returns no errors."""
        agent_file = tmp_path / "clean.agent.md"
        _write_agent(
            agent_file,
            _agent_content("name: clean\ntools: [read/readFile]"),
        )
        assert validate_agent(agent_file) == []

    # --- Error paths ---

    def test_resolve_uri_in_tools_line_fails(self, tmp_path: Path) -> None:
        """AC2: resolveMemoryFileUri in tools: list triggers failure."""
        agent_file = tmp_path / "bad-tools.agent.md"
        _write_agent(
            agent_file,
            _agent_content(
                "name: bad-tools\ntools: [todos, resolveMemoryFileUri]",
            ),
        )
        errors = validate_agent(agent_file)
        assert errors, "Expected errors for resolveMemoryFileUri in tools:"

    def test_resolve_uri_in_body_fails(self, tmp_path: Path) -> None:
        """AC2: resolveMemoryFileUri in markdown body (not frontmatter) triggers failure."""
        agent_file = tmp_path / "bad-body.agent.md"
        _write_agent(
            agent_file,
            _agent_content(
                "name: bad-body\ntools: [todos]",
                body="Call resolveMemoryFileUri to load memory files.\n",
            ),
        )
        errors = validate_agent(agent_file)
        assert errors, "Expected errors for resolveMemoryFileUri in file body"

    def test_resolve_uri_in_frontmatter_description_fails(
        self, tmp_path: Path
    ) -> None:
        """AC2: resolveMemoryFileUri in any frontmatter field value triggers failure."""
        agent_file = tmp_path / "bad-fm.agent.md"
        _write_agent(
            agent_file,
            _agent_content(
                "name: bad-fm\n"
                "tools: [todos]\n"
                "description: 'Uses resolveMemoryFileUri internally'"
            ),
        )
        errors = validate_agent(agent_file)
        assert errors, "Expected errors for resolveMemoryFileUri in description field"


# ---------------------------------------------------------------------------
# TestFromAC_ValidateAgentsPreCommitHook
# ---------------------------------------------------------------------------
class TestFromAC_ValidateAgentsPreCommitHook:
    """AC3: .pre-commit-config.yaml has a repo: local hook id: validate-agents."""

    def _precommit_text(self) -> str:
        return _PRECOMMIT_CONFIG.read_text(encoding="utf-8")

    def test_validate_agents_hook_id_present(self) -> None:
        """AC3: id: validate-agents line exists in .pre-commit-config.yaml."""
        content = self._precommit_text()
        assert "validate-agents" in content, (
            "No 'validate-agents' hook id found in .pre-commit-config.yaml"
        )

    def test_validate_agents_files_pattern_present(self) -> None:
        r"""AC3: files: ^agents/.*\.agent\.md$ pattern exists in config."""
        content = self._precommit_text()
        assert r"^agents/.*\.agent\.md$" in content, (
            r"Expected 'files: ^agents/.*\.agent\.md$' in .pre-commit-config.yaml"
        )

    def test_validate_agents_under_local_repo(self) -> None:
        """AC3: the validate-agents hook is inside a 'repo: local' block."""
        content = self._precommit_text()
        local_pos = content.find("repo: local")
        assert local_pos != -1, "'repo: local' not found in .pre-commit-config.yaml"
        # Everything from the first 'repo: local' onwards should contain the hook
        local_section = content[local_pos:]
        assert "validate-agents" in local_section, (
            "'validate-agents' hook is not inside a 'repo: local' block"
        )


# ---------------------------------------------------------------------------
# TestFromAC_ValidateAgentsIntegration
# ---------------------------------------------------------------------------
class TestFromAC_ValidateAgentsIntegration:
    """AC4 & AC5: script exits 0 on all current agent files, completes in < 1s."""

    def test_script_exits_zero_on_current_agents(self) -> None:
        """AC4: validate_agents.py exits 0 when run against all current agents/*.agent.md."""
        agent_files = sorted(_AGENTS_DIR.glob("*.agent.md"))
        assert agent_files, f"No *.agent.md files found in {_AGENTS_DIR}"
        result = subprocess.run(
            [sys.executable, str(_SCRIPT), *[str(f) for f in agent_files]],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"validate_agents.py exited {result.returncode} on current agent files.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_script_completes_under_one_second(self) -> None:
        """AC5: validate_agents.py on all current agent files completes in < 1s."""
        agent_files = sorted(_AGENTS_DIR.glob("*.agent.md"))
        assert agent_files, f"No *.agent.md files found in {_AGENTS_DIR}"
        start = time.monotonic()
        subprocess.run(
            [sys.executable, str(_SCRIPT), *[str(f) for f in agent_files]],
            capture_output=True,
        )
        elapsed = time.monotonic() - start
        assert elapsed < 1.0, (
            f"validate_agents.py took {elapsed:.2f}s for {len(agent_files)} files "
            f"(limit: 1.0s)"
        )


# ---------------------------------------------------------------------------
# TestFromAC_ValidateAgentsReadme
# ---------------------------------------------------------------------------
class TestFromAC_ValidateAgentsReadme:
    """AC6: README.md has a note about the validate-agents hook and auto-staging trap."""

    def _readme_text(self) -> str:
        return _README.read_text(encoding="utf-8")

    def test_readme_mentions_validate_agents_hook(self) -> None:
        """AC6: README references the validate-agents hook."""
        content = self._readme_text()
        assert "validate-agents" in content, (
            "README.md does not mention the validate-agents hook"
        )

    def test_readme_mentions_auto_staging_trap(self) -> None:
        """AC6: README mentions the VS Code auto-staging trap."""
        content = self._readme_text()
        content_lower = content.lower()
        assert "auto-staging" in content_lower or "auto-stage" in content_lower, (
            "README.md does not mention the VS Code auto-staging trap"
        )


# ---------------------------------------------------------------------------
# TestFromAC_BanTodosToolCheck  (#193)
# ---------------------------------------------------------------------------
class TestFromAC_BanTodosToolCheck:
    """AC #193: validate_agents flags 'todos' on the tools: frontmatter line.

    The todos/manage_todo_list tool does not function in subagent context and
    must be banned from all agent definitions.  The check is scoped to the
    tools: block only — mentions in argument-hint or body must not be flagged.
    """

    def test_todos_in_tools_line_produces_error(self, tmp_path: Path) -> None:
        """#193-AC1: tools: [todos] returns at least one validation error."""
        agent_file = tmp_path / "todos-in-tools.agent.md"
        _write_agent(
            agent_file,
            _agent_content("name: todos-agent\ntools: [todos]"),
        )
        errors = validate_agent(agent_file)
        assert errors, "Expected an error for 'todos' in tools: line"

    def test_todos_error_mentions_disabled_for_subagents(self, tmp_path: Path) -> None:
        """#193-AC1: error message for 'todos' in tools: states the tool is disabled for subagents."""
        agent_file = tmp_path / "todos-in-tools.agent.md"
        _write_agent(
            agent_file,
            _agent_content("name: todos-agent\ntools: [todos]"),
        )
        errors = validate_agent(agent_file)
        assert errors, "Expected a non-empty error list"
        combined = " ".join(errors).lower()
        assert "disabled" in combined, (
            f"Expected error message to mention 'disabled'; got: {errors}"
        )

    def test_todos_with_other_tools_still_errors(self, tmp_path: Path) -> None:
        """#193-AC1: tools: [todos, read/readFile] still produces an error."""
        agent_file = tmp_path / "todos-mixed.agent.md"
        _write_agent(
            agent_file,
            _agent_content("name: todos-mixed\ntools: [todos, read/readFile]"),
        )
        errors = validate_agent(agent_file)
        assert errors, "Expected an error even when todos is mixed with other tools"


# ---------------------------------------------------------------------------
# TestFromAC_BanManageTodoListCheck  (#193)
# ---------------------------------------------------------------------------
class TestFromAC_BanManageTodoListCheck:
    """AC #193: validate_agents flags 'manage_todo_list' anywhere in the file.

    Full-file scope — frontmatter, body, anywhere.  Same pattern as the
    existing resolveMemoryFileUri check.
    """

    def test_manage_todo_list_in_tools_line_produces_error(self, tmp_path: Path) -> None:
        """#193-AC2: manage_todo_list in tools: list returns at least one error."""
        agent_file = tmp_path / "mtl-tools.agent.md"
        _write_agent(
            agent_file,
            _agent_content("name: mtl-agent\ntools: [manage_todo_list]"),
        )
        errors = validate_agent(agent_file)
        assert errors, "Expected an error for 'manage_todo_list' in tools:"

    def test_manage_todo_list_in_body_produces_error(self, tmp_path: Path) -> None:
        """#193-AC2 (AC-mandated scenario): manage_todo_list in markdown body returns error."""
        agent_file = tmp_path / "mtl-body.agent.md"
        _write_agent(
            agent_file,
            _agent_content(
                "name: mtl-body\ntools: [read/readFile]",
                body="Use manage_todo_list to track progress.\n",
            ),
        )
        errors = validate_agent(agent_file)
        assert errors, "Expected an error for 'manage_todo_list' in file body"

    def test_manage_todo_list_in_frontmatter_produces_error(self, tmp_path: Path) -> None:
        """#193-AC2: manage_todo_list in frontmatter description field returns error."""
        agent_file = tmp_path / "mtl-fm.agent.md"
        _write_agent(
            agent_file,
            _agent_content(
                "name: mtl-fm\n"
                "description: 'Calls manage_todo_list internally'\n"
                "tools: [read/readFile]",
            ),
        )
        errors = validate_agent(agent_file)
        assert errors, "Expected an error for 'manage_todo_list' in frontmatter"

    def test_manage_todo_list_error_mentions_disabled(self, tmp_path: Path) -> None:
        """#193-AC2: error message for manage_todo_list states the tool is disabled."""
        agent_file = tmp_path / "mtl-msg.agent.md"
        _write_agent(
            agent_file,
            _agent_content(
                "name: mtl-msg\ntools: [read/readFile]",
                body="manage_todo_list is used here.\n",
            ),
        )
        errors = validate_agent(agent_file)
        assert errors, "Expected a non-empty error list"
        combined = " ".join(errors).lower()
        assert "disabled" in combined, (
            f"Expected error message to mention 'disabled'; got: {errors}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_DeprecatedTodoMessage  (#193)
# ---------------------------------------------------------------------------
class TestFromAC_DeprecatedTodoMessage:
    """AC #193: bare 'todo' check message updated to reflect disabled status.

    The existing bare-todo error message says 'should be todos' — this must be
    updated to state that the tool itself is disabled for subagents.
    """

    def test_bare_todo_error_message_not_says_should_be_todos(self, tmp_path: Path) -> None:
        """#193-AC3: bare 'todo' error message no longer says 'should be todos'."""
        agent_file = tmp_path / "bare-todo.agent.md"
        _write_agent(
            agent_file,
            _agent_content("name: bare-todo\ntools: [todo]"),
        )
        errors = validate_agent(agent_file)
        assert errors, "Expected at least one error for bare 'todo' in tools:"
        combined = " ".join(errors).lower()
        assert "should be" not in combined, (
            f"Error message still says 'should be' (old phrasing); got: {errors}"
        )

    def test_bare_todo_error_message_says_disabled_for_subagents(
        self, tmp_path: Path
    ) -> None:
        """#193-AC3: bare 'todo' error message states the tool is disabled for subagents."""
        agent_file = tmp_path / "bare-todo-msg.agent.md"
        _write_agent(
            agent_file,
            _agent_content("name: bare-todo-msg\ntools: [todo]"),
        )
        errors = validate_agent(agent_file)
        assert errors, "Expected a non-empty error list"
        combined = " ".join(errors).lower()
        assert "disabled" in combined, (
            f"Expected error message to mention 'disabled'; got: {errors}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_CopilotInstructionsCleanup  (#193)
# ---------------------------------------------------------------------------
_COPILOT_INSTRUCTIONS = _REPO_ROOT / ".github" / "copilot-instructions.md"


class TestFromAC_CopilotInstructionsCleanup:
    """AC #193: manage_todo_list process-habit line removed from copilot-instructions."""

    def test_manage_todo_list_not_in_copilot_instructions(self) -> None:
        """#193-AC4: .github/copilot-instructions.md does not reference manage_todo_list."""
        content = _COPILOT_INSTRUCTIONS.read_text(encoding="utf-8")
        assert "manage_todo_list" not in content, (
            "Found 'manage_todo_list' in .github/copilot-instructions.md — "
            "the process-habit line must be removed"
        )


# ---------------------------------------------------------------------------
# TestFromAC_KnownToolsConstants  (#198)
# ---------------------------------------------------------------------------


class TestFromAC_KnownToolsConstants:
    """#198 AC1-3: KNOWN_TOOLSETS and KNOWN_STANDALONE_TOOLS constants exist and are correct."""

    # --- KNOWN_TOOLSETS ---

    def test_known_toolsets_is_importable_and_frozenset(self) -> None:
        """AC1: KNOWN_TOOLSETS can be imported from validate_agents and is a frozenset."""
        from validate_agents import KNOWN_TOOLSETS

        assert isinstance(KNOWN_TOOLSETS, frozenset), (
            f"KNOWN_TOOLSETS must be a frozenset, got {type(KNOWN_TOOLSETS)}"
        )

    def test_known_toolsets_contains_all_8_prefixes(self) -> None:
        """AC1: KNOWN_TOOLSETS contains all 8 VS Code built-in toolset prefixes."""
        from validate_agents import KNOWN_TOOLSETS

        expected = frozenset(
            {"agent", "browser", "edit", "execute", "read", "search", "web", "vscode"}
        )
        missing = expected - KNOWN_TOOLSETS
        assert not missing, f"KNOWN_TOOLSETS is missing prefixes: {missing}"

    def test_known_toolsets_does_not_contain_arbitrary_strings(self) -> None:
        """AC1 boundary: KNOWN_TOOLSETS does not contain known-invalid names."""
        from validate_agents import KNOWN_TOOLSETS

        assert "fly_to_moon" not in KNOWN_TOOLSETS
        assert "foo" not in KNOWN_TOOLSETS

    # --- KNOWN_STANDALONE_TOOLS ---

    def test_known_standalone_tools_is_importable_and_frozenset(self) -> None:
        """AC2: KNOWN_STANDALONE_TOOLS can be imported and is a frozenset."""
        from validate_agents import KNOWN_STANDALONE_TOOLS

        assert isinstance(KNOWN_STANDALONE_TOOLS, frozenset), (
            f"KNOWN_STANDALONE_TOOLS must be a frozenset, got {type(KNOWN_STANDALONE_TOOLS)}"
        )

    def test_known_standalone_tools_contains_new_workspace(self) -> None:
        """AC2: 'newWorkspace' is in KNOWN_STANDALONE_TOOLS."""
        from validate_agents import KNOWN_STANDALONE_TOOLS

        assert "newWorkspace" in KNOWN_STANDALONE_TOOLS, (
            "'newWorkspace' missing from KNOWN_STANDALONE_TOOLS"
        )

    def test_known_standalone_tools_contains_selection(self) -> None:
        """AC2: 'selection' is in KNOWN_STANDALONE_TOOLS."""
        from validate_agents import KNOWN_STANDALONE_TOOLS

        assert "selection" in KNOWN_STANDALONE_TOOLS, (
            "'selection' missing from KNOWN_STANDALONE_TOOLS"
        )


# ---------------------------------------------------------------------------
# TestFromAC_CheckUnknownToolsHelper  (#198)
# ---------------------------------------------------------------------------


class TestFromAC_CheckUnknownToolsHelper:
    """#198 AC4: _check_unknown_tools() helper is importable and callable."""

    def test_check_unknown_tools_is_importable_and_callable(self) -> None:
        """AC4: _check_unknown_tools can be imported from validate_agents and is a callable."""
        from validate_agents import _check_unknown_tools

        assert callable(_check_unknown_tools), "_check_unknown_tools must be callable"


# ---------------------------------------------------------------------------
# TestFromAC_UnknownToolErrors  (#198)
# ---------------------------------------------------------------------------


class TestFromAC_UnknownToolErrors:
    """#198 AC5: unrecognized tool names produce validation errors."""

    def test_hallucinated_tool_name_produces_error(self, tmp_path: Path) -> None:
        """AC5: tool 'fly_to_moon' (not in any registry category) produces an error."""
        agent_file = tmp_path / "hallucinated.agent.md"
        _write_agent(agent_file, _agent_content("name: hallucinated\ntools: [fly_to_moon]"))
        errors = validate_agent(agent_file)
        assert errors, "Expected error for unknown tool 'fly_to_moon'"

    def test_unknown_prefix_tool_produces_error(self, tmp_path: Path) -> None:
        """AC5: tool 'foo/bar' (prefix 'foo' not in KNOWN_TOOLSETS) produces error."""
        agent_file = tmp_path / "bad-prefix.agent.md"
        _write_agent(agent_file, _agent_content("name: bad-prefix\ntools: [foo/bar]"))
        errors = validate_agent(agent_file)
        assert errors, "Expected error for tool 'foo/bar' (unknown prefix 'foo')"

    def test_typo_toolset_prefix_produces_error(self, tmp_path: Path) -> None:
        """AC5: misspelled prefix 'Seach/findFile' (not 'search') produces error."""
        agent_file = tmp_path / "typo.agent.md"
        _write_agent(agent_file, _agent_content("name: typo\ntools: [Seach/findFile]"))
        errors = validate_agent(agent_file)
        assert errors, "Expected error for typo tool name 'Seach/findFile'"

    def test_mcp_path_without_wildcard_and_unknown_prefix_produces_error(
        self, tmp_path: Path
    ) -> None:
        """AC5: 'someMCP/specificTool' (unknown prefix, no '/*') produces error."""
        agent_file = tmp_path / "no-wildcard.agent.md"
        _write_agent(
            agent_file, _agent_content("name: no-wildcard\ntools: [someMCP/specificTool]")
        )
        errors = validate_agent(agent_file)
        assert errors, "Expected error for 'someMCP/specificTool' (not a valid pattern)"

    def test_multiple_unknown_tools_each_produce_error(self, tmp_path: Path) -> None:
        """AC5 boundary: two unknown tools each produce their own error (two errors minimum)."""
        agent_file = tmp_path / "two-bad.agent.md"
        _write_agent(
            agent_file,
            _agent_content("name: two-bad\ntools: [ghost_tool, phantom_tool]"),
        )
        errors = validate_agent(agent_file)
        assert len(errors) >= 2, (
            f"Expected at least 2 errors for two unknown tools; got {len(errors)}: {errors}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_UnknownToolErrorMessage  (#198)
# ---------------------------------------------------------------------------


class TestFromAC_UnknownToolErrorMessage:
    """#198 AC6: error message for unknown tool matches the required format."""

    def test_error_message_includes_filename(self, tmp_path: Path) -> None:
        """AC6: error message includes the agent file path/name."""
        agent_file = tmp_path / "bad-msg.agent.md"
        _write_agent(agent_file, _agent_content("name: bad-msg\ntools: [ghost_tool]"))
        errors = validate_agent(agent_file)
        assert errors, "Expected at least one error"
        combined = "\n".join(errors)
        assert "bad-msg.agent.md" in combined, (
            f"Error message should include filename; got: {errors}"
        )

    def test_error_message_contains_unknown_tool_phrase(self, tmp_path: Path) -> None:
        """AC6: error message contains the phrase 'unknown tool'."""
        agent_file = tmp_path / "bad-phrase.agent.md"
        _write_agent(agent_file, _agent_content("name: bad-phrase\ntools: [ghost_tool]"))
        errors = validate_agent(agent_file)
        assert errors, "Expected at least one error"
        combined = "\n".join(errors)
        assert "unknown tool" in combined, (
            f"Error message should contain 'unknown tool'; got: {errors}"
        )

    def test_error_message_includes_specific_tool_name(self, tmp_path: Path) -> None:
        """AC6: error message includes the specific unknown tool name."""
        agent_file = tmp_path / "bad-toolname.agent.md"
        _write_agent(agent_file, _agent_content("name: bad-toolname\ntools: [phantom_tool]"))
        errors = validate_agent(agent_file)
        assert errors, "Expected at least one error"
        combined = "\n".join(errors)
        assert "phantom_tool" in combined, (
            f"Error should include tool name 'phantom_tool'; got: {errors}"
        )

    def test_error_message_says_not_a_recognized_pattern(self, tmp_path: Path) -> None:
        """AC6: error message contains 'not a recognized VS Code built-in or MCP server pattern'."""
        agent_file = tmp_path / "bad-recog.agent.md"
        _write_agent(agent_file, _agent_content("name: bad-recog\ntools: [ghost_tool]"))
        errors = validate_agent(agent_file)
        assert errors, "Expected at least one error"
        combined = "\n".join(errors)
        assert "not a recognized" in combined, (
            f"Error should contain 'not a recognized'; got: {errors}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_NoBannedToolDoubleError  (#198)
# ---------------------------------------------------------------------------


class TestFromAC_NoBannedToolDoubleError:
    """#198 AC7: banned tools are NOT also reported as unknown — no double errors.

    Each test uses _require_registry() to ensure the unknown-tool check exists before
    asserting no double-errors.  Tests fail in RED (AssertionError on missing helper)
    and guard the correctness constraint for the builder.
    """

    @staticmethod
    def _require_registry() -> None:
        """Fail clearly if _check_unknown_tools is not yet implemented (#198 builder step)."""
        import validate_agents as va

        if not hasattr(va, "_check_unknown_tools"):
            msg = "_check_unknown_tools not yet implemented — #198 builder step required"
            raise AssertionError(msg)

    def test_todos_banned_not_also_reported_as_unknown(self, tmp_path: Path) -> None:
        """AC7: 'todos' (banned #193) should not also produce an 'unknown tool' error."""
        self._require_registry()
        agent_file = tmp_path / "todos-no-double.agent.md"
        _write_agent(agent_file, _agent_content("name: todos-no-double\ntools: [todos]"))
        errors = validate_agent(agent_file)
        unknown_errors = [e for e in errors if "unknown tool" in e]
        assert not unknown_errors, (
            f"'todos' (banned) should not produce unknown-tool error; got: {unknown_errors}"
        )

    def test_manage_todo_list_not_also_reported_as_unknown(self, tmp_path: Path) -> None:
        """AC7: 'manage_todo_list' (banned #193) should not produce an 'unknown tool' error."""
        self._require_registry()
        agent_file = tmp_path / "mtl-no-double.agent.md"
        _write_agent(
            agent_file, _agent_content("name: mtl-no-double\ntools: [manage_todo_list]")
        )
        errors = validate_agent(agent_file)
        unknown_errors = [e for e in errors if "unknown tool" in e]
        assert not unknown_errors, (
            f"'manage_todo_list' (banned) should not produce unknown-tool error; got: {unknown_errors}"
        )

    def test_resolve_uri_not_also_reported_as_unknown(self, tmp_path: Path) -> None:
        """AC7: 'resolveMemoryFileUri' (banned original) should not produce an 'unknown tool' error."""
        self._require_registry()
        agent_file = tmp_path / "uri-no-double.agent.md"
        _write_agent(
            agent_file,
            _agent_content("name: uri-no-double\ntools: [resolveMemoryFileUri]"),
        )
        errors = validate_agent(agent_file)
        unknown_errors = [e for e in errors if "unknown tool" in e]
        assert not unknown_errors, (
            f"'resolveMemoryFileUri' (banned) should not produce unknown-tool error; got: {unknown_errors}"
        )

    def test_mixed_banned_and_unknown_only_unknown_gets_unknown_error(
        self, tmp_path: Path
    ) -> None:
        """AC7 edge: file with banned + unknown tool — only the unknown gets an unknown-tool error."""
        self._require_registry()
        agent_file = tmp_path / "mixed-bad.agent.md"
        _write_agent(
            agent_file,
            _agent_content("name: mixed-bad\ntools: [todos, ghost_tool]"),
        )
        errors = validate_agent(agent_file)
        unknown_errors = [e for e in errors if "unknown tool" in e]
        ghost_flagged = any("ghost_tool" in e for e in unknown_errors)
        todos_flagged = any("todos" in e for e in unknown_errors)
        assert ghost_flagged, (
            f"Expected 'ghost_tool' to produce an unknown-tool error; got: {errors}"
        )
        assert not todos_flagged, (
            f"'todos' (banned) should not produce unknown-tool error; got: {unknown_errors}"
        )
