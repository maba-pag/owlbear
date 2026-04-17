# lint-changed PostToolUse Hook — Test Approach

> **Owning task:** #892 — Tests: lint-changed PostToolUse hook equivalence
> **Date:** 2026-04-17 **Status:** Complete

## 1. Context and Question

Task #890 (macOS compat) requires porting 7 PowerShell hooks to Python. Task #892 is the RED-phase test file for the `lint-changed` PostToolUse hook. The existing test `test_lint_guard_hook_210.py` tests an older version at `scripts/hooks/lint-changed.ps1` (Windows-only, PowerShell subprocess). The production script is `.owlbear/hooks/lint-changed.ps1`.

**Question:** What is the correct testing approach for the Python port's equivalence tests, particularly ruff mocking, path extraction expansion, and .py file filtering?

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | VS Code Hooks docs — PostToolUse I/O | code.visualstudio.com/docs/copilot/customization/hooks | 1.0 |
| 2 | lint-changed.ps1 (dev) | `.owlbear/hooks/lint-changed.ps1` | 1.0 |
| 3 | lint-changed.ps1 (seed) | `seed/.owlbear/hooks/lint-changed.ps1` | 0.9 |
| 4 | test_lint_guard_hook_210.py | `tests/test_lint_guard_hook_210.py` | 1.0 |
| 5 | PostToolUse feasibility research | `.owlbear/research/posttooluse-lint-guard-feasibility.md` | 0.8 |
| 6 | #891 research (sibling) | `.owlbear/research/891-pretooluse-hooks-test-approach.md` | 1.0 |
| 7 | allow-stances-only.ps1 (path extraction) | `.owlbear/hooks/allow-stances-only.ps1` | 0.9 |
| 8 | test_deny_scratch_only_writes_hook_685.py | `tests/test_deny_scratch_only_writes_hook_685.py` | 0.8 |

## 3. Analysis

### 3.1 PostToolUse I/O Contract (from .ps1 + VS Code docs)

| Direction | Format |
|-----------|--------|
| stdin | `{"tool_name": "...", "tool_input": {...}}` (VS Code adds `timestamp`, `cwd`, `sessionId`, `tool_use_id`, `tool_response` — all ignored) |
| stdout clean/error | `{}` |
| stdout lint errors | `{"systemMessage": "<ruff>", "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "<ruff>"}}` |
| exit code | always 0 |
| fail-open | malformed/empty/binary stdin → `{}` exit 0 |

### 3.2 .ps1 vs Python Port Differences

| Aspect | Current .ps1 | Python port (per AC) |
|--------|-------------|---------------------|
| Edit tools | create_file, replace_string_in_file, multi_replace_string_in_file, apply_patch | Same 4 + editFiles, create_directory (implied by path formats) |
| Path extraction | filePath, replacements[].filePath | filePath, dirPath, replacements[].filePath, files[] |
| Extension filter | None (all files to ruff) | Only .py files |
| Dedup | Case-insensitive HashSet | Case-insensitive set |
| Invocation | `powershell -NoProfile -File` | `uv run python` (or `sys.executable` in tests) |

### 3.3 Ruff Mocking Strategy

The AC requires verifying `ruff check --ignore INP001` args. Since tests invoke the hook via subprocess, in-process mocking (`unittest.mock`) cannot reach into the child process. Two viable approaches:

| Approach | How | Pros | Cons |
|----------|-----|------|------|
| **Mock ruff on PATH** | Create a small script in `tmp_path` that records args to a file; prepend to `PATH` env when spawning hook subprocess | Tests exact ruff invocation args; no hook code changes needed | Requires executable mock script; platform-specific shebang |
| **Real ruff execution** | Create temp .py files with known lint errors/clean code; assert output behavior | Simpler; validates end-to-end behavior | Doesn't verify exact args; ruff version-coupled |

