---
id: 201
title: Add tests for canonical tool registry validation
status: archived
priority: medium
created: 2026-03-30 03:21:27.761933+02:00
updated: 2026-04-01 20:30:53.784386+02:00
started: 2026-04-01 20:30:53.207286+02:00
completed: 2026-04-01 20:30:53.207286+02:00
tags:
- phase-1
- tooling
- test
depends_on:
- 198
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Add happy-path and parametrized regression tests for the canonical tool registry
validation in validate_agents.py (landed in #198). Current test suite covers error
paths only; these tests close the gap for valid-input paths.

## AC
- [ ] `test_valid_toolset_shorthand_passes` â€” `@pytest.mark.parametrize` over all 8 KNOWN_TOOLSETS members (agent, browser, edit, execute, read, search, web, vscode): `validate_agent()` on a tmp_path fixture with `tools: [{name}]` returns no errors
- [ ] `test_valid_prefixed_tool_passes` â€” `@pytest.mark.parametrize` over representative prefixed tools (execute/runInTerminal, read/readFile, vscode/memory, edit/createFile, search/semanticSearch): `validate_agent()` on a tmp_path fixture returns no errors
- [ ] `test_valid_standalone_tool_passes` â€” `@pytest.mark.parametrize` over KNOWN_STANDALONE_TOOLS (newWorkspace, selection): `validate_agent()` on a tmp_path fixture returns no errors
- [ ] `test_mcp_wildcard_pattern_passes` â€” `@pytest.mark.parametrize` over MCP patterns (owlbear-kanban/*, microsoft/markitdown/*): `validate_agent()` on a tmp_path fixture returns no errors
- [ ] `test_each_agent_file_passes_validation` â€” `@pytest.mark.parametrize(filename, <glob agents/*.agent.md>)` dynamically discovers agent files: `validate_agent(agents/{filename})` returns `[]`. No hardcoded file count
- [ ] All 47 pre-existing tests in test_validate_agents.py pass (regression)
- [ ] ruff clean on tests/test_validate_agents.py

## Patterns to follow
- Reuse existing `_write_agent` / `_agent_content` helpers for tmp_path fixtures
- Follow `test_rename_todo_to_todos.py` parametrize idiom (`AGENT_MD_FILES` list, `AGENTS_DIR` constant)
- New class: `TestFromAC_ValidToolPatterns` to group all happy-path tests

## Files to touch
- tests/test_validate_agents.py (~25 LOC: 1 new test class with 5 parametrized functions)

## Architecture Notes
- Tests validate existing `_is_valid_tool()` contract: toolset shorthand (a), prefix match (b), standalone (c), MCP wildcard (d)
- These tests should PASS immediately since #198 implementation exists. TDD RED phase produces passing tests (test-writer notes this as validating existing code)
- Parametrized per-agent test provides per-file failure isolation vs. existing aggregate integration test

See docs/research/test-canonical-tool-registry-coverage.md
See docs/research/canonical-tool-registry-validation.md

[[2026-04-01]] Wed 09:15
## Architecture Review
**Verdict:** APPROVED
**DR Verification:** N/A -- test coverage gap analysis, not T3 research

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| test_valid_toolset_shorthand_passes (8 params) | Precise: all KNOWN_TOOLSETS members, verifiable | Keep |
| test_valid_prefixed_tool_passes (5 params) | Precise: representative prefixed tools from actual agents | Keep |
| test_valid_standalone_tool_passes (2 params) | Precise: both KNOWN_STANDALONE_TOOLS members | Keep |
| test_mcp_wildcard_pattern_passes (2 params) | Precise: both MCP patterns currently in use | Keep |
| test_each_agent_file_passes_validation (dynamic) | Precise: discovers files dynamically, not hardcoded 11 | Refined from original |
| 47 pre-existing tests pass | Standard regression gate | Keep |
| ruff clean | Standard quality gate | Keep |

### Architecture Notes
Test-only task targeting a single module (validate_agents.py). All tests exercise the existing _is_valid_tool() contract: toolset shorthand (a), prefix match (b), standalone (c), MCP wildcard (d). No implementation code changes required.

Key refinements:
1. Removed 3 redundant AC items already covered by #198 TDD (unknown tools flagged, existing todo/resolveMemoryFileUri tests, ruff)
2. Fixed agent count: original said 11 files, now 13 (challenger.agent.md, code-reader.agent.md added). Parametrized test discovers dynamically
3. Specified test class name: TestFromAC_ValidToolPatterns
4. Added explicit helpers to reuse: _write_agent, _agent_content
5. Noted TDD RED inapplicability: tests validate existing code, should pass when written

Codebase verified: scripts/validate_agents.py (175 LOC), tests/test_validate_agents.py (747 LOC), tests/test_rename_todo_to_todos.py (parametrize pattern).

### Changes Made
- Rewrote AC: removed 3 redundant items, refined 4 remaining with test names, parametrization inputs, and expected behavior
- Fixed agent count (dynamic discovery instead of hardcoded 11)
- Added Patterns to follow and Files to touch sections
- Approved to todo

### Dependencies
- Verified: #198 (archived) -- KNOWN_TOOLSETS, _is_valid_tool(), _check_unknown_tools() all present on HEAD

### Challenge Results
Challenge: FALLBACK -- subagent network error (ERR_INCOMPLETE_CHUNKED_ENCODING)

[[2026-04-01]] Wed 14:37
## Test-Writer Notes
- Test file: tests/test_validate_agents.py
- Classes: TestFromAC_ValidToolPatterns
- Tests per category: happy 8+5+2+2+13=30 (all happy-path, no error tests needed)
- Total: 30 new parametrized tests, all PASS (validates existing #198 implementation)
- Pre-existing: 47 tests all still pass (77 total)
- ruff: clean
- Added import pytest at module level (first parametrize usage in this file)
- AC coverage:
  AC1 test_valid_toolset_shorthand_passes: 8 params (agent, browser, edit, execute, read, search, web, vscode)
  AC2 test_valid_prefixed_tool_passes: 5 params (execute/runInTerminal, read/readFile, vscode/memory, edit/createFile, search/semanticSearch)
  AC3 test_valid_standalone_tool_passes: 2 params (newWorkspace, selection)
  AC4 test_mcp_wildcard_pattern_passes: 2 params (owlbear-kanban/*, microsoft/markitdown/*)
  AC5 test_each_agent_file_passes_validation: 13 params (dynamic glob, all current agents/*.agent.md)
  AC6 regression: 47 pre-existing tests pass
  AC7 ruff: clean

[[2026-04-01]] Wed 15:49
## Builder Notes
- Files changed: none (test-only task; test-writer committed tests in d9ff053)
- Tests: 77 passed (47 pre-existing + 30 new TestFromAC_ValidToolPatterns)
- Lint: ruff clean on tests/test_validate_agents.py
- Evidence: uv run pytest tests/test_validate_agents.py -q --tb=short -> 77 passed in 1.45s
- Fixes applied: None -- tests were already committed and passing per #198 implementation

[[2026-04-01]] Wed 18:08
## Review Evidence

### Test Results
- pytest: 77 passed, 0 failed (all collected from tests/test_validate_agents.py)
- New tests (TestFromAC_ValidToolPatterns): 8+5+2+2+13 = 30
- Pre-existing: 47 (77-30 = 47) matches AC6 exactly

### Lint Results
- ruff: All checks passed!

### Coverage
- Test-only task; no source module changed; coverage N/A for new LOC

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage
AC1 test_valid_toolset_shorthand_passes (8 params): TestFromAC_ValidToolPatterns::test_valid_toolset_shorthand_passes -- asserts validate_agent() == [] for each shorthand -- would fail if shorthand not recognised: COVERED
AC2 test_valid_prefixed_tool_passes (5 params): TestFromAC_ValidToolPatterns::test_valid_prefixed_tool_passes -- asserts [] for each prefix/tool -- would fail if prefix match broken: COVERED
AC3 test_valid_standalone_tool_passes (2 params): TestFromAC_ValidToolPatterns::test_valid_standalone_tool_passes -- asserts [] for newWorkspace and selection: COVERED
AC4 test_mcp_wildcard_pattern_passes (2 params): TestFromAC_ValidToolPatterns::test_mcp_wildcard_pattern_passes -- asserts [] for owlbear-kanban/* and microsoft/markitdown/*: COVERED
AC5 test_each_agent_file_passes_validation (13 params): Dynamic glob agents/*.agent.md -- 13 files discovered (architect, auditor, builder, challenger, code-reader, curator, kanban-planner, orchestrator, planner, researcher, reviewer, test-writer, writer): COVERED
AC6 regression (47 pre-existing): 77 total - 30 new = 47 pre-existing, all pass: COVERED
AC7 ruff clean: Verified directly -- All checks passed!: COVERED

#### Security Review
No new source code added (test-only task). No security issues.

#### Test Integrity
Builder made no file changes (committed d9ff053 by test-writer unchanged). All TestFromAC_ValidToolPatterns methods PRESERVED.

#### Test Quality
Assertion specificity: STRONG -- all tests assert == [] (exact empty list, not just falsy)
Negative/error paths: N/A for this AC (happy-path-only class by design; error paths covered by pre-existing tests)
Mutation reasoning: STRONG -- each tool check feeds through _is_valid_tool(); if any category broke, the corresponding parametrized tests would fail
Test independence: STRONG -- each test creates its own tmp_path file; no shared state
Descriptive names: STRONG -- test_valid_toolset_shorthand_passes, test_valid_prefixed_tool_passes etc. are self-explanatory

#### Data Safety
No data safety issues (test-only, no source changes).

#### Implementation-Aware Test Gaps
No new implementation code introduced. Builder confirmed no files changed.

#### Builder Process Quality
Builder Notes sections: 1 (CLEAN -- single section, no retries)

### AC Compliance
AC1 8-param shorthand: test_valid_toolset_shorthand_passes at test_validate_agents.py:769 -- 8 pass: PASS
AC2 5-param prefixed: test_valid_prefixed_tool_passes at test_validate_agents.py:778 -- 5 pass: PASS
AC3 2-param standalone: test_valid_standalone_tool_passes at test_validate_agents.py:795 -- 2 pass: PASS
AC4 2-param MCP wildcard: test_mcp_wildcard_pattern_passes at test_validate_agents.py:801 -- 2 pass: PASS
AC5 dynamic agent files: test_each_agent_file_passes_validation at test_validate_agents.py:809 -- 13 agents discovered and all pass: PASS
AC6 47 pre-existing tests pass: 77 total minus 30 new = 47, all pass: PASS
AC7 ruff clean: ruff check tests/test_validate_agents.py returned All checks passed!: PASS

### Verdict: PASS
Confidence: .96

[[2026-04-01]] Wed 20:30
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 test_valid_toolset_shorthand_passes (8 params) | Verified L759-768, 8 parametrized pass | PASS |
| AC2 test_valid_prefixed_tool_passes (5 params) | Verified L771-785, 5 parametrized pass | PASS |
| AC3 test_valid_standalone_tool_passes (2 params) | Verified L788-793, 2 parametrized pass | PASS |
| AC4 test_mcp_wildcard_pattern_passes (2 params) | Verified L796-802, 2 parametrized pass | PASS |
| AC5 test_each_agent_file_passes_validation (dynamic) | Verified L805-813, 13 agents discovered, all pass | PASS |
| AC6 47 pre-existing tests pass | 77 total minus 30 new equals 47, all pass | PASS |
| AC7 ruff clean | All checks passed! | PASS |

### Test Results
- pytest (scoped): 77 passed in 1.22s
- pytest (full suite): 2625 passed, 194 failed (all failures from other tasks: quality-runner, rename, hooks, voice)
- ruff: All checks passed!

### Architect Quality
- AC specificity: Excellent. Named exact functions, parametrize inputs, expected behavior
- Edge case coverage: N/A (happy-path-only by design; error paths covered by #198 tests)
- Design direction: Architecture notes correctly identified TDD RED inapplicability
- AC quality score: 5/5

### Deduction breakdown: none (all AC verified with evidence, lint clean, AC quality 5, reviewer evidence thorough)
### Confidence: 1.0
### Action: archive

### Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| d9ff053 | test | tests/test_validate_agents.py | #201 |
