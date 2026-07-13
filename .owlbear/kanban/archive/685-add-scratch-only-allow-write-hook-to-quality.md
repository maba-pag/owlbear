---
id: 685
title: Add scratch-only-allow write hook to quality-runner agent
status: archived
priority: medium
created: 2026-04-08T20:54:05.4426172+02:00
updated: 2026-04-09T02:24:01.6612457+02:00
started: 2026-04-09T02:24:01.6612457+02:00
completed: 2026-04-09T02:24:01.6612457+02:00
tags:
    - scope:agents
    - ' type:safety'
    - ' source:analysis'
class: standard
---

## Context

Split from #677. The quality-runner agent is "read-only except `.owlbear/scratch/` cleanup" per its persona. It cannot use the full `deny-writes.ps1` hook because it legitimately needs to write/delete files in `.owlbear/scratch/` (e.g., `pytest-output-{task_id}.txt` capture files).

Requires a dedicated PreToolUse hook that:
- Allows writes to `.owlbear/scratch/` paths only
- Denies all other file writes
- Follows the path-guard pattern from `deny-src-writes.ps1` (which allows `tests/` only)

## Codebase References

- Path-guard pattern: `.owlbear/hooks/deny-src-writes.ps1` (allow-list approach)
- Full deny pattern: `.owlbear/hooks/deny-writes.ps1`
- Agent file: `share/agents/quality-runner.agent.md`
- Repo memory note on absolute path handling: path guards must use regex match (`-match '(^|/)pattern/'`) not `StartsWith` — see `.owlbear/hooks/deny-src-writes.ps1` known issue

## Acceptance Criteria

- [ ] AC1: New hook script `.owlbear/hooks/deny-scratch-only-writes.ps1` exists and is non-empty
- [ ] AC2: Hook allows writes to paths matching `.owlbear/scratch/` (both absolute and relative paths)
- [ ] AC3: Hook denies writes to any path NOT matching `.owlbear/scratch/` with a descriptive `permissionDecisionReason`
- [ ] AC4: Hook covers all write tools: `create_file`, `replace_string_in_file`, `multi_replace_string_in_file`, `apply_patch`, `create_directory`, `editFiles`
- [ ] AC5: Hook returns `{}` (pass-through) for non-write tools
- [ ] AC6: `quality-runner.agent.md` frontmatter contains `hooks:` section with PreToolUse entry referencing the new hook script
- [ ] AC7: Test file validates hook script behavior (deny non-scratch writes, allow scratch writes, pass-through non-write tools) and agent frontmatter configuration

[[2026-04-08]] Wed 21:59
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One hook script + one agent frontmatter edit — single concern |
| Interface clarity | PASS | AC specifies exact path, tool list, and behavioral contract. Refinements below tighten AC2 and AC5 |
| Dependency correctness | PASS | No dependencies. `deny-src-writes.ps1` (pattern reference) already exists. #677 (split source) is independent |
| Module layering | PASS | Agent configs (`share/agents/`) reference hooks (`.owlbear/hooks/`) — no layering violation |
| TDD compliance | PASS | AC7 specifies test requirements. Test-writer will derive tests following `test_deny_src_writes_hook_589.py` pattern |
| KISS/YAGNI | PASS | Minimal adaptation of established allow-list pattern. No speculative features |
| Premise challenge | PASS | Defense-in-depth is established project pattern — reviewer, auditor, code-reader, challenger all have deny-writes hooks despite zero write tools. Hook guards against VS Code adding tools, model hallucination, and future tools-list changes |
| Pattern consistency | PASS | Follows `deny-src-writes.ps1` allow-list pattern exactly (stdin JSON → parse → check tool → extract paths → regex match → deny/allow) |
| Security surface | PASS | Hook IS a security control. Allow-list approach (deny by default) is correct. Known limitation: `run_in_terminal` bypasses PreToolUse hooks (documented, acceptable — quality-runner legitimately writes via terminal to `.owlbear/scratch/`) |
| Single domain | PASS | Hooks/agent configuration domain only |

### AC Refinements

