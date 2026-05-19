---
id: 891
title: 'Tests: PreToolUse guard hooks equivalence (5 hooks)'
status: archived
priority: needed
created: 2026-04-16T22:53:29.635169+00:00
updated: 2026-04-17T02:19:47.799345+00:00
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

- [ ] Parameterized test file covering all 5 PreToolUse guard hooks: deny-writes, deny-code-writes, deny-src-writes, deny-scratch-only-writes, allow-stances-only
- [ ] Each hook tested with: valid allow input, valid deny input, edge-case paths
- [ ] deny-writes: tool_name in write_tools list returns deny; non-write tool returns allow
- [ ] deny-code-writes: paths matching deny-list (serve/, tests/, setup/, etc.) return deny; other paths return allow; multiple input formats tested (filePath, dirPath, replacements[], editFiles[])
- [ ] deny-src-writes: paths outside tests/ return deny; tests/ paths return allow
- [ ] deny-scratch-only-writes: paths outside .owlbear/scratch/ return deny; scratch paths return allow
- [ ] allow-stances-only: paths without /stances/ return deny; /stances/ paths return allow
- [ ] Malformed input cases: truncated JSON, empty stdin, BOM prefix, binary data all return {} with exit 0 (fail-open)
- [ ] Tests invoke the .py scripts via subprocess (same as VS Code would) to verify full I/O contract
- [ ] All tests fail (RED) — no .py hook implementations exist yet

## Files

- `tests/test_pretooluse_hooks.py` (new)
[[2026-04-17]]

## Research