**Recommendation:** Use both. Mock-PATH tests for arg verification (AC4). Real-ruff tests for end-to-end I/O contract (AC2–3). The mock approach uses a Python script as the mock (`#!/usr/bin/env python3`) — cross-platform, no bash dependency.

### 3.4 Test Structure

| Aspect | Approach | Rationale |
|--------|----------|-----------|
| Script path | `.owlbear/hooks/lint-changed.py` | Matches #890 convention |
| Invocation | `subprocess.run([sys.executable, script], ...)` | Avoids `uv` dependency in test; consistent with #891 |
| File | `tests/test_lint_changed_hook.py` | Per AC |
| Markers | `pytest.mark.slow` | Subprocess I/O; consistent with existing hook tests |
| RED guarantee | `.owlbear/hooks/lint-changed.py` doesn't exist → FileNotFoundError | Explicit RED failure |

### 3.5 Test Case Matrix

| Category | Input | Expected Output |
|----------|-------|-----------------|
| Script exists | — | `.owlbear/hooks/lint-changed.py` on disk |
| Non-edit tool | `{"tool_name": "read_file", ...}` | `{}` |
| Unknown tool | `{"tool_name": "future_tool", ...}` | `{}` |
| create_file + clean .py | filePath → existing clean .py | `{}` |
| create_file + lint errors | filePath → existing bad .py | `{"systemMessage": "...", "hookSpecificOutput": {...}}` |
| replace_string + lint errors | filePath → existing bad .py | non-empty systemMessage |
| multi_replace + clean | replacements[].filePath → clean .py | `{}` |
| multi_replace + errors | replacements[].filePath → bad .py | non-empty systemMessage |
| apply_patch + filePath | filePath → bad .py | non-empty systemMessage |
| editFiles + files[] | files: ["bad.py"] | non-empty systemMessage (if editFiles in tool list) |
| dirPath input | dirPath → path string | `{}` (not a .py file, or not an edit tool) |
| Non-.py file filtered | filePath → existing .js file with bad content | `{}` |
| Non-existent file filtered | filePath → /nonexistent/foo.py | `{}` |
| Dedup: same path twice | replacements with duplicate filePaths | ruff called once per unique path |
| Dedup: case variants | `Foo.py` and `foo.py` same file | deduplicated (1 path to ruff) |
| Ruff args | mock ruff on PATH | receives `check --ignore INP001 <paths>` |
| Malformed: truncated JSON | `'{"tool_na'` | `{}` exit 0 |
| Malformed: empty stdin | `''` | `{}` exit 0 |
| Malformed: BOM prefix | BOM + valid JSON | `{}` exit 0 |
| Malformed: binary data | random bytes | `{}` exit 0 |
| Exit code always 0 | all scenarios | exit 0 |
| Output always valid JSON | all scenarios | parseable JSON dict |

## 4. Recommendation (confidence: 0.90)

**Follow the established subprocess-based testing pattern** from `test_lint_guard_hook_210.py` and #891, adapted for Python invocation. Key adaptations:

1. Helper: `_run_hook(stdin_data: dict | str | bytes) -> tuple[int, dict]` — invokes `sys.executable .owlbear/hooks/lint-changed.py`; raises `FileNotFoundError` when script missing (RED-explicit)
2. Ruff mocking via PATH manipulation — a Python script mock records args to a temp file; hook subprocess gets modified `PATH` env
3. `.py` filtering tests — create non-.py temp files, verify ruff not invoked on them
4. Deduplication tests — provide duplicate paths, verify ruff receives deduplicated list
5. Expanded path extraction tests — all 4 formats (filePath, dirPath, replacements[], files[])

The 3 deviations from the .ps1 (extension filter, expanded path formats, dedup verification) are prescribed by the AC and align with the PreToolUse hooks' path extraction.

Challenge: skipped — info-only research confirming a prescribed approach with no alternatives.

## 5. Follow-up Tasks

No new follow-up tasks needed — #895 (GREEN phase: port lint-changed to Python) already exists as the dependency target.