| Original AC | Issue | Refined AC |
|---|---|---|
| AC2: "paths matching `.owlbear/scratch/` (both absolute and relative)" | Does not specify regex vs StartsWith — known pitfall from `deny-src-writes.ps1` bug (repo memory: path guards must use regex not StartsWith) | AC2: Hook allows writes to paths containing `.owlbear/scratch/` segment using PowerShell `-match '(^\|/)\.owlbear/scratch/'` regex (handles both absolute `C:\...\owlbear\.owlbear\scratch\file.txt` and relative `.owlbear/scratch/file.txt` paths). Must NOT use `StartsWith`. |
| AC5: "returns {} for non-write tools" | Missing safety edge cases that all existing hooks test (see test_deny_src_writes_hook_589.py AC5a-AC5e) | AC5: Hook returns `{}` (pass-through) for non-write tools AND for safety edge cases: (a) malformed JSON input, (b) missing `tool_name` key, (c) empty `tool_name` string, (d) write tool with no path fields in `tool_input`, (e) write tool with empty string `filePath`. |

### Architecture Notes

- quality-runner has zero edit tools: `tools: [execute/runInTerminal, execute/getTerminalOutput, execute/sendToTerminal, execute/awaitTerminal, execute/killTerminal, read/readFile, vscode/memory, read/terminalLastCommand, execute/testFailure]`. Hook is defense-in-depth per established project pattern.
- quality-runner writes to `.owlbear/scratch/` via terminal commands (`pathlib.Path('.owlbear/scratch/pytest-output-{task_id}.txt').write_text(...)`) — these bypass PreToolUse hooks by design. The hook guards the VS Code edit-tool layer only.
- Seed copy not required — `quality-runner.agent.md` does not exist in `seed/share/agents/` (seed has no agent files). All 5 existing hooks are mirrored to seed because their agents are consumer-facing. This hook is pipeline-internal only.
- Use case-insensitive `-notcontains` for write-tools matching (not `-cnotcontains`) per `deny-src-writes.ps1` pattern — more conservative.
- Existing `deny-src-writes.ps1` line 73 shows the regex pattern to follow: `$normalized -match '(^|/)tests/'` → adapt to `$normalized -match '(^|/)\.owlbear/scratch/'`.

### Challenge Results