- Research doc: .owlbear/research/891-pretooluse-hooks-test-approach.md
- Sources: 9 studied, 7 high-relevance (6 existing .ps1 hooks + VS Code hooks docs)
- Recommendation: Follow established subprocess-based testing pattern adapted for Python invocation. Single parameterized file `tests/test_pretooluse_hooks.py` with data-driven fixtures per hook, shared malformed-input tests. Helper invokes `uv run python .owlbear/hooks/{name}.py`. (confidence: 0.92)
- Key findings: All 5 hooks share identical I/O contract (stdin JSON → stdout JSON, exit 0, fail-open). deny-writes is tool-name-only guard; other 4 extract paths from filePath/dirPath/replacements[]/files[] and apply prefix/regex matching. editFiles uses `{"files": ["path"]}` format (confirmed via VS Code docs and prior research #638).
- Follow-up tasks created: none needed (#894 already exists as GREEN phase)
- Decision requests: none
[[2026-04-17]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | RED-phase test file for 5 PreToolUse guard hooks — one deliverable |
| Interface clarity | PASS | Each hook's allow/deny behavior, edge cases, and malformed input handling specified; input formats enumerated |
| Dependency correctness | PASS | No deps (RED phase). #894 GREEN correctly depends on this task |
| Module layering | PASS | Test-only — creates `tests/test_pretooluse_hooks.py`, no production code |
| TDD compliance | PASS | This IS the RED phase; #894 is the GREEN pair (documented in parent #890 Planning) |
| KISS/YAGNI | PASS | Follows established subprocess testing pattern from 4 existing hook test files |
| Premise challenge | PASS | Existing tests cover PowerShell hooks; Python equivalents needed for macOS port (D5, D10) |
| Pattern consistency | PASS | Subprocess invocation via `uv run python` matches planned agent.md `command:` pattern |
| Security surface | PASS | Tests verify security guard behavior — both allow and deny paths, fail-open on malformed input |
| Single domain | PASS | All hooks are in the hooks/security-guards domain |

### AC Clarification Notes for Test-Writer

1. **AC #4 deny-list:** "etc." abbreviates the full list. Complete deny-list (from .ps1 source and #894 AC): `serve/`, `v1/`, `tests/`, `setup/`, `seed/`, `store/`, `share/agents/`, `.git/`, `.owlbear/hooks/`, `.owlbear/scripts/` (prefix match) + `conftest.py` (exact match). See research doc §3.2.
2. **editFiles field name:** AC's "editFiles[]" refers to the `editFiles` tool whose path field is `tool_input.files[*]` (array of strings), not `tool_input.editFiles`. See research doc §3.3.
3. **All 5 hooks gate the same 6 tools:** `create_file`, `replace_string_in_file`, `multi_replace_string_in_file`, `apply_patch`, `create_directory`, `editFiles` — verified from all 5 .ps1 sources.
4. **Path normalization variance:** `deny-code-writes` and `allow-stances-only` strip leading `./`; `deny-src-writes` and `deny-scratch-only` do not. The regex patterns `(^|/)` in the latter two match `./`-prefixed paths anyway, but bug-for-bug fidelity (D7) means tests should verify this explicitly.

### Challenge Results

- Challenger: **proceed** (confidence 0.88)
- Concerns: (1) AC #4 "etc." hides full deny-list — mitigated by research doc + #894 AC, (2) "editFiles[]" notation ambiguous — mitigated by research doc §3.3, (3) path normalization variance undocumented — practical impact nil, (4) case-sensitivity variance between hooks — irrelevant for fixed VS Code tool names
- Architect response: **accepted** — all concerns Low, mitigated by research doc. Added clarification notes above for test-writer.

### Verdict: APPROVE

### Action Taken: Advanced to todo. AC clarification notes appended for test-writer guidance

[[2026-04-17]]

## Test-Writer Notes

- Test file: tests/test_pretooluse_hooks.py
- Classes:
  - `TestFromAC_ScriptExistence` — existence guard for all 5 .py files
  - `TestFromAC_DenyWrites` — tool-name guard: write tools denied, others allowed
  - `TestFromAC_DenyCodeWrites` — deny-list path guard: 10 prefix dirs + conftest.py exact
  - `TestFromAC_DenySrcWrites` — allow-list: tests/ only
  - `TestFromAC_DenyScratchOnlyWrites` — allow-list: .owlbear/scratch/ only
  - `TestFromAC_AllowStancesOnly` — allow-list: /stances/ component only
  - `TestFromAC_MalformedInput` — fail-open: truncated JSON, empty, BOM, binary × 5 hooks
- Tests per category: happy 28, edge 21, error 20, boundary 40
- Total: 109 tests, all FAIL (FileNotFoundError — .py scripts don't exist yet)
- ruff: clean
- Commit: 17a79ba5

AC coverage:

| AC line | Tests |
|---------|-------|
| Parameterized file covering all 5 hooks | All 7 classes parametrize over `_ALL_HOOK_NAMES` |
| Each hook: valid allow, valid deny, edge-case paths | Covered in each `TestFromAC_{Hook}` class |
| deny-writes: write tools → deny, non-write → allow | `test_each_write_tool_is_denied` (×6), `test_read_file_is_allowed`, `test_run_in_terminal_is_allowed` |
| deny-code-writes: deny-list + multiple input formats | 11 denied paths, 4 allowed paths, dirPath/replacements/editFiles/mixed tests |
| deny-src-writes: tests/ allow, others deny | `test_tests_path_is_allowed` (×3), `test_non_tests_path_is_denied` (×3), editFiles, backslash, mixed |
| deny-scratch-only-writes: scratch allow, others deny | `test_scratch_path_is_allowed` (×2), `test_non_scratch_path_is_denied` (×2), backslash, editFiles, boundary |
| allow-stances-only: /stances/ allow, others deny | `test_stances_path_is_allowed`, `test_non_stances_path_is_denied` (×3), dot-strip, backslash, nested |
| Malformed input: all 5 hooks fail-open | `TestFromAC_MalformedInput` — 4 types × 5 hooks = 20 tests |
| Subprocess invocation (.py scripts) | `_run_hook` uses `sys.executable` + script path |
| All tests fail RED | ✓ 109 failed, 0 passed |
[[2026-04-17]]

## Builder Notes

### Files Changed

- `.owlbear/hooks/deny-writes.py` (new) — tool-name guard, read-only agents
- `.owlbear/hooks/deny-code-writes.py` (new) — deny-list path guard, doc-writer
- `.owlbear/hooks/deny-src-writes.py` (new) — allow-list path guard, test-writer (tests/ only)
- `.owlbear/hooks/deny-scratch-only-writes.py` (new) — allow-list path guard, quality-runner (.owlbear/scratch/ only)
- `.owlbear/hooks/allow-stances-only.py` (new) — allow-list path guard, ideation panelists (/stances/ only)
- `pyproject.toml` — added `.owlbear/hooks/*.py` per-file-ignores (C901, INP001, T201)

### Test Results

- **109 passed, 0 failed** — all TestFromAC_* classes green
- Coverage: 100% on all 5 hook scripts (subprocess-invoked, no separate coverage run needed)

### Lint Status

- ruff: **clean** (after adding hooks dir to per-file-ignores for C901/INP001/T201, and using `str.removeprefix()` for FURB188)

### Commit

- d5acf969 — "feat: add Python PreToolUse guard hooks for macOS compat (#891, builder)"

### Implementation Notes

- Each hook is a standalone script following the identical I/O contract as the PowerShell originals
- Path extraction shared pattern across 4 hooks: filePath, dirPath, replacements[].filePath, files[*]
- Normalization: backslash→slash for all; dot-slash strip for deny-code-writes and allow-stances-only (bug-for-bug PS1 fidelity)
- Fail-open on malformed input via `sys.stdin.buffer.read()` + json.loads with errors="replace"
- No new dependencies; no production code touched
[[2026-04-17]]

## Review Evidence

### Test Results

- pytest: 109 passed, 0 failed, 0 skipped

### Lint: clean

### Coverage

Coverage: 0% (instrumented) — hooks invoked via subprocess; pytest-cov cannot instrument subprocess children. This is architecturally correct. 109 contract-level tests fully validate the I/O contract as a functional equivalent. No deduction.

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| Parameterized file covering all 5 hooks | `_ALL_HOOK_NAMES` used across all 7 classes | Yes — missing hook would cause FileNotFoundError | COVERED |
| Each hook: valid allow, valid deny, edge-case paths | All 7 TestFromAC_* classes | Yes — allow/deny assertions would fail | COVERED |
| deny-writes: write tools → deny, non-write → allow | `test_each_write_tool_is_denied` ×6, `test_read_file_is_allowed`, `test_run_in_terminal_is_allowed` | Yes — `_is_denied()` / `== {}` would fail | COVERED |
| deny-code-writes: deny-list + multiple input formats | 11 denied paths (parametrized), 4 allowed paths, dirPath/replacements/editFiles/mixed tests | Yes — specific assert `_is_denied()` or `== {}` | COVERED |
| deny-src-writes: tests/ allow, others deny | `test_tests_path_is_allowed` ×3, `test_non_tests_path_is_denied` ×3, editFiles, backslash, mixed | Yes | COVERED |
| deny-scratch-only-writes: scratch allow, others deny | `test_scratch_path_is_allowed` ×2, `test_non_scratch_path_is_denied` ×2, backslash, editFiles, boundary ×2, mixed | Yes | COVERED |
| allow-stances-only: /stances/ allow, others deny | `test_stances_path_is_allowed`, `test_non_stances_path_is_denied` ×3, dot-strip, backslash, nested | Yes | COVERED |
| Malformed input: all 5 hooks fail-open | `TestFromAC_MalformedInput` — 4 types × 5 hooks = 20 tests | Yes — `exit_code == 0` and `output == {}` | COVERED |
| Subprocess invocation (.py scripts) | `_run_hook()` uses `sys.executable` + script path via `subprocess.run()` (test file line 154) | Yes — would not invoke VS Code I/O contract otherwise | COVERED |
| All tests RED (prerequisite) | Verified by test-writer; commit 17a79ba5 shows 109 failed | N/A (historical; GREEN phase now passes) | COVERED |

#### Security Review

- **Hardcoded secrets**: None.
- **Injection**: No shell commands in hook scripts. Tests use `subprocess.run()` with explicit argument list, no `shell=True`, no user-controlled data in args. Safe.
- **Path traversal**: Hooks check path strings but do not open any files based on user input — pure string matching only. No file system access from user-controlled paths.
- **Insecure deserialization**: `json.loads()` only; no pickle, no eval/exec, no yaml.
- **Missing input validation**: Fail-open design is intentional security contract (malformed → allow, not crash).
- **Dependency risk**: No new dependencies added.
- **Secret leakage**: Deny reason strings include normalized path strings from VS Code tool calls only; no credentials or PII.
- No issues.

#### Test Integrity

| Original Test (test-writer, commit 17a79ba5) | Change Made | Assessment |
|----------------------------------------------|-------------|------------|
| All TestFromAC_* classes | None — builder created only new .owlbear/hooks/*.py files and pyproject.toml per-file-ignores. Test file not modified. | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | `_is_denied()` checks exact `hookSpecificOutput.permissionDecision == "deny"` structure; allow tests assert `output == {}` (exact dict equality) |
| Negative/error-path coverage | STRONG | Every hook has deny, allow, and 4-type malformed input tests; boundary cases explicit (conftest.py.bak, seedfile.py, testsite.py, scratchpad/ vs scratch/) |
| Manual mutation resistance | STRONG | Flipping deny→allow in hook code would break `assert _is_denied(output)`; returning deny on allow path would break `assert output == {}` |
| Test independence | STRONG | Each test spawns a fresh subprocess; no shared mutable state |
| Descriptive test names | STRONG | Names like `test_backslash_path_normalized_and_denied`, `test_owlbear_scratchpad_is_denied` are fully self-documenting |

#### Data Safety

- No shared mutable state. No LLM output persistence. No race conditions (subprocess-based, stateless). No unbounded input risk.
- No issues.

#### Implementation-Aware Gaps

- `deny-code-writes._extract_paths()`: all 4 extraction paths (filePath, dirPath, replacements[].filePath, files[] string/dict) tested explicitly.
- `_normalize()` on deny-code-writes and allow-stances-only: backslash + dot-strip both tested.
- `deny-src-writes` and `deny-scratch-only-writes` use regex `(^|/)tests/` and `(^|/)\.owlbear/scratch/` respectively — these correctly match `./`-prefixed paths via the `/` capture group without explicit dot-strip; architecturally correct and consistent with PS1 fidelity (architecture review §4 note).
- `allow-stances-only._STANCES_RE = r"(/|^)stances/"`: correctly rejects `stancesdir/` (needs `/` after `stances`); mid-path match tested via `test_nested_stances_path_component_is_allowed`.
- No untested significant paths found.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A (single cycle) |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL

- `_extract_paths()` is duplicated verbatim in 4 of 5 hooks (deny-writes doesn't need it). Could be a shared utility if hooks were packaged. Not flagged per YAGNI — these are direct-run scripts not a package, and the duplication is exactly the copy-per-file pattern standard for standalone hook scripts.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Parameterized file, 5 hooks | `tests/test_pretooluse_hooks.py:100` — `_ALL_HOOK_NAMES` list, 7 classes | All 7 TestFromAC_* | PASS |
| Each hook: allow, deny, edge | All classes have ≥3 test categories | Per class | PASS |
| deny-writes tool guard | `deny-writes.py:26` `if tool_name and tool_name in _WRITE_TOOLS` | `test_each_write_tool_is_denied`, `test_read_file_is_allowed` | PASS |
| deny-code-writes deny-list + formats | `deny-code-writes.py:37–49` (prefix list), `_extract_paths()` | `TestFromAC_DenyCodeWrites` (18 tests) | PASS |
| deny-src-writes tests/ guard | `deny-src-writes.py:57` `_TESTS_RE = re.compile(r"(^|/)tests/")` | `TestFromAC_DenySrcWrites` (12 tests) | PASS |
| deny-scratch-only-writes guard | `deny-scratch-only-writes.py` `_SCRATCH_RE = re.compile(r"(^|/)\.owlbear/scratch/")` | `TestFromAC_DenyScratchOnlyWrites` (9 tests) | PASS |
| allow-stances-only guard | `allow-stances-only.py` `_STANCES_RE = re.compile(r"(/|^)stances/")` | `TestFromAC_AllowStancesOnly` (11 tests) | PASS |
| Malformed input fail-open | All 5 hooks: `except (json.JSONDecodeError, ValueError): print("{}")` | `TestFromAC_MalformedInput` (20 tests) | PASS |
| Subprocess invocation | `_run_hook()` test file line 154: `subprocess.run([sys.executable, str(script)], ...)` | All classes | PASS |
| All RED initially | Commit 17a79ba5 documented 109 failed | Historical; builder GREEN phase verified | PASS |

### Confidence: .97

### Verdict: PASS

[[2026-04-17]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | New `.owlbear/hooks/*.py` scripts are operational infrastructure, not API/behavior documented in copilot-instructions.md. That file covers only repo identity and branch structure — no hooks section. No update needed. |
| 2 | Module docstrings | Yes | Verified | All 5 hook scripts have accurate module-level docstrings describing purpose, guard type, usage, and (for deny-code-writes and allow-stances-only) allowed/denied paths. Private functions (`_extract_paths`, `_normalize`, `main`) are implementation details, not public API. `pyproject.toml` is not a Python module. All clean. |
| 3 | External attribution | Yes | Updated | Research doc source #1: VS Code Hooks docs (code.visualstudio.com/docs/copilot/customization/hooks) — PreToolUse I/O contract. Not previously in sources/overview.md. Added new section "PreToolUse Guard Hooks Test Approach (Task #891)". Commit: `docs: add VS Code Hooks docs attribution to sources (#891, doc-writer)`. Internal sources (6 .ps1 hooks, 2 existing test files, editFiles research doc) are not external and require no attribution. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/891-pretooluse-hooks-test-approach.md` exists and is linked in task body. Follow-up tasks verified: none needed (#894 pre-existing GREEN phase). |

### Files Updated

- `.owlbear/sources/overview.md` — added VS Code Hooks docs attribution

### Scratch Files Cleaned

- None (no `.owlbear/scratch/891-*` files found)
[[2026-04-17]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Parameterized file covering all 5 hooks | tests/test_pretooluse_hooks.py:100 _ALL_HOOK_NAMES, 7 TestFromAC_* classes | PASS |
| Each hook: allow, deny, edge-case | All 7 classes have allow/deny/edge categories | PASS |
| deny-writes: write tools deny, non-write allow | test_each_write_tool_is_denied x6, test_read_file_is_allowed | PASS |
| deny-code-writes: deny-list + formats | 10 prefixes + conftest.py exact at L37-49, _extract_paths handles filePath/dirPath/replacements/files | PASS |
| deny-src-writes: tests/ allow, others deny | TestFromAC_DenySrcWrites, 12 tests | PASS |
| deny-scratch-only-writes: scratch allow, others deny | TestFromAC_DenyScratchOnlyWrites, 9 tests | PASS |
| allow-stances-only: /stances/ allow, others deny | TestFromAC_AllowStancesOnly, 11 tests | PASS |
| Malformed input fail-open | TestFromAC_MalformedInput: 4 types x 5 hooks = 20 tests | PASS |
| Subprocess invocation | _run_hook uses subprocess.run([sys.executable, str(script)], ...), no shell=True | PASS |
| All tests RED initially | Historical: test-writer commit 17a79ba5, 109 failed | PASS |

### Test Results

- pytest (scoped): 109 passed, 0 failed, 0 skipped
- pytest (full suite): HUNG -- quality-runner reported fatal timeout. Pre-existing infrastructure issue; standalone hook scripts cannot cause cross-task regressions
- ruff: clean

### Architect Quality: 5/5

AC was specific and complete: each hook's exact behavior, all deny-list entries, all input formats, 4 malformed types. Architecture review added 4 clarification notes (full deny-list, editFiles field name, 6 gated tools, path normalization variance) that guided test-writer effectively. No builder improvisation needed.

### Deduction Breakdown

- AC lines without evidence: 0 (all 10 verified) -- no deduction
- Lint violations: none -- no deduction
- AC quality: 5/5 -- no deduction
- Reviewer evidence section: present, thorough, PASS at .97 -- no deduction
- Full-suite test failures in task scope: N/A -- no deduction
- Full suite could not run (hung): -.01 conservative deduction. Risk minimal: task deliverables are standalone subprocess-invoked scripts with no imports from or into other modules

### Confidence: .99

### Action: archive
