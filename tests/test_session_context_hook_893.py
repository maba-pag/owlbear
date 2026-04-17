"""Tests for task #893: session-context.py SessionStart hook equivalence.

Contract-level tests for .owlbear/hooks/session-context.py — a cross-platform
Python port of session-context.ps1.

AC coverage:
  AC1: session-context.py exists at .owlbear/hooks/session-context.py and is non-empty
  AC2: stdin JSON → stdout JSON with hookSpecificOutput, hookEventName, additionalContext
       containing branch name and recent commits
  AC3: git branch --show-current and git log --oneline -3 --no-decorate are invoked
  AC4: non-zero git exit code → {} with exit 0 (fail-open)
  AC5: truncated JSON, empty stdin, BOM prefix, binary → all return {} with exit 0
  AC6: tests invoke the .py script via subprocess (sys.executable)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

_REPO_ROOT = Path(__file__).parent.parent
_SCRIPT_PATH = _REPO_ROOT / ".owlbear" / "hooks" / "session-context.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fake_git(
    tmp_path: Path,
    *,
    branch_output: str = "main",
    log_lines: str = "abc1234 Add feature\ndef5678 Fix bug\n1234567 Update docs",
    branch_exit_code: int = 0,
    log_exit_code: int = 0,
) -> tuple[Path, Path]:
    """Create a fake Python-based git executable in tmp_path.

    The fake git logs all invocation arguments to git_calls.log and returns
    controlled output for 'branch' and 'log' sub-commands.

    Returns (fake_git_path, git_calls_log_path).
    """
    git_calls_log = tmp_path / "git_calls.log"
    fake_git = tmp_path / "git"

    script = "\n".join(
        [
            f"#!{sys.executable}",
            "import sys, pathlib",
            f"_log = pathlib.Path({str(git_calls_log)!r})",
            'with _log.open("a") as f:',
            '    f.write(" ".join(sys.argv[1:]) + "\\n")',
            'cmd = sys.argv[1] if len(sys.argv) > 1 else ""',
            'if cmd == "branch":',
            f"    if {branch_exit_code!r} == 0:",
            f"        print({branch_output!r})",
            f"    sys.exit({branch_exit_code!r})",
            'elif cmd == "log":',
            f"    if {log_exit_code!r} == 0:",
            f"        print({log_lines!r})",
            f"    sys.exit({log_exit_code!r})",
            "sys.exit(0)",
        ]
    )
    fake_git.write_text(script)
    fake_git.chmod(0o755)
    return fake_git, git_calls_log


def _run_hook(
    stdin_data: str | dict,
    *,
    timeout: int = 30,
    extra_env: dict[str, str] | None = None,
) -> tuple[int, dict]:
    """Run session-context.py via subprocess with the given stdin.

    Raises FileNotFoundError if session-context.py does not exist — makes
    RED-phase failures explicit and readable.

    Returns (exit_code, parsed_stdout_as_dict).
    """
    if not _SCRIPT_PATH.exists():
        msg = (
            f"session-context.py not found at {_SCRIPT_PATH}. "
            "Builder must create .owlbear/hooks/session-context.py to pass these tests."
        )
        raise FileNotFoundError(msg)

    env = {**os.environ, **(extra_env or {})}
    input_str = json.dumps(stdin_data) if isinstance(stdin_data, dict) else stdin_data

    result = subprocess.run(
        [sys.executable, str(_SCRIPT_PATH)],
        input=input_str,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=env,
    )
    stdout = result.stdout.strip()
    try:
        output = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError:
        output = {"_raw": stdout}
    return result.returncode, output


def _run_hook_binary(
    stdin_bytes: bytes,
    *,
    timeout: int = 30,
    extra_env: dict[str, str] | None = None,
) -> tuple[int, dict]:
    """Run session-context.py with raw binary stdin (for malformed-input tests).

    Raises FileNotFoundError if session-context.py does not exist.
    Returns (exit_code, parsed_stdout_as_dict).
    """
    if not _SCRIPT_PATH.exists():
        msg = (
            f"session-context.py not found at {_SCRIPT_PATH}. "
            "Builder must create .owlbear/hooks/session-context.py to pass these tests."
        )
        raise FileNotFoundError(msg)

    env = {**os.environ, **(extra_env or {})}

    result = subprocess.run(
        [sys.executable, str(_SCRIPT_PATH)],
        input=stdin_bytes,
        capture_output=True,
        timeout=timeout,
        env=env,
    )
    stdout = result.stdout.strip().decode("utf-8", errors="replace")
    try:
        output = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError:
        output = {"_raw": stdout}
    return result.returncode, output


# ---------------------------------------------------------------------------
# AC1: Script existence
# ---------------------------------------------------------------------------


class TestFromAC_ScriptExists:
    """AC1: .owlbear/hooks/session-context.py must exist and be non-empty."""

    def test_session_context_py_exists(self) -> None:
        """AC1: session-context.py must exist at the expected path."""
        assert _SCRIPT_PATH.exists(), (
            f"session-context.py not found at {_SCRIPT_PATH}. Builder must create .owlbear/hooks/session-context.py."
        )

    def test_script_is_nonempty(self) -> None:
        """AC1: script file must have content — an empty file cannot implement context injection."""
        assert _SCRIPT_PATH.exists(), f"session-context.py not found at {_SCRIPT_PATH}."
        assert _SCRIPT_PATH.stat().st_size > 0, "session-context.py exists but is empty — builder must implement it."


# ---------------------------------------------------------------------------
# AC2: JSON I/O contract
# ---------------------------------------------------------------------------


class TestFromAC_JsonIoContract:
    """AC2: stdin JSON → stdout JSON with hookSpecificOutput containing branch and commits."""

    def test_output_has_hook_specific_output_key(self, tmp_path: Path) -> None:
        """AC2: happy-path output must contain 'hookSpecificOutput' key."""
        _make_fake_git(tmp_path)
        env = {"PATH": f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}"}
        _, output = _run_hook({"source": "new"}, extra_env=env)
        assert "hookSpecificOutput" in output, f"Expected 'hookSpecificOutput' key in response, got: {output!r}"

    def test_hook_event_name_is_session_start(self, tmp_path: Path) -> None:
        """AC2: hookSpecificOutput.hookEventName must be 'SessionStart'."""
        _make_fake_git(tmp_path)
        env = {"PATH": f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}"}
        _, output = _run_hook({"source": "new"}, extra_env=env)
        hook_out = output.get("hookSpecificOutput", {})
        assert hook_out.get("hookEventName") == "SessionStart", (
            f"hookEventName must be 'SessionStart', got: {hook_out!r}"
        )

    def test_additional_context_has_branch_prefix(self, tmp_path: Path) -> None:
        """AC2: additionalContext must start with 'Branch: '."""
        _make_fake_git(tmp_path, branch_output="feature-branch")
        env = {"PATH": f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}"}
        _, output = _run_hook({"source": "new"}, extra_env=env)
        ctx = output.get("hookSpecificOutput", {}).get("additionalContext", "")
        assert ctx.startswith("Branch: "), f"additionalContext must start with 'Branch: ', got: {ctx!r}"

    def test_additional_context_contains_branch_name(self, tmp_path: Path) -> None:
        """AC2: additionalContext must include the actual branch name returned by git."""
        _make_fake_git(tmp_path, branch_output="test-branch-xyz")
        env = {"PATH": f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}"}
        _, output = _run_hook({"source": "new"}, extra_env=env)
        ctx = output.get("hookSpecificOutput", {}).get("additionalContext", "")
        assert "test-branch-xyz" in ctx, (
            f"additionalContext must contain the branch name 'test-branch-xyz', got: {ctx!r}"
        )

    def test_additional_context_has_commits_separator(self, tmp_path: Path) -> None:
        """AC2: additionalContext must contain ' | Commits: ' separator."""
        _make_fake_git(tmp_path)
        env = {"PATH": f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}"}
        _, output = _run_hook({"source": "new"}, extra_env=env)
        ctx = output.get("hookSpecificOutput", {}).get("additionalContext", "")
        assert " | Commits: " in ctx, f"additionalContext must contain ' | Commits: ' separator, got: {ctx!r}"

    def test_stdout_is_valid_json(self, tmp_path: Path) -> None:
        """AC2: script stdout must always be valid JSON — no plaintext noise."""
        if not _SCRIPT_PATH.exists():
            raise FileNotFoundError(f"session-context.py not found at {_SCRIPT_PATH}.")
        _make_fake_git(tmp_path)
        env = {**os.environ, "PATH": f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}"}
        result = subprocess.run(
            [sys.executable, str(_SCRIPT_PATH)],
            input=json.dumps({"source": "new"}),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            env=env,
        )
        stdout = result.stdout.strip()
        try:
            parsed = json.loads(stdout) if stdout else {}
        except json.JSONDecodeError as exc:
            pytest.fail(f"Script stdout is not valid JSON: {stdout!r}\nError: {exc}")
        assert isinstance(parsed, dict), f"Output must be a JSON object, got: {parsed!r}"

    def test_exit_code_is_zero_on_success(self, tmp_path: Path) -> None:
        """AC2: script must exit with code 0 on successful execution."""
        _make_fake_git(tmp_path)
        env = {"PATH": f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}"}
        exit_code, _ = _run_hook({"source": "new"}, extra_env=env)
        assert exit_code == 0, f"Script must exit 0 on success, got: {exit_code}"

    def test_detached_head_uses_head_fallback(self, tmp_path: Path) -> None:
        """AC2: when git branch --show-current returns empty string (detached HEAD),
        additionalContext must contain 'HEAD' as the branch name."""
        _make_fake_git(tmp_path, branch_output="")
        env = {"PATH": f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}"}
        _, output = _run_hook({"source": "new"}, extra_env=env)
        ctx = output.get("hookSpecificOutput", {}).get("additionalContext", "")
        assert "HEAD" in ctx, (
            f"additionalContext must contain 'HEAD' for detached HEAD state (empty git branch output), got: {ctx!r}"
        )

    def test_additional_context_contains_commit_text(self, tmp_path: Path) -> None:
        """AC2: additionalContext must contain actual commit text from git log output."""
        known_commit = "abc1234"
        _make_fake_git(
            tmp_path,
            log_lines=f"{known_commit} Add feature\ndef5678 Fix bug\n1234567 Update docs",
        )
        env = {"PATH": f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}"}
        _, output = _run_hook({"source": "new"}, extra_env=env)
        ctx = output.get("hookSpecificOutput", {}).get("additionalContext", "")
        assert known_commit in ctx, (
            f"additionalContext must contain commit text '{known_commit}' from git log output, got: {ctx!r}"
        )


# ---------------------------------------------------------------------------
# AC3: Git invocation — verify exact commands called
# ---------------------------------------------------------------------------


class TestFromAC_GitInvocation:
    """AC3: 'git branch --show-current' and 'git log --oneline -3 --no-decorate' must be called."""

    def test_git_branch_show_current_is_called(self, tmp_path: Path) -> None:
        """AC3: script must invoke 'git branch --show-current'."""
        _, calls_log = _make_fake_git(tmp_path)
        env = {"PATH": f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}"}
        _run_hook({"source": "new"}, extra_env=env)
        assert calls_log.exists(), "Fake git log file was not created — script did not invoke git at all."
        calls = calls_log.read_text()
        assert "branch --show-current" in calls, (
            f"Expected 'git branch --show-current' to be called, got git calls:\n{calls}"
        )

    def test_git_log_oneline_3_no_decorate_is_called(self, tmp_path: Path) -> None:
        """AC3: script must invoke 'git log --oneline -3 --no-decorate'."""
        _, calls_log = _make_fake_git(tmp_path)
        env = {"PATH": f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}"}
        _run_hook({"source": "new"}, extra_env=env)
        assert calls_log.exists(), "Fake git log file was not created — script did not invoke git at all."
        calls = calls_log.read_text()
        assert "log --oneline -3 --no-decorate" in calls, (
            f"Expected 'git log --oneline -3 --no-decorate' to be called, got git calls:\n{calls}"
        )


# ---------------------------------------------------------------------------
# AC4: Git failure handling
# ---------------------------------------------------------------------------


class TestFromAC_GitFailureHandling:
    """AC4: any git failure → {} with exit 0 (fail-open, no crash)."""

    def test_git_branch_failure_returns_empty_dict(self, tmp_path: Path) -> None:
        """AC4: git branch exiting non-zero must cause script to return {} with exit 0."""
        _make_fake_git(tmp_path, branch_exit_code=1)
        env = {"PATH": f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}"}
        exit_code, output = _run_hook({"source": "new"}, extra_env=env)
        assert output == {}, f"Git branch failure must return {{}} (fail-open, AC4), got: {output!r}"
        assert exit_code == 0, f"Script must exit 0 even on git branch failure, got: {exit_code}"

    def test_git_log_failure_returns_empty_dict(self, tmp_path: Path) -> None:
        """AC4: git log exiting non-zero must cause script to return {} with exit 0."""
        _make_fake_git(tmp_path, log_exit_code=1)
        env = {"PATH": f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}"}
        exit_code, output = _run_hook({"source": "new"}, extra_env=env)
        assert output == {}, f"Git log failure must return {{}} (fail-open, AC4), got: {output!r}"
        assert exit_code == 0, f"Script must exit 0 even on git log failure, got: {exit_code}"

    def test_git_not_found_returns_empty_dict(self, tmp_path: Path) -> None:
        """AC4: git not on PATH must return {} with exit 0 (FileNotFoundError handled gracefully)."""
        # Restrict PATH to tmp_path only — no system git available
        env = {"PATH": str(tmp_path)}
        exit_code, output = _run_hook({"source": "new"}, extra_env=env)
        assert output == {}, f"Missing git must return {{}} (fail-open, AC4), got: {output!r}"
        assert exit_code == 0, f"Script must exit 0 when git is not found, got: {exit_code}"

    def test_git_failure_exit_code_is_always_zero(self, tmp_path: Path) -> None:
        """AC4: script must always exit 0 regardless of git failure mode (128 = not-a-git-repo)."""
        _make_fake_git(tmp_path, branch_exit_code=128, log_exit_code=128)
        env = {"PATH": f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}"}
        exit_code, _ = _run_hook({"source": "new"}, extra_env=env)
        assert exit_code == 0, f"Script must exit 0 even on git exit 128 (not-a-git-repo), got: {exit_code}"


# ---------------------------------------------------------------------------
# AC5: Malformed input
# ---------------------------------------------------------------------------


class TestFromAC_MalformedInput:
    """AC5: truncated JSON, empty stdin, BOM prefix, binary → all return {} with exit 0."""

    def test_truncated_json_returns_empty_dict(self) -> None:
        """AC5: truncated/incomplete JSON must return {} with exit 0 (fail-open)."""
        exit_code, output = _run_hook('{"source": "new"')
        assert output == {}, f"Truncated JSON must return {{}} (fail-open, AC5), got: {output!r}"
        assert exit_code == 0, f"Must exit 0 on truncated JSON, got: {exit_code}"

    def test_empty_stdin_returns_empty_dict(self) -> None:
        """AC5: empty stdin must return {} with exit 0 (fail-open)."""
        exit_code, output = _run_hook("")
        assert output == {}, f"Empty stdin must return {{}} (fail-open, AC5), got: {output!r}"
        assert exit_code == 0, f"Must exit 0 on empty stdin, got: {exit_code}"

    def test_bom_prefix_returns_empty_dict(self) -> None:
        """AC5: BOM-prefixed input must return {} with exit 0 (json.loads rejects BOM)."""
        exit_code, output = _run_hook('\ufeff{"source": "new"}')
        assert output == {}, f"BOM-prefixed input must return {{}} (fail-open, AC5), got: {output!r}"
        assert exit_code == 0, f"Must exit 0 on BOM-prefixed input, got: {exit_code}"

    def test_binary_stdin_returns_empty_dict(self) -> None:
        """AC5: raw binary stdin must return {} with exit 0 (non-UTF-8 bytes are malformed)."""
        exit_code, output = _run_hook_binary(b"\x00\x01\x02\xff\xfe")
        assert output == {}, f"Binary stdin must return {{}} (fail-open, AC5), got: {output!r}"
        assert exit_code == 0, f"Must exit 0 on binary stdin, got: {exit_code}"