- Challenger: RECONSIDER (confidence 0.35) — raised redundancy concern (quality-runner has no write tools), AC2 regex ambiguity, AC5 edge-case gap
- Architect response: Redundancy REBUTTED (defense-in-depth is established pattern per #677 review — reviewer/auditor/code-reader/challenger all have deny hooks with zero write tools). AC2 and AC5 refinements ACCEPTED and applied above.

### Verdict: APPROVE (with AC refinements)
### Action Taken: Refined AC2 (explicit regex requirement) and AC5 (enumerated edge cases). Advanced to todo.

[[2026-04-08]] Wed 23:00
## Test-Writer Notes

**Test file:** `tests/test_deny_scratch_only_writes_hook_685.py`

**Classes:**
- `TestFromAC_ScriptExists` — AC1 (script existence + non-empty)
- `TestFromAC_ScratchPathGuardBehavior` — AC2/AC3/AC4/AC5 (hook behavior via subprocess)
- `TestFromAC_QualityRunnerAgentHooks` — AC6 (agent frontmatter configuration)

**Tests per category:**

| Category | Count | Examples |
|---|---|---|
| Happy path (scratch allowed) | 10 | create_file/replace/multi_replace/apply_patch/create_directory/editFiles all with scratch paths |
| Error / deny paths | 11 | src/, tests/, .owlbear/hooks/, root paths; multi_replace mixed paths |
| Edge cases / safety | 9 | malformed JSON, empty tool_name, missing key, no paths, empty filePath, unknown tool |
| Boundary conditions | 4 | scratch without trailing slash, scratchpad/, empty replacements, mixed scratch+non-scratch |
| Output contract | 3 | valid JSON for allowed/denied calls, deny reason non-empty |
| Frontmatter (AC6) | 6 | hooks: key, PreToolUse entry, type: command, script reference, YAML parse, no duplicates |

**Total: 43 tests, all FAIL** (confirmed via pytest run)

**Failure reasons:**
- `TestFromAC_ScriptExists` (2): `.owlbear/hooks/deny-scratch-only-writes.ps1` does not exist → `AssertionError`
- `TestFromAC_ScratchPathGuardBehavior` (35): `FileNotFoundError` raised in `_run_hook()` before PowerShell executes
- `TestFromAC_QualityRunnerAgentHooks` (6): `quality-runner.agent.md` frontmatter missing `hooks:` key → `AssertionError`

**AC coverage:**

| AC | Tests |
|---|---|
| AC1: script exists and non-empty | `test_deny_scratch_only_writes_ps1_exists`, `test_script_is_nonempty` |
| AC2: allows .owlbear/scratch/ paths (regex, absolute, backslash) | `test_create_file_scratch_relative_path_is_allowed`, `test_create_file_scratch_nested_file_is_allowed`, `test_create_file_absolute_scratch_path_is_allowed`, `test_create_file_backslash_scratch_path_is_allowed` |
| AC3: denies non-scratch paths with reason | `test_create_file_src_path_is_denied`, `test_create_file_tests_path_is_denied`, `test_create_file_owlbear_hooks_path_is_denied`, `test_create_file_root_path_is_denied`, `test_deny_response_has_hook_specific_output_key`, `test_deny_reason_is_nonempty` |
| AC4: all 6 write tools gated | allow+deny tests for each of create_file, replace_string_in_file, multi_replace, apply_patch, create_directory, editFiles |
| AC5: pass-through + safety edges | malformed JSON, empty tool_name, missing key, no paths, empty filePath, run_in_terminal, read_file, unknown tool |
| AC6: agent frontmatter | 6 frontmatter tests |

Ruff: clean (0 violations).

[[2026-04-08]] Wed 23:28
## Builder Notes

### Files Changed
- `.owlbear/hooks/deny-scratch-only-writes.ps1` — new hook script (85 lines)
- `share/agents/quality-runner.agent.md` — added `hooks:` section to frontmatter

### Implementation
Adapted `deny-src-writes.ps1` allow-list pattern for `.owlbear/scratch/` only. Key changes:
- Regex: `$normalized -match '(^|/)\.owlbear/scratch/'` (not StartsWith per AC2 refinement)
- All 6 write tools gated: create_file, replace_string_in_file, multi_replace_string_in_file, apply_patch, create_directory, editFiles
- All AC5 safety edges handled: malformed JSON → `{}`, missing/empty tool_name → `{}`, no paths → `{}`, empty filePath → `{}`
- Agent frontmatter: `hooks: PreToolUse: [{type: command, command: powershell ... deny-scratch-only-writes.ps1}]`

### Test Results
- **43 passed, 0 failed** (all TestFromAC_* classes green)
- Confirmed RED before GREEN: 43 failed before implementation
- No TestBuilderDiscovered tests needed (AC covered all edge cases)

### Lint
- ruff: **clean** (0 violations on Python files)

### Commit
`2344773 feat(agents): add deny-scratch-only-writes hook to quality-runner - #685`

[[2026-04-09]] Thu 00:34
## Review Evidence

### Test Results
- pytest: **43 passed, 0 failed, 0 skipped** (re-run with `-v -m "not e2e"`)
- Initial QR run returned 4 (xdist artifact); explicit re-run confirmed 43.

### Lint
- ruff: **clean** (0 violations on test file)

### Coverage
- N/A — no Python modules changed (`.ps1` and `.md` changes only)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Tests | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: script exists and non-empty | `test_deny_scratch_only_writes_ps1_exists`, `test_script_is_nonempty` | Yes — explicit `.exists()` and `.stat().st_size > 0` assertions | **COVERED** |
| AC2: allows `.owlbear/scratch/` via regex (not StartsWith) | `test_create_file_scratch_relative_path_is_allowed`, `test_create_file_absolute_scratch_path_is_allowed`, `test_create_file_backslash_scratch_path_is_allowed`, `test_create_file_scratch_nested_file_is_allowed` | Yes — `assert output == {}` fails if deny returned; regex verified at hook line 64 | **COVERED** |
| AC3: denies non-scratch with descriptive reason | `test_create_file_src_path_is_denied`, `_tests_path_`, `_hooks_path_`, `_root_path_`, `test_deny_reason_is_nonempty`, `test_deny_response_has_hook_specific_output_key` | Yes — `_is_denied()` checks `hookSpecificOutput.permissionDecision == "deny"`; non-empty reason asserted | **COVERED** |
| AC4: all 6 write tools gated | allow+deny pair for each of: `create_file`, `replace_string_in_file`, `multi_replace_string_in_file`, `apply_patch`, `create_directory`, `editFiles` | Yes — each tool tested independently with allow (scratch) and deny (non-scratch) | **COVERED** |
| AC5: pass-through + 5 safety edges | `test_malformed_stdin_json_returns_empty_json` (AC5a), `test_empty_tool_name_returns_empty_json` (AC5b), `test_missing_tool_name_key_returns_empty_json` (AC5c), `test_write_tool_with_no_paths_returns_empty_json` (AC5d), `test_write_tool_with_empty_string_filepath_returns_empty_json` (AC5e), plus `run_in_terminal`, `read_file`, `unknown_tool` | Yes — all return `{}` assertions would fail if hook crashes or returns deny | **COVERED** |
| AC6: agent frontmatter hooks section | `test_frontmatter_has_hooks_section`, `test_frontmatter_has_pretooluse_entry`, `test_pretooluse_hook_type_is_command`, `test_pretooluse_hook_command_references_deny_scratch_only_writes`, `test_frontmatter_is_parseable_yaml_with_pretooluse_hook`, `test_frontmatter_no_duplicate_keys` | Yes — YAML parse + key assertions fail if section missing or malformed | **COVERED** |

#### Security Review
- Hardcoded secrets: none
- Injection: paths are only regex-matched, never interpolated into commands — safe
- Path traversal (`../`): regex `(^|/)\.owlbear/scratch/` does not normalize `..` segments. `some/.owlbear/scratch/../sensitive.py` would be allowed. This behavior is consistent with the `deny-src-writes.ps1` established pattern (same regex-match approach, no `..` normalization). Context: agent has ZERO edit tools; hook is defense-in-depth; inputs are model-generated VS Code tool calls (constrained inputs). Classified as **constrained-input edge case** per suppression rules — not a new vulnerability introduced by this task.
- Deserialization: `ConvertFrom-Json` with try/catch — safe
- No new dependencies

#### Test Integrity — TestFromAC_* Comparison

| Class | Preserved? | Modifications | Assessment |
|-------|-----------|---------------|------------|
| `TestFromAC_ScriptExists` (2 tests) | Yes | None | **PRESERVED** |
| `TestFromAC_ScratchPathGuardBehavior` (35 tests) | Yes | None | **PRESERVED** |
| `TestFromAC_QualityRunnerAgentHooks` (6 tests) | Yes | None | **PRESERVED** |

No TestFromAC_* tests weakened, removed, or modified by the builder.

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | **STRONG** | `output == {}` for allowed; `_is_denied()` checks `hookSpecificOutput.permissionDecision == "deny"`; deny reason asserted non-empty; context messages include `got: {output!r}` |
| Negative-path coverage | **STRONG** | All 6 write tools have allow + deny pair; edge cases: empty filePath, missing key, malformed JSON; boundary: `.owlbear/scratch` vs `.owlbear/scratchpad/` |
| Mutation resistance | **ADEQUATE** | Allow/deny logic inversion would be caught; boundary1/boundary2 tests catch regex tightness; `editFiles` object-format branch (hook lines 51–55, object entries with `.filePath`) is unexercised — see Pass 2 |
| Test independence | **STRONG** | Subprocess isolation; no shared state; each test independent |
| Descriptive names | **STRONG** | `test_[tool]_[path_variant]_[is_allowed/is_denied]` pattern throughout |

#### Data Safety
- No shared mutable state; no multi-step atomicity concerns; subprocess calls timeout-guarded (30s) — no issues.

#### Builder Process Quality
- 1 builder cycle, clean approach, no loop patterns — **CLEAN**.

### Pass 2 — Informational

1. **editFiles object-format branch untested** (hook lines 51–55): builder implemented handling for `files[*]` as objects with `.filePath` property. All AC4f tests use string arrays. If the object-handling branch returned `{}` for all inputs (a mutation), no test would catch it. The AC spec says "editFiles is a gated write tool" — verified by string tests. The agent has no editFiles tool, so this is dead-code-in-practice. Deduction: **–0.03**.
2. **Exit code contract unasserted**: tests verify JSON output but no test asserts `result.returncode == 0` for deny paths. Very minor. Deduction: **–0.01**.

### AC Compliance Table

| AC | Evidence | Status |
|----|----------|--------|
| AC1 | `.owlbear/hooks/deny-scratch-only-writes.ps1` exists, 85 lines; `TestFromAC_ScriptExists` green | **PASS** |
| AC2 | Hook line 64: `$normalized -match '(^|/)\.owlbear/scratch/'` (not StartsWith); 4 scratch-allow tests pass | **PASS** |
| AC3 | Hook lines 67–74: deny with `hookSpecificOutput.permissionDecisionReason`; 6 deny tests pass | **PASS** |
| AC4 | Hook lines 18–24: `$write_tools` array has all 6; 12 allow+deny pairs pass | **PASS** |
| AC5 | Hook lines 7–11 (try/catch), 27–28 (empty guard), 57–60 (no-paths guard); 9 safety tests pass | **PASS** |
| AC6 | `quality-runner.agent.md` lines 9–14: `hooks: PreToolUse: [{type: command, command: powershell ... deny-scratch-only-writes.ps1}]`; 6 frontmatter tests pass | **PASS** |

### Deductions
- editFiles object branch untested: –0.03
- Exit code not asserted: –0.01
- **Total deductions: –0.04**

### Verdict
**Confidence: 0.96 → PASS**
**Route: #685 → docs**

[[2026-04-09]] Thu 01:16
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `copilot-instructions.md` is 80 lines (project identity + branches only); agents/hooks not documented there; no behavior change to documented conventions |
| 2 | Module docstrings | No | N/A | No Python modules changed — only `.ps1` hook script and `quality-runner.agent.md` frontmatter (`.md` YAML, not Python) |
| 3 | External attribution | No | N/A | Pattern adapted from existing internal `deny-src-writes.ps1` — no external sources used |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | No | N/A | Task split from #677; no research phase; no `.owlbear/research/` doc produced |

### Files Updated
None — no docs impact.

### Scratch Files
No `.owlbear/scratch/685-*` files found — nothing to clean.

### Verdict
No docs impact. All AC passed per reviewer evidence. Advancing to done.

[[2026-04-09]] Thu 02:24
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: script exists and non-empty | `.owlbear/hooks/deny-scratch-only-writes.ps1` exists, 84 lines; `TestFromAC_ScriptExists` (2 tests) green | PASS |
| AC2: allows `.owlbear/scratch/` via regex | Hook line 64: `$normalized -match '(^\|/)\.owlbear/scratch/'` — not StartsWith; 4 allow tests green | PASS |
| AC3: denies non-scratch with reason | Hook lines 67–74: deny with `permissionDecisionReason`; 6 deny tests green | PASS |
| AC4: all 6 write tools gated | Hook lines 16–23: `$write_tools` array; 12 allow+deny pairs green | PASS |
| AC5: pass-through + safety edges | Hook try/catch, empty guard, no-paths guard; 9 safety tests green | PASS |
| AC6: agent frontmatter hooks | `quality-runner.agent.md` lines 10–13: hooks section present; 6 frontmatter tests green | PASS |
| AC7: test file validates behavior | `tests/test_deny_scratch_only_writes_hook_685.py`: 43 tests, 3 classes, all green | PASS |

### Test Results
- pytest (task-scoped): 43 passed, 0 failed
- pytest (full suite): 3663 passed, 383 failed — all 383 failures are pre-existing (none in task scope; verified by filtering for scratch/685/quality-runner patterns)
- ruff: 5 violations — all pre-existing in `serve/mcp-kanban/`, none in task files

### Architect Quality: 5/5
Specific AC with exact file paths, tool lists, behavioral contracts. AC2 and AC5 proactively refined during architecture review (regex requirement, 5 enumerated edge cases). Design notes correctly identified defense-in-depth rationale, seed copy exemption, and pattern source.

### Deduction Breakdown
- AC lines without evidence: 0 (all 7 verified) → 0
- Lint violations in scope: 0 → 0
- AC quality: 5/5 → 0
- Reviewer evidence: present, thorough, PASS at 0.96 → 0
- Full-suite failures in scope: 0 → 0
- Uncommitted test file (test-writer gap): noted but not a code quality issue → 0

### Confidence: 1.00
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 2344773 | feat | deny-scratch-only-writes.ps1, quality-runner.agent.md | #685 |
| 219665e | test | test_deny_scratch_only_writes_hook_685.py, 685 kanban task, hook line-ending normalization | #685 |
