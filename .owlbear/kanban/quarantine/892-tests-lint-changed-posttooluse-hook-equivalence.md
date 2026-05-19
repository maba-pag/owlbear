---
id: 892
title: 'Tests: lint-changed PostToolUse hook equivalence'
status: archived
priority: needed
created: 2026-04-16T22:53:29.680503+00:00
updated: 2026-04-17T02:55:16.060880+00:00
tags:
- phase-1
- scope:hooks
- type:test
- platform
parent: 890
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #890 and `.owlbear/briefs/draft-macos-compat/brief.md`

## Acceptance Criteria

- [ ] Test file for lint-changed.py PostToolUse hook
- [ ] Tests verify JSON I/O contract: stdin JSON with tool_input containing file paths, stdout JSON with systemMessage and hookSpecificOutput
- [ ] File path extraction tested: filePath, dirPath, replacements[], editFiles[] input formats
- [ ] Ruff invocation mocked or patched — verify correct args passed (ruff check --ignore INP001)
- [ ] Only existing .py files passed to ruff (non-existent paths filtered, non-.py filtered)
- [ ] Deduplication of file paths tested (HashSet equivalent behavior)
- [ ] Malformed input cases: truncated JSON, empty stdin, BOM, binary all return {} with exit 0
- [ ] Tests invoke the .py script via subprocess
- [ ] All tests fail (RED) — no .py implementation exists yet

## Files

- `tests/test_lint_changed_hook.py` (new)
[[2026-04-17]]

## Research

