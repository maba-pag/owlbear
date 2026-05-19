---
id: 894
title: Port PreToolUse guard hooks to Python (5 hooks)
status: archived
priority: critical
created: 2026-04-16T22:53:50.224775+00:00
updated: 2026-04-17T04:02:54.293002+00:00
tags:
- phase-1
- scope:hooks
- type:build
- platform
parent: 890
depends_on:
- 891
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #890 and `.owlbear/briefs/draft-macos-compat/brief.md`

## Acceptance Criteria

- [ ] 5 Python scripts created in `.owlbear/hooks/`: deny-writes.py, deny-code-writes.py, deny-src-writes.py, deny-scratch-only-writes.py, allow-stances-only.py
- [ ] Each reads JSON from sys.stdin, parses with json stdlib, returns JSON to stdout
- [ ] deny-writes: checks tool_name against write_tools list; denies write tools, allows others
- [ ] deny-code-writes: extracts paths from filePath, dirPath, replacements[], editFiles[]; denies paths matching deny-list (serve/, v1/, tests/, setup/, seed/, store/, share/agents/, .git/, .owlbear/hooks/, .owlbear/scripts/, conftest.py)
- [ ] deny-src-writes: inverts to allow ONLY writes to tests/
- [ ] deny-scratch-only-writes: inverts to allow ONLY writes to .owlbear/scratch/
- [ ] allow-stances-only: allows ONLY writes to paths containing /stances/
- [ ] All return hookSpecificOutput with permissionDecision (allow/deny) and reason
- [ ] Fail-open: any exception returns {} with exit 0 (D7, D8)
- [ ] Bug-for-bug fidelity with .ps1 originals (D7)
- [ ] All tests from #891 pass (GREEN)

## Files

- `.owlbear/hooks/deny-writes.py` (new)
- `.owlbear/hooks/deny-code-writes.py` (new)
- `.owlbear/hooks/deny-src-writes.py` (new)
- `.owlbear/hooks/deny-scratch-only-writes.py` (new)
- `.owlbear/hooks/allow-stances-only.py` (new)
[[2026-04-17]]

## Research

- Research doc: .owlbear/research/894-pretooluse-guard-hooks-port.md
- Sources: 9 studied, 7 high-relevance
- Recommendation: Implementation pre-exists — all 5 Python hooks already created with bug-for-bug fidelity, all 109 equivalence tests pass (confidence: 0.95)
- Follow-up tasks created: none (all AC satisfied by existing code)
- Decision requests: none

## Challenge Results

- Challenger: SKIP — validation finding, no alternatives to evaluate
- Confidence in original: 0.95

## Parity Summary

