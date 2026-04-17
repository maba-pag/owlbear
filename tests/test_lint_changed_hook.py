"""Tests for task #892: lint-changed PostToolUse hook equivalence.

Contract-level tests for:
1. .owlbear/hooks/lint-changed.py — Python port of lint-changed.ps1 PostToolUse hook
2. JSON I/O contract: stdin JSON → stdout JSON (systemMessage + hookSpecificOutput)
3. File path extraction: filePath, dirPath, replacements[], editFiles files[] formats
4. Ruff invocation: ruff check --ignore INP001, only existing .py files
5. Deduplication: case-insensitive HashSet-equivalent behavior
6. Malformed input: truncated JSON, empty stdin, BOM, binary → {} exit 0

Script path: .owlbear/hooks/lint-changed.py (does NOT exist yet — RED phase)

AC coverage:
  AC1:  tests/test_lint_changed_hook.py exists (this file)
  AC2a: stdout is valid JSON in all cases
  AC2b: systemMessage present on lint errors
  AC2c: hookSpecificOutput present on lint errors (hookEventName + additionalContext)
  AC2d: {} returned when no lint errors
  AC3a: filePath path extraction (create_file, replace_string_in_file, apply_patch)
  AC3b: dirPath path extraction — not a .py file path, must return {}
  AC3c: replacements[].filePath path extraction (multi_replace_string_in_file)
  AC3d: editFiles tool_name with files[] array of strings
  AC4a: ruff receives 'check' as first argument
  AC4b: ruff receives '--ignore' flag
  AC4c: ruff receives 'INP001' as the --ignore value
  AC4d: ruff receives the actual .py file path
  AC5a: non-existent .py path not passed to ruff → {}
  AC5b: existing non-.py file not passed to ruff → {}
  AC5c: existing .py file with errors IS passed to ruff → systemMessage
  AC6a: duplicate filePaths in replacements → ruff called once
  AC6b: case-variant paths → deduplicated (case-insensitive)
  AC7a: truncated JSON → {} exit 0
  AC7b: empty stdin → {} exit 0
  AC7c: BOM-prefixed input → {} exit 0
  AC7d: binary stdin → {} exit 0
  AC8:  tests invoke hook via subprocess([sys.executable, script_path])
  AC9:  all tests fail RED — .owlbear/hooks/lint-changed.py does not exist
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

_REPO_ROOT = Path(__file__).parent.parent
_SCRIPT_PATH = _REPO_ROOT / ".owlbear" / "hooks" / "lint-changed.py"

# A Python source that reliably generates an F401 unused-import ruff error.
_LINT_ERROR_CONTENT = "import os\n"

# A Python source that is ruff-clean under the project's ruff config.
_CLEAN_CONTENT = "x: int = 1\n"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_hook(
    stdin_data: dict | str | bytes,
    *,
    env: dict[str, str] | None = None,
    timeout: int = 30,
) -> tuple[int, dict]:
    """Invoke lint-changed.py via subprocess with the given stdin.

    Raises FileNotFoundError if the script does not exist — makes RED-phase
    failures explicit rather than silently masking the missing implementation.

    Returns (exit_code, parsed_stdout_dict).
    """
    if not _SCRIPT_PATH.exists():
        msg = (
            f"lint-changed.py not found at {_SCRIPT_PATH}. "
            "Builder must create .owlbear/hooks/lint-changed.py to make these tests pass."
        )
        raise FileNotFoundError(msg)

    if isinstance(stdin_data, dict):
        input_bytes: bytes = json.dumps(stdin_data).encode("utf-8")
    elif isinstance(stdin_data, str):
        input_bytes = stdin_data.encode("utf-8", errors="replace")
    else:
        input_bytes = stdin_data

    result = subprocess.run(
        [sys.executable, str(_SCRIPT_PATH)],
        input=input_bytes,
        capture_output=True,
        env=env if env is not None else os.environ.copy(),
        timeout=timeout,
    )
    stdout_bytes = result.stdout.strip()
    try:
        output = json.loads(stdout_bytes) if stdout_bytes else {}
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        output = {"_raw": stdout_bytes.decode("utf-8", errors="replace")}
    return result.returncode, output


@pytest.fixture
def mock_ruff_dir(tmp_path: Path) -> Path:
    """Create a mock 'ruff' Python script that records invocation args to a file.

    Returns the directory containing the mock ruff executable.
    Prepend this directory to PATH when invoking the hook to intercept ruff calls.
    The recorded args file is at <mock_ruff_dir>/ruff-args.json.
    """
    args_file = tmp_path / "ruff-args.json"
    mock_script = tmp_path / "ruff"
    mock_script.write_text(
        textwrap.dedent(
            f"""\
            #!/usr/bin/env python3
            import json
            import sys

            with open({str(args_file)!r}, "w", encoding="utf-8") as f:
                json.dump(sys.argv[1:], f)
            """
        ),
        encoding="utf-8",
    )
    mock_script.chmod(mock_script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return tmp_path


# ---------------------------------------------------------------------------
# AC1 / AC8 / AC9 — script must exist at expected path
# ---------------------------------------------------------------------------


class TestFromAC_ScriptExists:
    """AC1/AC8/AC9: .owlbear/hooks/lint-changed.py must exist and be non-empty."""

    def test_script_exists(self) -> None:
        """AC1: lint-changed.py must be created at .owlbear/hooks/lint-changed.py."""
        assert _SCRIPT_PATH.exists(), (
            f"lint-changed.py not found at {_SCRIPT_PATH}. Builder must create .owlbear/hooks/lint-changed.py."
        )

    def test_script_is_nonempty(self) -> None:
        """AC1: script must have content — an empty file is not a valid hook."""
        assert _SCRIPT_PATH.exists(), f"lint-changed.py not found at {_SCRIPT_PATH}."
        assert _SCRIPT_PATH.stat().st_size > 0, "lint-changed.py exists but is empty."


# ---------------------------------------------------------------------------
# AC2 — JSON I/O contract
# ---------------------------------------------------------------------------


class TestFromAC_JsonIOContract:
    """AC2: stdin JSON → stdout JSON; systemMessage + hookSpecificOutput on lint errors."""

    def test_non_edit_tool_returns_empty_dict(self) -> None:
        """AC2d: non-edit tool_name (read_file) → {}."""
        _, output = _run_hook({"tool_name": "read_file", "tool_input": {}})
        assert output == {}

    def test_unknown_tool_returns_empty_dict(self) -> None:
        """AC2d: unknown/future tool_name → {}."""
        _, output = _run_hook({"tool_name": "some_future_tool", "tool_input": {}})
        assert output == {}

    def test_lint_errors_include_system_message(self, tmp_path: Path) -> None:
        """AC2b: lint errors → output has non-empty 'systemMessage' key."""
        bad_file = tmp_path / "bad.py"
        bad_file.write_text(_LINT_ERROR_CONTENT, encoding="utf-8")
        _, output = _run_hook({"tool_name": "create_file", "tool_input": {"filePath": str(bad_file)}})
        assert "systemMessage" in output, f"Expected systemMessage in output, got: {output!r}"
        assert output["systemMessage"], "systemMessage must be non-empty ruff output"

    def test_lint_errors_include_hook_specific_output(self, tmp_path: Path) -> None:
        """AC2c: lint errors → hookSpecificOutput with hookEventName and additionalContext."""
        bad_file = tmp_path / "bad_hso.py"
        bad_file.write_text(_LINT_ERROR_CONTENT, encoding="utf-8")
        _, output = _run_hook({"tool_name": "create_file", "tool_input": {"filePath": str(bad_file)}})
        assert "hookSpecificOutput" in output, f"Expected hookSpecificOutput in output, got: {output!r}"
        hso = output["hookSpecificOutput"]
        assert hso.get("hookEventName") == "PostToolUse", f"hookEventName must be 'PostToolUse', got: {hso!r}"
        assert "additionalContext" in hso, f"additionalContext missing from hookSpecificOutput: {hso!r}"
        assert hso["additionalContext"], "additionalContext must be non-empty"

    def test_clean_file_returns_empty_dict(self, tmp_path: Path) -> None:
        """AC2d: clean .py file → {}."""
        clean_file = tmp_path / "clean.py"
        clean_file.write_text(_CLEAN_CONTENT, encoding="utf-8")
        _, output = _run_hook({"tool_name": "create_file", "tool_input": {"filePath": str(clean_file)}})
        assert output == {}

    def test_exit_code_always_zero_on_lint_errors(self, tmp_path: Path) -> None:
        """AC2: exit code must be 0 even when lint errors are reported (non-blocking design)."""
        bad_file = tmp_path / "bad_exit.py"
        bad_file.write_text(_LINT_ERROR_CONTENT, encoding="utf-8")
        code, _ = _run_hook({"tool_name": "create_file", "tool_input": {"filePath": str(bad_file)}})
        assert code == 0, f"Hook must exit 0 on lint errors, got exit {code}"

    def test_exit_code_always_zero_on_clean_file(self, tmp_path: Path) -> None:
        """AC2: exit code must be 0 for clean file."""
        clean_file = tmp_path / "clean_exit.py"
        clean_file.write_text(_CLEAN_CONTENT, encoding="utf-8")
        code, _ = _run_hook({"tool_name": "create_file", "tool_input": {"filePath": str(clean_file)}})
        assert code == 0, f"Hook must exit 0 on clean file, got exit {code}"

    def test_exit_code_always_zero_non_edit_tool(self) -> None:
        """AC2: exit code must be 0 for non-edit tool."""
        code, _ = _run_hook({"tool_name": "read_file", "tool_input": {}})
        assert code == 0, f"Hook must exit 0 for non-edit tools, got exit {code}"

    def test_output_is_always_valid_json(self, tmp_path: Path) -> None:
        """AC2a: stdout must always be parseable as a JSON object (raw subprocess check)."""
        if not _SCRIPT_PATH.exists():
            pytest.fail(
                f"lint-changed.py not found at {_SCRIPT_PATH}. Builder must create .owlbear/hooks/lint-changed.py."
            )
        bad_file = tmp_path / "bad_json_check.py"
        bad_file.write_text(_LINT_ERROR_CONTENT, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(_SCRIPT_PATH)],
            input=json.dumps({"tool_name": "create_file", "tool_input": {"filePath": str(bad_file)}}).encode("utf-8"),
            capture_output=True,
            timeout=30,
        )
        stdout = result.stdout.strip()
        try:
            parsed = json.loads(stdout) if stdout else {}
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            pytest.fail(f"stdout is not valid JSON: {stdout!r}\nError: {exc}")
        assert isinstance(parsed, dict), f"Output must be a JSON object, got: {parsed!r}"


# ---------------------------------------------------------------------------
# AC3 — path extraction formats
# ---------------------------------------------------------------------------


class TestFromAC_PathExtraction:
    """AC3: filePath, dirPath, replacements[].filePath, editFiles files[] extraction."""

    def test_filepath_from_create_file_linted(self, tmp_path: Path) -> None:
        """AC3a: filePath from create_file is extracted and linted."""
        bad_file = tmp_path / "create.py"
        bad_file.write_text(_LINT_ERROR_CONTENT, encoding="utf-8")
        _, output = _run_hook({"tool_name": "create_file", "tool_input": {"filePath": str(bad_file)}})
        assert "systemMessage" in output, "create_file filePath not extracted and linted"

    def test_filepath_from_replace_string_linted(self, tmp_path: Path) -> None:
        """AC3a: filePath from replace_string_in_file is extracted and linted."""
        bad_file = tmp_path / "replace.py"
        bad_file.write_text(_LINT_ERROR_CONTENT, encoding="utf-8")
        _, output = _run_hook({"tool_name": "replace_string_in_file", "tool_input": {"filePath": str(bad_file)}})
        assert "systemMessage" in output, "replace_string_in_file filePath not extracted and linted"

    def test_filepath_from_apply_patch_linted(self, tmp_path: Path) -> None:
        """AC3a: filePath from apply_patch is extracted and linted."""
        bad_file = tmp_path / "patch.py"
        bad_file.write_text(_LINT_ERROR_CONTENT, encoding="utf-8")
        _, output = _run_hook({"tool_name": "apply_patch", "tool_input": {"filePath": str(bad_file)}})
        assert "systemMessage" in output, "apply_patch filePath not extracted and linted"

    def test_dirpath_returns_empty_dict(self, tmp_path: Path) -> None:
        """AC3b: dirPath is not a .py file — must return {} (filtered by extension or tool)."""
        _, output = _run_hook(
            {
                "tool_name": "create_directory",
                "tool_input": {"dirPath": str(tmp_path / "some_dir")},
            }
        )
        assert output == {}, "dirPath must not produce lint output (not a .py file)"

    def test_replacements_filepath_from_multi_replace_linted(self, tmp_path: Path) -> None:
        """AC3c: replacements[].filePath from multi_replace_string_in_file is extracted and linted."""
        bad_file = tmp_path / "multi.py"
        bad_file.write_text(_LINT_ERROR_CONTENT, encoding="utf-8")
        _, output = _run_hook(
            {
                "tool_name": "multi_replace_string_in_file",
                "tool_input": {"replacements": [{"filePath": str(bad_file)}]},
            }
        )
        assert "systemMessage" in output, "multi_replace replacements[].filePath not extracted and linted"

    def test_multi_replace_clean_files_returns_empty_dict(self, tmp_path: Path) -> None:
        """AC3c: multi_replace with clean .py files → {}."""
        clean_file = tmp_path / "clean_multi.py"
        clean_file.write_text(_CLEAN_CONTENT, encoding="utf-8")
        _, output = _run_hook(
            {
                "tool_name": "multi_replace_string_in_file",
                "tool_input": {"replacements": [{"filePath": str(clean_file)}]},
            }
        )
        assert output == {}

    def test_editfiles_files_array_linted(self, tmp_path: Path) -> None:
        """AC3d: editFiles tool with files[] array of strings — .py files extracted and linted."""
        bad_file = tmp_path / "edit.py"
        bad_file.write_text(_LINT_ERROR_CONTENT, encoding="utf-8")
        _, output = _run_hook({"tool_name": "editFiles", "tool_input": {"files": [str(bad_file)]}})
        assert "systemMessage" in output, "editFiles files[] array not extracted and linted"

    def test_empty_replacements_array_returns_empty_dict(self) -> None:
        """AC3c: multi_replace with empty replacements[] → no paths extracted → {}."""
        _, output = _run_hook(
            {
                "tool_name": "multi_replace_string_in_file",
                "tool_input": {"replacements": []},
            }
        )
        assert output == {}


# ---------------------------------------------------------------------------
# AC4 — ruff invocation arguments
# ---------------------------------------------------------------------------


class TestFromAC_RuffArgs:
    """AC4: ruff invoked with 'check --ignore INP001 <paths>' — verified via PATH mock."""

    def test_ruff_receives_check_subcommand(self, tmp_path: Path, mock_ruff_dir: Path) -> None:
        """AC4a: ruff is invoked with 'check' as the first argument."""
        bad_file = tmp_path / "ruff_check.py"
        bad_file.write_text(_LINT_ERROR_CONTENT, encoding="utf-8")
        env = os.environ.copy()
        env["PATH"] = str(mock_ruff_dir) + os.pathsep + env.get("PATH", "")
        _run_hook(
            {"tool_name": "create_file", "tool_input": {"filePath": str(bad_file)}},
            env=env,
        )
        args_file = mock_ruff_dir / "ruff-args.json"
        assert args_file.exists(), "Mock ruff was never called — hook did not invoke ruff"
        args: list[str] = json.loads(args_file.read_text(encoding="utf-8"))
        assert "check" in args, f"ruff must receive 'check' subcommand; got args: {args}"

    def test_ruff_receives_ignore_inp001(self, tmp_path: Path, mock_ruff_dir: Path) -> None:
        """AC4b/AC4c: ruff is invoked with '--ignore INP001'."""
        bad_file = tmp_path / "ruff_ignore.py"
        bad_file.write_text(_LINT_ERROR_CONTENT, encoding="utf-8")
        env = os.environ.copy()
        env["PATH"] = str(mock_ruff_dir) + os.pathsep + env.get("PATH", "")
        _run_hook(
            {"tool_name": "create_file", "tool_input": {"filePath": str(bad_file)}},
            env=env,
        )
        args_file = mock_ruff_dir / "ruff-args.json"
        assert args_file.exists(), "Mock ruff was never called — hook did not invoke ruff"
        args = json.loads(args_file.read_text(encoding="utf-8"))
        assert "--ignore" in args, f"ruff must receive '--ignore' flag; got args: {args}"
        ignore_idx = args.index("--ignore")
        assert ignore_idx + 1 < len(args), f"'--ignore' has no following value; got args: {args}"
        assert args[ignore_idx + 1] == "INP001", f"ruff '--ignore' value must be 'INP001'; got '{args[ignore_idx + 1]}'"

    def test_ruff_receives_file_path(self, tmp_path: Path, mock_ruff_dir: Path) -> None:
        """AC4d: ruff is invoked with the actual file path as an argument."""
        bad_file = tmp_path / "ruff_path.py"
        bad_file.write_text(_LINT_ERROR_CONTENT, encoding="utf-8")
        env = os.environ.copy()
        env["PATH"] = str(mock_ruff_dir) + os.pathsep + env.get("PATH", "")
        _run_hook(
            {"tool_name": "create_file", "tool_input": {"filePath": str(bad_file)}},
            env=env,
        )
        args_file = mock_ruff_dir / "ruff-args.json"
        assert args_file.exists(), "Mock ruff was never called — hook did not invoke ruff"
        args = json.loads(args_file.read_text(encoding="utf-8"))
        assert str(bad_file) in args, f"ruff must receive file path '{bad_file}'; got args: {args}"


# ---------------------------------------------------------------------------
# AC5 — .py extension and existence filtering
# ---------------------------------------------------------------------------


class TestFromAC_PyFilter:
    """AC5: only existing .py files are passed to ruff."""

    def test_nonexistent_py_file_not_passed_to_ruff(self) -> None:
        """AC5a: non-existent .py path → filtered out → {} (ruff not called)."""
        _, output = _run_hook(
            {
                "tool_name": "create_file",
                "tool_input": {"filePath": "/nonexistent/path/no_such_file_abc123.py"},
            }
        )
        assert output == {}, "Non-existent .py path must be filtered; hook must return {}"

    def test_existing_non_py_file_not_linted(self, tmp_path: Path) -> None:
        """AC5b: existing non-.py file → filtered by extension → {}."""
        bad_js = tmp_path / "bad.js"
        bad_js.write_text("import os\n", encoding="utf-8")
        _, output = _run_hook({"tool_name": "create_file", "tool_input": {"filePath": str(bad_js)}})
        assert output == {}, "Non-.py file must be filtered from ruff invocation"

    def test_existing_py_file_with_errors_is_linted(self, tmp_path: Path) -> None:
        """AC5c: existing .py file with lint errors → ruff runs → systemMessage returned."""
        bad_file = tmp_path / "should_lint.py"
        bad_file.write_text(_LINT_ERROR_CONTENT, encoding="utf-8")
        _, output = _run_hook({"tool_name": "create_file", "tool_input": {"filePath": str(bad_file)}})
        assert "systemMessage" in output, "Existing .py file with errors must trigger systemMessage"

    def test_txt_file_not_linted(self, tmp_path: Path) -> None:
        """AC5b: existing .txt file → filtered by extension → {}."""
        txt_file = tmp_path / "notes.txt"
        txt_file.write_text("import os\n", encoding="utf-8")
        _, output = _run_hook({"tool_name": "create_file", "tool_input": {"filePath": str(txt_file)}})
        assert output == {}, ".txt file must be filtered from ruff invocation"


# ---------------------------------------------------------------------------
# AC6 — deduplication (case-insensitive)
# ---------------------------------------------------------------------------


class TestFromAC_Deduplication:
    """AC6: duplicate file paths deduplicated before ruff invocation."""

    def test_duplicate_paths_in_replacements_deduplicated(self, tmp_path: Path, mock_ruff_dir: Path) -> None:
        """AC6a: same filePath twice in replacements → ruff receives path exactly once."""
        bad_file = tmp_path / "dedup.py"
        bad_file.write_text(_LINT_ERROR_CONTENT, encoding="utf-8")
        env = os.environ.copy()
        env["PATH"] = str(mock_ruff_dir) + os.pathsep + env.get("PATH", "")
        _run_hook(
            {
                "tool_name": "multi_replace_string_in_file",
                "tool_input": {
                    "replacements": [
                        {"filePath": str(bad_file)},
                        {"filePath": str(bad_file)},
                    ]
                },
            },
            env=env,
        )
        args_file = mock_ruff_dir / "ruff-args.json"
        assert args_file.exists(), "Mock ruff was never called"
        args: list[str] = json.loads(args_file.read_text(encoding="utf-8"))
        # Count occurrences of this exact path in ruff args
        path_occurrences = args.count(str(bad_file))
        assert path_occurrences == 1, (
            f"Duplicate path must be deduplicated to 1 ruff arg; got {path_occurrences} occurrences in args: {args}"
        )

    def test_case_variant_paths_deduplicated(self, tmp_path: Path, mock_ruff_dir: Path) -> None:
        """AC6b: case-variant paths (foo.py vs Foo.py) → single .py arg to ruff."""
        lower = tmp_path / "case.py"
        lower.write_text(_LINT_ERROR_CONTENT, encoding="utf-8")
        upper_str = str(tmp_path / "Case.py")  # same file on case-insensitive FS
        env = os.environ.copy()
        env["PATH"] = str(mock_ruff_dir) + os.pathsep + env.get("PATH", "")
        _run_hook(
            {
                "tool_name": "multi_replace_string_in_file",
                "tool_input": {
                    "replacements": [
                        {"filePath": str(lower)},
                        {"filePath": upper_str},
                    ]
                },
            },
            env=env,
        )
        args_file = mock_ruff_dir / "ruff-args.json"
        assert args_file.exists(), "Mock ruff was never called"
        args = json.loads(args_file.read_text(encoding="utf-8"))
        # Only one .py path should reach ruff after case-insensitive dedup
        py_args = [a for a in args if a.lower().endswith(".py")]
        assert len(py_args) == 1, (
            f"Case-variant paths must be deduplicated to 1; ruff received {len(py_args)} .py args: {py_args}"
        )


# ---------------------------------------------------------------------------
# AC7 — malformed input (fail-open: → {} exit 0)
# ---------------------------------------------------------------------------


class TestFromAC_MalformedInput:
    """AC7: malformed stdin cases all return {} with exit 0 (fail-open contract)."""

    def test_truncated_json_returns_empty_dict(self) -> None:
        """AC7a: truncated JSON → {} exit 0."""
        code, output = _run_hook('{"tool_na')
        assert output == {}, f"Truncated JSON must return {{}}, got {output!r}"
        assert code == 0, f"Truncated JSON must exit 0, got {code}"

    def test_empty_stdin_returns_empty_dict(self) -> None:
        """AC7b: empty stdin → {} exit 0."""
        code, output = _run_hook("")
        assert output == {}, f"Empty stdin must return {{}}, got {output!r}"
        assert code == 0, f"Empty stdin must exit 0, got {code}"

    def test_bom_prefixed_input_returns_empty_dict(self) -> None:
        """AC7c: BOM-prefixed input → {} exit 0 (BOM may corrupt JSON parsing)."""
        bom = b"\xef\xbb\xbf"
        # Use an edit tool + non-existent file so that even if BOM is stripped and
        # JSON parses, the missing file is filtered → {} regardless of parse outcome.
        payload = bom + json.dumps(
            {
                "tool_name": "create_file",
                "tool_input": {"filePath": "/nonexistent/bom_test_abc123.py"},
            }
        ).encode("utf-8")
        code, output = _run_hook(payload)
        assert output == {}, f"BOM-prefixed input must return {{}}, got {output!r}"
        assert code == 0, f"BOM-prefixed input must exit 0, got {code}"

    def test_binary_stdin_returns_empty_dict(self) -> None:
        """AC7d: binary/random bytes → {} exit 0 (fail-open)."""
        binary_data = bytes(range(256))
        code, output = _run_hook(binary_data)
        assert output == {}, f"Binary stdin must return {{}}, got {output!r}"
        assert code == 0, f"Binary stdin must exit 0, got {code}"