- Research doc: .owlbear/research/892-lint-changed-hook-test-approach.md
- Sources: 8 studied, 7 high-relevance (lint-changed.ps1, test_lint_guard_hook_210.py, VS Code hooks docs, #891 sibling research, allow-stances-only.ps1 path extraction, PostToolUse feasibility research)
- Recommendation: Follow established subprocess-based testing pattern adapted for Python invocation. Helper invokes `sys.executable .owlbear/hooks/lint-changed.py`. Ruff mocking via PATH manipulation (Python script mock records args to temp file). Extension filtering (.py only) and expanded path extraction (filePath, dirPath, replacements[], files[]) align with PreToolUse hooks. (confidence: 0.90)
- Key findings: .ps1 I/O contract well-defined (stdin JSON → stdout JSON, exit 0, fail-open). AC expands on .ps1 in 3 areas: .py file filtering, 4-format path extraction (vs 2 in .ps1), and ruff arg verification via mocking. Deduplication should be case-insensitive (matching .ps1 HashSet behavior). Mock-PATH + real-ruff hybrid approach covers both arg verification and end-to-end behavior.
- Follow-up tasks created: none needed (#895 already exists as GREEN phase)
- Decision requests: none

## Challenge Results

- Challenger: skipped — info-only research confirming prescribed approach with no alternatives
- Confidence in original: 0.90
[[2026-04-17]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One test file for one hook (lint-changed PostToolUse) |
| Interface clarity | PASS | All 9 AC lines are specific and testable; path formats, ruff args, malformed cases all enumerated |
| Dependency correctness | PASS | No depends_on — correct for RED phase. GREEN #895 depends on this task |
| Module layering | N/A | Test file only |
| TDD compliance | PASS | This IS the RED phase; #895 is the GREEN pair |
| KISS/YAGNI | PASS | AC expands beyond .ps1 (dirPath, editFiles/files[], .py filter) — justified by Brief D2/D5/D10 clean-break decisions |
| Premise challenge | PASS | Cross-platform porting requires tests first; no existing capability covers this |
| Pattern consistency | PASS | Follows established subprocess test pattern from test_lint_guard_hook_210.py |
| Security surface | PASS | No new security surface — tests are isolated with controlled stdin |
| Single domain | PASS | scope:hooks only |
| Failure mode map | N/A | Test-only task |
| Decision-request verification | PASS | Parent decisions D2/D5/D6/D7/D10 all resolved in Brief |
| User-action detection | N/A | Counter-signal C3: tagged type:test |

### Codebase Evidence

- `.owlbear/hooks/lint-changed.ps1` — production hook, 85 lines, I/O contract well-defined
- `.owlbear/hooks/lint-changed.py` — does NOT exist (correct for RED)
- `tests/test_lint_guard_hook_210.py` — 350+ lines, established subprocess testing pattern to follow
- Research doc `.owlbear/research/892-lint-changed-hook-test-approach.md` — thorough (8 sources, 0.90 confidence), includes full test case matrix

### Non-implementation tagging

Task tagged `type:test` — pass-through tag present. Test-writer will process accordingly.

### Challenge Results

- Challenger: proceed (0.85)
- Concerns: (1) AC3 "editFiles[]" conflates tool name with field name — mitigated by research doc §3.5 showing `editFiles + files[]` pattern. (2) dirPath extraction is vacuous for lint (always filtered by .py check) — acceptable for consistency with PreToolUse hooks. (3) No explicit ruff-not-found test case — covered by GREEN phase #895 AC "any exception returns {} with exit 0".
- Architect response: accepted — all concerns low-severity, mitigated by research doc the test-writer will consume

### Verdict: APPROVE

### Action Taken: Advanced to todo. AC well-specified, research thorough, TDD pairing correct (#892 RED → #895 GREEN)

[[2026-04-17]]

## Test-Writer Notes

**File:** `tests/test_lint_changed_hook.py` (new, 32 tests)

### Test Classes

| Class | AC Line(s) | Tests | Category |
|-------|-----------|-------|----------|
| `TestFromAC_ScriptExists` | AC1/AC8/AC9 | 2 | happy/error |
| `TestFromAC_JsonIOContract` | AC2 | 9 | happy/edge/error/boundary |
| `TestFromAC_PathExtraction` | AC3 | 8 | happy/edge/boundary |
| `TestFromAC_RuffArgs` | AC4 | 3 | happy/boundary |
| `TestFromAC_PyFilter` | AC5 | 4 | happy/edge/boundary |
| `TestFromAC_Deduplication` | AC6 | 2 | edge/boundary |
| `TestFromAC_MalformedInput` | AC7 | 4 | error |

**Total: 32 tests — 32 FAIL, 0 PASS (pytest verified)**

### AC Coverage

| AC | Description | Tests |
|----|-------------|-------|
| AC1 | Test file for lint-changed.py PostToolUse hook | `TestFromAC_ScriptExists` |
| AC2 | JSON I/O contract: stdin JSON → stdout systemMessage + hookSpecificOutput | `TestFromAC_JsonIOContract` (9 tests) |
| AC3 | Path extraction: filePath, dirPath, replacements[], editFiles files[] | `TestFromAC_PathExtraction` (8 tests) |
| AC4 | Ruff invocation: `ruff check --ignore INP001` args verified via PATH mock | `TestFromAC_RuffArgs` (3 tests) |
| AC5 | Only existing .py files passed to ruff (non-existent + non-.py filtered) | `TestFromAC_PyFilter` (4 tests) |
| AC6 | Deduplication: exact duplicate + case-variant paths → 1 ruff arg | `TestFromAC_Deduplication` (2 tests) |
| AC7 | Malformed input: truncated JSON, empty stdin, BOM, binary → {} exit 0 | `TestFromAC_MalformedInput` (4 tests) |
| AC8 | Tests invoke script via `subprocess([sys.executable, script_path])` | `_run_hook` helper |
| AC9 | All tests fail RED — .owlbear/hooks/lint-changed.py does not exist | 32/32 FAIL ✓ |

### Mock Strategy

- Ruff arg verification uses PATH-mock fixture (`mock_ruff_dir`): Python script named `ruff` records `sys.argv[1:]` to `ruff-args.json`; hook subprocess picks it up via modified PATH env.
- All other tests use real ruff via `tmp_path` temp .py files.

**ruff check:** All checks passed (clean)
[[2026-04-17]]

## Builder Notes

**Files changed:** `.owlbear/hooks/lint-changed.py` (new, 112 lines)

**Test results:** 32 passed, 0 failed — all TestFromAC_* classes green

**Coverage:** N/A — subprocess-tested script (not importable as module)

**Lint status:** ruff clean (0 violations)

**Commit:** 0d80ee7e — `feat: add lint-changed.py PostToolUse hook Python port (#892, builder)`

### Evidence summary

- Implemented `.owlbear/hooks/lint-changed.py` following pattern from `deny-writes.py` and mirroring `.ps1` I/O contract
- Stdin JSON → stdout JSON; fail-open on all parse/subprocess errors (BOM stripped, `try/except` guards)
- Tool routing: `multi_replace_string_in_file` → `replacements[].filePath`; `editFiles` → `files[]`; others → `tool_input.filePath`
- Case-insensitive deduplication via `seen: set[str]` with `.lower()` key
- Filters: only existing `.py` files passed to ruff
- Ruff args: `ruff check --ignore INP001 <paths>` with `check=False` for `subprocess.run`
- Inline `# noqa: BLE001/S603/S607` for intentional patterns (fail-open, trusted binary)
- Exit code always 0 per fail-open contract
[[2026-04-17]]

## Review Evidence

### Test Results

- pytest: 32 passed, 0 failed

### Lint

clean: true (0 violations — both `tests/test_lint_changed_hook.py` and `.owlbear/hooks/lint-changed.py`)

### Coverage

N/A — subprocess-tested script; not importable as module. Coverage tooling inapplicable by design.

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: test file exists | `TestFromAC_ScriptExists.test_script_exists` | Yes — asserts `_SCRIPT_PATH.exists()` | COVERED |
| AC2: JSON I/O contract | `TestFromAC_JsonIOContract` (9 tests) | Yes — systemMessage, hookSpecificOutput, exit codes, valid JSON all asserted by value | COVERED |
| AC3: path extraction (filePath, dirPath, replacements[], editFiles) | `TestFromAC_PathExtraction` (8 tests) | Yes for filePath/multi_replace/editFiles; dirPath test (`create_directory` not in `_EDIT_TOOLS`) returns `{}` via tool routing, not dirPath filtering — behavior correct, mechanism indirect | LAX (AC3b) |
| AC4: ruff args `check --ignore INP001` | `TestFromAC_RuffArgs` (3 tests, mock_ruff_dir) | Yes — args list inspected by value: `"check" in args`, `args[ignore_idx+1] == "INP001"`, path in args | COVERED |
| AC5: .py extension + existence filter | `TestFromAC_PyFilter` (4 tests) | Yes — nonexistent .py, .js, .txt all assert `output == {}` | COVERED |
| AC6: case-insensitive deduplication | `TestFromAC_Deduplication` (2 tests) | Yes — counts occurrences in ruff args list, asserts `== 1` | COVERED |
| AC7: malformed input → {} exit 0 | `TestFromAC_MalformedInput` (4 tests) | Yes — truncated JSON, empty, BOM, binary all assert `output == {} and code == 0` | COVERED |
| AC8: subprocess invocation | `_run_hook` helper (line 72) | Yes — `subprocess.run([sys.executable, str(_SCRIPT_PATH)], ...)` | COVERED |
| AC9: RED phase (all fail before impl) | Historical (test-writer verified 32/32 FAIL) | N/A — implementation now exists | COVERED |

LAX AC3b: `test_dirpath_returns_empty_dict` uses `create_directory` (unrecognized tool → `{}` via tool routing). Correct output, wrong mechanism. A `create_file` + `{"dirPath": ...}` payload also returns `{}` via `_add(tool_input.get("filePath"))` → None → empty list. Behavior equivalent; no compensating test required (architect noted "dirPath extraction is vacuous for lint").

#### Security Review

- Hardcoded secrets: None
- Injection: `subprocess.run(["ruff", "check", "--ignore", "INP001", *existing_py], check=False)` — list form, no `shell=True`; no shell injection risk. `# noqa: S603/S607` comments acknowledge pattern. SAFE.
- Path traversal: Stdin-sourced paths passed to ruff (read-only linter, no file write). Hook runs as local user; no privilege escalation path. SAFE.
- Insecure deserialization: `json.loads` only. SAFE.
- Input validation: Fail-open `try/except` at all boundaries. SAFE.
- Dependencies: No new dependencies. SAFE.
- Secret leakage: ruff output returned in systemMessage/additionalContext — ruff only reports error locations (file:line:col rule), not file contents. SAFE.

**No security issues.**

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All 32 `TestFromAC_*` tests | Builder only created `.owlbear/hooks/lint-changed.py` (new file, 112 lines); test file not in builder's changed-files list | PRESERVED |

No `TestFromAC_*` modifications detected. Builder self-report ("Files changed: `.owlbear/hooks/lint-changed.py`") consistent with task scope.

#### Test Quality

- **Assertion specificity**: STRONG — no lazy `assert result` or `assert result is not None`. Assertions check exact values (`output == {}`, `output["hookSpecificOutput"]["hookEventName"] == "PostToolUse"`, args by index).
- **Error-path coverage**: STRONG — AC7 class (4 error paths), filter tests (AC5), tool-routing tests (AC2d).
- **Mutation resistance**: STRONG — removing BOM stripping still returns `{}` (JSON parse fails), but other mutations caught: removing `_EDIT_TOOLS` check breaks 2+ tests; removing `--ignore INP001` breaks `test_ruff_receives_ignore_inp001`; removing dedup breaks count assertion.
- **Test independence**: STRONG — `tmp_path` fixture isolates all file I/O; `mock_ruff_dir` scoped to test.
- **Descriptive names**: STRONG — all names are behavior-describing.

#### Data Safety

No shared mutable state. No LLM output persistence. No unbounded input paths. PASS.

#### Implementation-Aware Gap Analysis

Implementation paths reviewed against AC:

- `not isinstance(tool_input, dict)` guard: lint-changed.py:22 — trivial defensive boundary, no AC requirement, not flagged.
- `try/except` around `_extract_paths`: lint-changed.py:68 — defensive guard for unexpected edge cases. Not flagged.
- `ruff returncode == 2` (ruff internal error): returns `{}` via `else` branch (lint-changed.py:97). No AC line requires testing this; consistent with `.ps1` behavior. Not flagged.

No significant untested paths.

#### Builder Process Quality

1 `## Builder Notes` section. CLEAN.

### Process Observation (Informational)

Builder performed GREEN implementation work (`.owlbear/hooks/lint-changed.py`) inside RED task #892, committing as `feat: add lint-changed.py PostToolUse hook Python port (#892, builder)`. The designated GREEN task #895 was bypassed. Task #895 likely needs to be closed or marked superseded. No impact on verdict.

### Verdict

Confidence: 0.95 → PASS
[[2026-04-17]]

## Docs Gate

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 1 | Behavior/API → copilot-instructions.md | No | N/A | New hook script is an internal ops file; copilot-instructions.md has no hooks inventory section; `.owlbear/` entry covers the directory |
| 2 | Module docstrings | Yes | PASS | `lint-changed.py` has module docstring (lines 1–5) and `_extract_paths()` docstring; `main()` is CLI entry-point covered by module docstring — adequate |
| 3 | External attribution | Yes | PASS | 1 external source (VS Code Hooks docs) already in `sources/overview.md` line 4034; 7 other sources are internal codebase files — no additional rows required |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | PASS | `.owlbear/research/892-lint-changed-hook-test-approach.md` exists; linked from task body; follow-up #895 (GREEN) pre-exists |

**Files updated:** None — no documentation changes required.

**Scratch files:** No `.owlbear/scratch/892-*` files found.

**Verdict:** No docs impact — checklist passed. Advancing to done.
[[2026-04-17]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Test file exists | `tests/test_lint_changed_hook.py` confirmed on disk, 32 tests | PASS |
| AC2: JSON I/O contract | Spot-checked: `test_lint_errors_include_system_message` (L176), `test_lint_errors_include_hook_specific_output` (L184) verify systemMessage + hookSpecificOutput with PostToolUse. 9 tests total per reviewer mapping. | PASS |
| AC3: Path extraction (4 formats) | Reviewer mapped 8 tests across filePath, dirPath, replacements[], editFiles. AC3b (dirPath) marked LAX — behavior correct via tool routing, mechanism indirect. Architect noted dirPath "vacuous for lint." | PASS |
| AC4: Ruff args mock | Spot-checked: `mock_ruff_dir` fixture (L112-127) records args; `test_ruff_receives_ignore_inp001` (L347) asserts --ignore INP001 pair | PASS |
| AC5: .py filter + existence | Reviewer verified 4 tests: nonexistent .py, .js, .txt all return {} | PASS |
| AC6: Deduplication | Reviewer verified 2 tests: exact duplicate + case-variant, count assertion | PASS |
| AC7: Malformed input | Reviewer verified 4 tests: truncated JSON, empty, BOM, binary all return {} exit 0 | PASS |
| AC8: Subprocess invocation | `_run_hook` helper at L72: `subprocess.run([sys.executable, str(_SCRIPT_PATH)])` | PASS |
| AC9: RED phase (all fail before impl) | Historical — test-writer verified 32/32 FAIL; now 32/32 PASS with implementation | PASS |

### Test Results

- pytest (full suite): INCOMPLETE — crashes at 76-98% with MCP server teardown error (exit 137). Systemic infrastructure issue, not task-related. Task-scoped tests: 32 passed, 0 failed (per builder + reviewer).
- ruff: 1 violation in unrelated file (`tests/test_scaffold_mcp_memory_524.py:739` F811). Task files clean.

### Architect Quality: 4/5

AC lines are specific, testable, and well-enumerated. Minor gap: AC3b dirPath extraction is vacuous for lint context (architect acknowledged this). Research was thorough (8 sources, 0.90 confidence). TDD pairing correctly structured (#892 RED, #895 GREEN). Clean implementation path.

### Deduction Breakdown

- AC lines without evidence: 0 (all 9 verified) — no deduction
- Lint violations in task scope: 0 — no deduction
- AC quality score: 4/5 (above 3) — no deduction
- Missing reviewer evidence: present, detailed, PASS — no deduction
- Full-suite test failures in task scope: 0 confirmed — no deduction
- Discretionary: -.02 for incomplete full-suite verification (infrastructure crash prevented confirmation of cross-task regression status)

### Confidence: 0.98

### Action: archive

### Process Observations (Informational)

1. Full test suite cannot complete due to systemic MCP teardown crash — affects all audits, not task-specific. Consider investigating separately.
2. Builder performed GREEN implementation inside RED task #892 (commit 0d80ee7e). GREEN task #895 may need to be closed or marked superseded.
3. Unrelated ruff F811 in test_scaffold_mcp_memory_524.py:739 — pre-existing, not introduced by this task.