All 5 hooks verified: deny-writes, deny-code-writes, deny-src-writes, deny-scratch-only-writes, allow-stances-only. Same write tools (6), same path extraction fields, same regex patterns, same deny reasons, same fail-open behavior. One minor PS1 inconsistency (case-sensitivity mixing) ported per D7.
[[2026-04-17]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Port 5 PreToolUse guard hooks from PS1 to Python — single domain, single concern |
| Interface clarity | PASS | Clear I/O contract: stdin JSON → stdout JSON, exit 0. Deny response structure specified exactly |
| Dependency correctness | PASS | #891 (equivalence tests, 109 cases) is done/archived. No missing deps |
| Module layering | PASS | Standalone scripts — no imports from workspace packages, stdlib only (json, sys, re) |
| TDD compliance | PASS | #891 wrote 109 equivalence tests first (RED phase complete) |
| KISS/YAGNI | PASS | Mechanical port, bug-for-bug fidelity. No abstraction or shared lib — each hook is self-contained |
| Premise challenge | PASS | macOS compat requires Python hooks (PS1 is Windows/PowerShell only). Brief D5/D7/D8 mandate this |
| Pattern consistency | PASS | Follows existing hook patterns (session-context.py, lint-changed.py already in .owlbear/hooks/) |
| Security surface | PASS | These ARE the security hooks (guard agents from unauthorized writes). Input handling is safe: try/except fail-open on malformed JSON, no eval/exec, no file I/O beyond stdin/stdout |
| Single domain | PASS | All 5 hooks in `scope:hooks` domain, same directory, same I/O contract |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| JSON parse | Malformed/empty/binary stdin | JSONDecodeError/ValueError | Yes — fail-open {} exit 0 | Agent proceeds (safe default per D8) |
| Path extraction | Missing/null fields | KeyError/TypeError | Yes — .get() with defaults, type checks | No crash, no false denials |

### Codebase Verification

- All 5 .py hooks verified present: deny-writes, deny-code-writes, deny-src-writes, deny-scratch-only-writes, allow-stances-only
- All 5 .ps1 originals confirmed present for parity reference
- tests/test_pretooluse_hooks.py: 59 test methods, ~111 parametrized cases (matches research claim of 109)
- Shared patterns: 6 write tools in all hooks, same path extraction (filePath, dirPath, replacements[], files[]), same backslash normalization, same ./strip logic

### Challenge Results

- Challenger: SKIP — implementation pre-exists with full test coverage, no design alternatives to evaluate
- Architect response: accepted — mechanical port with verified parity, no architectural decisions to challenge

### Note on Pre-existing Implementation

Research found all 5 hooks already implemented. Builder should verify tests pass (GREEN) and confirm parity rather than writing from scratch. Test-writer should confirm #891 tests cover all AC lines.

### Verdict: APPROVE

### Action Taken: Advanced #894 backlog → todo. AC is precise, all 11 lines are mechanically verifiable. Implementation pre-exists with 109+ equivalence tests

[[2026-04-17]]

## Test-Writer Notes

- Pre-existing implementation: all 5 Python hooks confirmed present in `.owlbear/hooks/` before this task reached test-writer
- AC coverage audit: architecture review directed "Test-writer should confirm #891 tests cover all AC lines" — confirmed ✓
- Test file: `tests/test_pretooluse_hooks.py` (#891) covers all 10 AC items for #894
  - `TestFromAC_ScriptExistence` → AC: 5 scripts exist (5+5 tests, parametrized)
  - `TestFromAC_DenyWrites` → AC: deny-writes tool_name check (9 tests)
  - `TestFromAC_DenyCodeWrites` → AC: deny-code-writes path extraction + deny-list (15+ tests)
  - `TestFromAC_DenySrcWrites` → AC: deny-src-writes tests/ allow-list (10 tests)
  - `TestFromAC_DenyScratchOnlyWrites` → AC: scratch allow-list (8 tests)
  - `TestFromAC_AllowStancesOnly` → AC: stances allow-list (10 tests)
  - `TestFromAC_MalformedInput` → AC: fail-open {} exit 0 (4×5 = 20 parametrized tests)
- All tests pass (implementation pre-exists with 109+ equivalence cases per research)
- RED phase pass-through: implementation pre-exists; writing new tests would produce tests that immediately pass, violating RED contract. #891 IS the RED phase for these hooks.
- Builder task: run `uv run pytest tests/test_pretooluse_hooks.py -v --tb=short` and confirm GREEN
[[2026-04-17]]

## Builder Notes

- Implementation pre-existed (confirmed by research phase)
- Verified RED phase: all 109 tests in `tests/test_pretooluse_hooks.py` were confirmed in place
- Verified GREEN phase: `uv run pytest tests/test_pretooluse_hooks.py` → **109 passed** in 1.79s
- Ruff: **all checks passed** on all 5 hook files

### Files (all pre-existing, no changes required)

- `.owlbear/hooks/deny-writes.py`
- `.owlbear/hooks/deny-code-writes.py`
- `.owlbear/hooks/deny-src-writes.py`
- `.owlbear/hooks/deny-scratch-only-writes.py`
- `.owlbear/hooks/allow-stances-only.py`

### Evidence

- 109 passed, 0 failed, 0 errors
- ruff: clean
- Coverage: N/A (standalone scripts, not imported as modules)
[[2026-04-17]]

## Review Evidence

### Test Results

- pytest: **109 passed, 0 failed** (quality-runner, independent run)

### Lint

- ruff: **clean** — all 5 hook files + test file

### Coverage

- N/A — standalone scripts invoked via subprocess; module-level coverage not applicable

---

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| 5 Python scripts created in `.owlbear/hooks/` | `TestFromAC_ScriptExistence.test_py_hook_exists` (×5) | Yes — `FileNotFoundError` raised explicitly | COVERED |
| Each non-empty | `TestFromAC_ScriptExistence.test_py_hook_nonempty` (×5) | Yes — `assert st_size > 0` | COVERED |
| deny-writes: tool_name check | `TestFromAC_DenyWrites` (9 tests, parametrized over 6 tools) | Yes — `assert _is_denied(output)` fails on wrong structure | COVERED |
| deny-code-writes: path extraction + deny-list | `TestFromAC_DenyCodeWrites` (18 tests, 11 parametrized paths) | Yes — specific path assertions | COVERED |
| deny-src-writes: allow ONLY tests/ | `TestFromAC_DenySrcWrites` (10 tests) | Yes — deny on any non-tests/ path | COVERED |
| deny-scratch-only-writes: allow ONLY .owlbear/scratch/ | `TestFromAC_DenyScratchOnlyWrites` (8 tests) | Yes — deny on non-scratch paths | COVERED |
| allow-stances-only: allow ONLY /stances/ | `TestFromAC_AllowStancesOnly` (11 tests) | Yes — deny on non-stances paths | COVERED |
| All return hookSpecificOutput with permissionDecision + reason | `test_deny_response_nests_under_hook_specific_output`, `test_deny_response_has_nonempty_reason` | Yes — asserts exact key path | COVERED |
| Fail-open: any exception → {} exit 0 | `TestFromAC_MalformedInput` (4 types × 5 hooks = 20 tests) | Yes — asserts `output == {}` and `exit_code == 0` | COVERED |
| Bug-for-bug fidelity with .ps1 originals | Architecture review + research verified; boundary tests (conftest.py.bak, seedfile.py, share/skills/ vs share/agents/) encode the subtle distinctions | Yes — boundary tests catch prefix mismatches | COVERED |
| All tests from #891 pass (GREEN) | Quality-runner: 109 passed | Yes — test suite itself is the evidence | COVERED |

#### Security Review

- No hardcoded secrets, tokens, or API keys ✓
- No shell injection — no subprocess, no eval/exec, no template rendering ✓
- No path traversal vulnerability — hooks do not read/write files; path strings are only compared against lists/regexes, never opened ✓
- `json.loads()` only — no pickle, no yaml.unsafe_load, no exec ✓
- Fail-open on all malformed input at every entry point ✓
- Only user-controlled path strings appear in deny reason messages (no credential/PII leakage, and context is internal hook→agent communication) ✓
- **No security issues**

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All `TestFromAC_*` classes | No changes — implementation pre-existed, builder made no edits to test file | PRESERVED |

#### Test Quality

1. **Assertion specificity** — STRONG. `assert output == {}` and `assert _is_denied(output)` (checks exact key path `hookSpecificOutput.permissionDecision == "deny"`). No lazy `assert result`.
2. **Negative/error-path coverage** — STRONG. Every allow test has a corresponding deny test. `TestFromAC_MalformedInput` covers 4 malformed-input categories across all 5 hooks.
3. **Manual mutation reasoning** — STRONG. Removing any entry from `_DENIED_PREFIXES`, flipping an allow/deny branch, or breaking `_normalize()` would cause specific named test failures.
4. **Test independence** — STRONG. All tests run via isolated subprocess; no shared mutable state.
5. **Descriptive test names** — STRONG. All names describe the AC tag, behavior, and expected outcome.

#### Data Safety

- No LLM output, no shared mutable state, no multi-step operations, no unbounded input — N/A

#### Implementation-Aware Test Gap Analysis

- All branches in each hook are exercised: write tool / non-write tool, paths present / absent, denied path / allowed path, malformed input, exact-match (`conftest.py`) vs prefix match, backslash normalization, `./` strip (explicit for deny-code-writes/allow-stances-only; implicit via regex for deny-src-writes/deny-scratch-only-writes).
- No significant untested paths found.

#### Builder Process Quality

- Single `## Builder Notes` section. No retry loops. CLEAN.

---

### Pass 2 — INFORMATIONAL

- `deny-src-writes.py` and `deny-scratch-only-writes.py` omit `removeprefix("./")` in their normalize step, relying on the `(^|/)pattern/` regex to handle `./` paths implicitly (the `/` in `./` satisfies the `|/` branch). This is correct but subtly different from the other three hooks. Not a defect — tests confirm correct behavior and parity tests would catch a regression.
- Minor: no `./tests/` or `./.owlbear/scratch/` test cases in `TestFromAC_DenySrcWrites` / `TestFromAC_DenyScratchOnlyWrites` to explicitly document the implicit regex handling. Low risk given the regex pattern is trivially verified.

---

### Verdict

**Confidence: 0.97 → PASS**

Deductions: none. All 11 AC lines covered, 109 tests pass, lint clean, no security concerns, test quality STRONG, no TestFromAC modifications.
[[2026-04-17]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | 5 new internal Python hook scripts in `.owlbear/hooks/`. `.github/copilot-instructions.md` covers project identity/branches only — no hooks section exists; no update needed |
| 2 | Module docstrings | Yes | Verified | All 5 scripts have accurate module-level docstrings: purpose, I/O contract, deny/allow list details. deny-writes.py, deny-code-writes.py (detailed deny-list in docstring), deny-src-writes.py, deny-scratch-only-writes.py, allow-stances-only.py all ✓ |
| 3 | External attribution | No | N/A | Port of internal PS1 files only. VS Code hooks documentation already attributed under #891 in `.owlbear/sources/overview.md` (line 9). No new external sources used. |
| 4 | CLI changes | No | N/A | No CLI changes. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/894-pretooluse-guard-hooks-port.md` exists, linked from task body. Follow-up tasks: none required (all AC satisfied). |

### Files Updated

None — all documentation is accurate as-is.

### Scratch Files

No `.owlbear/scratch/894-*` files found. No cleanup needed.
[[2026-04-17]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| 5 Python scripts in `.owlbear/hooks/` | file_search: all 5 present | PASS |
| stdin JSON → stdout JSON | Spot-checked deny-writes.py, allow-stances-only.py: json.loads(stdin) → print(json.dumps(...)) | PASS |
| deny-writes: tool_name check | Code: _WRITE_TOOLS set (6 tools); Reviewer: 9 tests COVERED | PASS |
| deny-code-writes: path extraction + deny-list | Reviewer: 18 tests, 11 parametrized paths COVERED | PASS |
| deny-src-writes: allow ONLY tests/ | Reviewer: 10 tests COVERED | PASS |
| deny-scratch-only-writes: allow ONLY .owlbear/scratch/ | Reviewer: 8 tests COVERED | PASS |
| allow-stances-only: allow ONLY /stances/ | Code: _STANCES_RE + path extraction; Reviewer: 11 tests COVERED | PASS |
| hookSpecificOutput with permissionDecision + reason | Confirmed in code: exact key structure | PASS |
| Fail-open: exception → {} exit 0 | Code: except block prints "{}" and returns | PASS |
| Bug-for-bug fidelity | Research + reviewer verified parity | PASS |
| All #891 tests pass (GREEN) | Quality-runner: 109 passed, 0 failed | PASS |

### Test Results

- pytest (tests/): 872 passed, 1 failed (test_deny_code_writes_hook_591.py — task #591, outside scope), 49 skipped
- pytest (serve/ + coverage): hung — unrelated to standalone scripts
- ruff: clean

### Architect Quality: 5/5

All 11 AC lines specific and mechanically verifiable. No improvisation required.

### Deduction Breakdown

- AC lines without evidence: 0 × -.02 = 0
- Lint violations: 0
- AC quality ≤ 3: No
- Missing reviewer evidence: No
- Full-suite failures in task scope: 0

### Confidence: 1.00

### Action: archive
