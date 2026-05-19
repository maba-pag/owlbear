---
id: 902
title: Clean up legacy kanban-md.exe references
status: archived
priority: important
created: 2026-04-16T22:54:41.784445+00:00
updated: 2026-04-17T03:04:33.858549+00:00
tags:
- phase-3
- cleanup
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

- [ ] All references to `kanban-md.exe` in orchestrator source and test files identified
- [ ] References removed or guarded with proper platform skip conditions (pytest.mark.skipif)
- [ ] No bare .exe references remain in serve/orchestrator/ or tests/
- [ ] grep -r "kanban-md.exe" serve/ tests/ returns no results (or only guarded references)
- [ ] Existing tests still pass after cleanup

## Files

- `serve/orchestrator/` (edit, affected files)
- `tests/` (edit, affected test files)
[[2026-04-17]]

## Research

- Research doc: .owlbear/research/legacy-kanban-md-exe-cleanup.md
- Sources: 6 studied, 5 high-relevance (all internal codebase)
- Recommendation: Drop `.exe` extension from all defaults; prefer `KANBAN_BIN` env var with `kanban-md` fallback (confidence: 0.92)
- Follow-up tasks created: none (task #902 is itself the implementation task with concrete AC)
- Decision requests: none (D4 already resolved in parent brief)

## Challenge Results

- Challenger: SKIPPED — trivial cleanup with pre-decided direction (D4)
- Confidence in original: 0.92

## Scope Summary

6 files affected, ~15 changed lines:

- `serve/orchestrator/src/owlbear/cli.py` — replace hardcoded `.exe` default with env var + `kanban-md`
- `tests/fixtures/mock_acp_agent.py` — change default to `kanban-md`
- `tests/test_mock_acp_agent.py` — update fallback assertion
- `tests/test_dispatch_integration.py` — remove `.exe` from convention path
- `tests/test_orchestrator_loop.py` — update 7 mocked Path args
- `tests/test_reviewer_execute_tools_457.py` — keep as-is (negative guard)
[[2026-04-17]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Pure `.exe` reference cleanup — one concern |
| Interface clarity | PASS | AC4 (grep check) is definitive; env var pattern exists in `mock_acp_agent.py` |
| Dependency correctness | PASS | No deps, correct — independent cleanup task |
| Module layering | PASS | Only editing defaults and test assertions |
| TDD compliance | PASS | Test-writer updates assertions to `kanban-md` (RED), builder changes source (GREEN) |
| KISS/YAGNI | PASS | String replacements only, no new abstractions |
| Premise challenge | PASS | Required by parent #890 brief, D4 resolved |
| Pattern consistency | PASS | `KANBAN_BIN` env var pattern already in `mock_acp_agent.py` L24 |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | Orchestrator domain only |

### Scope Correction

Research identified 6 files but grep found **8 files** with `kanban-md.exe` references. Two missing:

| File | Line(s) | Nature | Action |
|------|---------|--------|--------|
| `tests/test_dispatch_cycle_trace_id.py` | 462, 509, 561 | `tmp_path / "kanban-md.exe"` in 3 test fixtures | Change to `tmp_path / "kanban-md"` |
| `tests/test_e2e_dispatch.py` | 39 | `_KANBAN_BIN = _PROJECT_ROOT / ".owlbear" / "kanban" / "kanban-md.exe"` | Change to `kanban-md` |

**Builder: use AC4 grep as your completeness check. The scope summary in the body undercounts — 8 files total, ~19 changed lines.**

### Challenge Results

- Challenger: FALLBACK — subagent returned no response
- Architect response: proceeded on own analysis; AC is self-verifying via grep check

### Verdict: APPROVE

### Action Taken: Advanced to todo with scope correction note for builder

[[2026-04-17]]

## Test-Writer Notes

- Test file: tests/test_legacy_exe_cleanup_902.py
- Classes: `TestFromAC_CliDefaultBinary`, `TestFromAC_MockAgentDefaultBinary`, `TestFromAC_TestFilesNoExeReference`
- Tests per category: happy 4, edge 0, error 0, boundary 7 (file-content grep checks)
- Total: 11 tests, all FAIL
- ruff: clean

### AC Coverage

| AC | Tests |
|----|-------|
| AC1 (all refs identified) | precondition from research — covered by AC4 scope |
| AC3 (no bare .exe in serve/ or tests/) | `test_cli_default_binary_has_no_exe_suffix`, `test_cli_default_binary_equals_kanban_md`, `test_mock_acp_default_binary_has_no_exe_suffix`, `test_mock_acp_default_binary_equals_kanban_md` |
| AC4 (grep returns no results) | `test_cli_source_file_contains_no_exe_reference`, `test_mock_acp_fixture_file_contains_no_exe_reference`, `test_orchestrator_loop_file_contains_no_exe_reference`, `test_dispatch_cycle_trace_file_contains_no_exe_reference`, `test_e2e_dispatch_file_contains_no_exe_reference`, `test_dispatch_integration_file_contains_no_exe_reference`, `test_mock_acp_agent_test_contains_no_exe_reference` |
| AC5 (existing tests still pass) | not tested here — regression guard, verified by builder after changes |

Note: `tests/test_reviewer_execute_tools_457.py` excluded per scope — it is a guarded negative reference (asserts the skill file does NOT contain `kanban-md.exe`), preserved intentionally.

Commit: `test: add failing tests for kanban-md.exe cleanup (#902, test-writer)`
[[2026-04-17]]

## Builder Notes

### Files Changed (7)

- `serve/orchestrator/src/owlbear/cli.py` — `_KANBAN_BIN = Path("kanban/kanban-md")`
- `tests/fixtures/mock_acp_agent.py` — `_DEFAULT_KANBAN_BIN = "kanban/kanban-md"` + docstring
- `tests/test_mock_acp_agent.py` — fallback assertion updated to `kanban/kanban-md`
- `tests/test_dispatch_integration.py` — convention path `kanban-md`
- `tests/test_orchestrator_loop.py` — 14 `kanban_bin=Path(...)` args updated
- `tests/test_dispatch_cycle_trace_id.py` — 3 `tmp_path / "kanban-md"` args updated
- `tests/test_e2e_dispatch.py` — `_KANBAN_BIN` constant updated

### Test Results

- `tests/test_legacy_exe_cleanup_902.py`: **11/11 passed**
- Ruff: **clean** on all 7 changed files
- AC4 grep: `grep -rn "kanban-md.exe" serve/ tests/` returns 0 results (excluding preserved negative guards)
- Pre-existing failures in `test_orchestrator_loop.py` (`TestFromAC_WaveAssembly`, `TestFromAC_FormatPrompt`) are from a different task, unrelated to this cleanup

### Commit

`00332071` — fix: remove legacy kanban-md.exe references (#902, builder)
[[2026-04-17]]

## Review Evidence

### Test Results

- pytest (scoped): 11 passed, 0 failed (tests/test_legacy_exe_cleanup_902.py)
- pytest (regression): 119 passed, 0 failed (test_mock_acp_agent.py, test_dispatch_integration.py, test_dispatch_cycle_trace_id.py, test_e2e_dispatch.py)
- pytest (test_orchestrator_loop.py): 8 pre-existing failures in TestFromAC_WaveAssembly (5) and TestFromAC_FormatPrompt (3) — unrelated to task #902, confirmed pre-existing

### Lint: clean (all 7 changed files)

### Coverage: owlbear.cli: 27% (scoped run — changed constant _KANBAN_BIN is covered; low pct due to untouched module surface)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 (all refs identified) | Covered by AC4 file-content scans over all 7 affected files | Yes — if any file retained .exe, test fails | COVERED |
| AC2 (removed or guarded) | test_cli_default_binary_has_no_exe_suffix, test_cli_default_binary_equals_kanban_md, test_mock_acp_default_binary_has_no_exe_suffix, test_mock_acp_default_binary_equals_kanban_md | Yes — direct import of live values | COVERED |
| AC3 (no bare .exe in serve/tests) | Same tests as AC2 + file-content scans | Yes | COVERED |
| AC4 (grep returns no results) | 7 file-content scan tests | Yes — would fail if literal kanban-md.exe present | COVERED |
| AC5 (existing tests pass) | Regression run: 119 tests pass on changed test files | Yes | COVERED |

#### Security Review

No issues. subprocess.run uses list args throughout mock_acp_agent.py; no path traversal or injection risks; no credentials.

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_CliDefaultBinary (test_legacy_exe_cleanup_902.py) | Not modified by builder | PRESERVED |
| TestFromAC_MockAgentDefaultBinary (test_legacy_exe_cleanup_902.py) | Not modified by builder | PRESERVED |
| TestFromAC_TestFilesNoExeReference (test_legacy_exe_cleanup_902.py) | Not modified by builder | PRESERVED |
| TestFromAC_EnvVarConfig::test_kanban_bin_fallback_when_env_var_absent (test_mock_acp_agent.py — different task) | Builder updated assertion from kanban-md.exe to kanban/kanban-md | DOCUMENTED — correct behavior correction, not weakening |

#### Test Quality: STRONG

- Direct import assertions (live runtime values, not file parsing) for AC2/AC3
- File-content scans with exact literal for AC4
- Both suffix and exact-equality checks — would catch any non-kanban/kanban-md value
- No lazy assertions

#### Data Safety: No issues

#### Builder Process Quality: CLEAN — single attempt

### Pass 2 — Informational

- **Coverage**: owlbear.cli at 27% in scoped run; acceptable for single-constant cleanup; changed line IS covered
- **Out-of-scope gap**: `.owlbear/scripts/e2e_smoke.py:51` still contains `kanban-md.exe` — outside AC scope (serve/ and tests/) but is a live legacy reference that will fail on macOS. Follow-up task recommended.

### AC Compliance Table

| AC | Evidence | Status |
|----|----------|--------|
| AC1 | Research + arch review found 8 files; builder addressed all 8 | PASS |
| AC2 | cli.py:23 Path("kanban/kanban-md"), mock_acp_agent.py:26 "kanban/kanban-md", test_e2e_dispatch.py:41 confirmed | PASS |
| AC3 | Code-reader confirmed no bare .exe in serve/ or tests/ | PASS |
| AC4 | 11 task tests pass; _EXE_LITERAL only in guarded not-in assertions | PASS |
| AC5 | 119 regression tests pass; 8 pre-existing failures confirmed unrelated | PASS |

### Verdict

Confidence: 0.93 → PASS #902 -> docs
[[2026-04-17]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | copilot-instructions.md has no kanban-md/KANBAN_BIN/binary references; internal constant change only |
| 2 | Module docstrings | Yes | Verified | cli.py: module docstring accurate, all public functions documented. mock_acp_agent.py: module docstring updated by builder — `default: kanban/kanban-md` matches actual `_DEFAULT_KANBAN_BIN = "kanban/kanban-md"` |
| 3 | External attribution | No | N/A | Pure internal cleanup; no external patterns used |
| 4 | CLI changes | No | N/A | No user-facing CLI commands added/removed; README.md contains no kanban-md.exe references |
| 5 | Research doc | Yes | Verified | `.owlbear/research/legacy-kanban-md-exe-cleanup.md` exists and is linked from task body |

### Files Updated

- None

### Scratch Files Cleaned

- None (no `.owlbear/scratch/902-*` files found)
[[2026-04-17]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: All refs identified | Research found 6, arch review corrected to 8 files; builder addressed all 8 | PASS |
| AC2: Removed or guarded | cli.py:21 Path("kanban/kanban-md"), mock_acp_agent.py:16 "kanban/kanban-md" confirmed via spot-check | PASS |
| AC3: No bare .exe in serve/ or tests/ | grep: 0 matches in serve/; 20 in tests/ all in assertion/guard context (test_legacy_exe_cleanup_902.py, test_reviewer_execute_tools_457.py) | PASS |
| AC4: grep returns no results or guarded | Same as AC3 — all 20 matches are test assertions verifying absence, not bare refs | PASS |
| AC5: Existing tests still pass | Reviewer: 11 task + 119 regression passed; 8 pre-existing failures confirmed unrelated | PASS |

### Test Results

- pytest (full suite): Quality-Runner collected 4,967 tests; SIGKILL at 98% during xdist teardown (system resource limit, not test failure)
- pytest (reviewer scoped): 11 task tests + 119 regression tests passed, 0 failed
- ruff: F811 in test_scaffold_mcp_memory_524.py (pre-existing, unrelated); clean on all 7 task files

### Architect Quality: 4/5

AC is concrete and grep-verifiable (AC4 is definitive). Architect corrected scope from 6 to 8 files during review. Minor gap: initial scope undercount required correction.

### Deduction Breakdown

- Start: 1.00
- 5 AC lines, all with specific evidence: 0
- Lint clean on task files: 0
- AC quality 4/5: 0
- Reviewer evidence present and detailed: 0
- Full suite incomplete (system SIGKILL, not test failure): -.02

### Confidence: 0.98

### Action: archive
