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

    def test_tools_todos_passes(self, tmp_path: Path) -> None:
        """AC1: tools: containing 'todos' (not bare 'todo') returns no errors."""
        agent_file = tmp_path / "clean.agent.md"
        _write_agent(
            agent_file,
            _agent_content("name: clean\ntools: [todos, read/readFile]"),
        )
        assert validate_agent(agent_file) == []

    def test_no_tools_field_passes(self, tmp_path: Path) -> None:
        """AC1: agent file with no tools: field at all returns no errors."""
        agent_file = tmp_path / "no-tools.agent.md"
        _write_agent(
            agent_file,
            _agent_content("name: no-tools\ndescription: Agent without tools."),
        )
        assert validate_agent(agent_file) == []

    def test_multiline_tools_todos_passes(self, tmp_path: Path) -> None:
        """AC1: multiline tools: block containing only 'todos' returns no errors."""
        content = "---\nname: multiline\ntools:\n  [todos, vscode/memory]\n---\n\n# Body\n"
        agent_file = tmp_path / "multiline.agent.md"
        _write_agent(agent_file, content)
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
        """
        agent_file = tmp_path / "substr.agent.md"
        _write_agent(
            agent_file,
            _agent_content("name: substr\ntools: [todos, todo_extra]"),
        )
        assert validate_agent(agent_file) == []

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
                "tools: [todos, read/readFile]",
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
            _agent_content("name: clean\ntools: [todos]"),
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
