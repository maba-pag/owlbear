---
id: 827
title: Tests for single Agent construction in _build_agent
status: archived
priority: someday
created: 2026-03-15T12:41:55.8199541+01:00
updated: 2026-03-15T15:57:43.6475999+01:00
started: 2026-03-15T15:57:12.6925165+01:00
completed: 2026-03-15T15:57:12.6925165+01:00
tags:
    - test
    - scope:core
    - type:test
class: standard
---

Test task paired with #561. Verifies _build_agent constructs exactly one Agent per call.

## AC

- [ ] Test: validator role _build_agent calls Agent() exactly once (mock Agent constructor, assert call_count == 1)
- [ ] Test: builder role _build_agent calls Agent() exactly once
- [ ] Test: validator role _build_agent passes filtered toolsets to Agent()
- [ ] ruff clean

Target file: tests/test_agent_registry.py (extend existing TestBuildAgent* classes)

[[2026-03-15]] Sun 13:17

## Test-Writer Notes

- Test file: tests/test_agent_registry.py
- Classes: TestFromAC_SingleAgentConstruction
- Tests per category: happy 1 (builder regression), edge 0, error 0, boundary 2 (validator single-call, filtered toolsets)
- Total: 3 tests, 2 FAIL + 1 PASS (builder regression guard, AC-required)
- ruff: clean
- AC coverage:
| AC Line | Test(s) | Category |
|---------|---------|----------|
| validator calls Agent() once | test_validator_role_calls_agent_exactly_once | boundary |
| builder calls Agent() once | test_builder_role_calls_agent_exactly_once | happy (regression) |
| validator passes filtered toolsets | test_validator_role_passes_filtered_toolsets | boundary |
| ruff clean | ruff check passed | gate |

[[2026-03-15]] Sun 13:28

## Builder Notes

- Files changed: src/owlbear/core/agent_registry.py
- Tests: 19 passed, coverage 95% on agent_registry
- Lint: ruff clean
- Fix: moved role-policy filtering BEFORE Agent() construction

[[2026-03-15]] Sun 13:51

## Review Evidence

### Test Results

- pytest: 19 passed, 0 failed (test_agent_registry.py)
- ruff: All checks passed
- Coverage: agent_registry.py 95% (73 stmts, 4 missed)

### TestFromAC Comparison

- Builder commit (540d968) has ZERO diff on test file
- All 3 TestFromAC methods: PRESERVED

### Test Quality

| Dimension | Rating |
|-----------|--------|
| Assertion specificity | STRONG |
| Negative/error-path | ADEQUATE |
| Mutation reasoning | STRONG |
| Test independence | STRONG |
| Descriptive names | STRONG |

### Security: No concerns (pure refactor, no I/O, no user input)

### Data Safety: No concerns (construction logic only)

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| validator calls Agent() once | test_validator_role_calls_agent_exactly_once: call_count==1 | PASS |
| builder calls Agent() once | test_builder_role_calls_agent_exactly_once: call_count==1 | PASS |
| validator passes filtered toolsets | test_validator_role_passes_filtered_toolsets: identity checks | PASS |
| ruff clean | ruff check: All checks passed | PASS |

### Verdict: PASS (confidence .95)

### Action: move to docs

[[2026-03-15]] Sun 14:22

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Internal refactor of _build_agent ordering; no behavior/API/convention change |
| 2 | Docstrings | No | N/A | agent_registry.py has complete docstrings on module, class, all methods |
| 3 | sources/overview.md | No | N/A | No external patterns adopted |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No research phase for this test task |

**No docs impact.** Test task + internal refactor with no documentation implications.

### Files Updated

- None

### Scratch Files Cleaned

- None (no 827-* files in docs/scratch/)

[[2026-03-15]] Sun 15:56

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| validator calls Agent() once | test_agent_registry.py L296: patches Agent, call_count==1 | PASS |
| builder calls Agent() once | test_agent_registry.py L312: same pattern builder role | PASS |
| validator passes filtered toolsets | test_agent_registry.py L328: mocks apply_role_policy, filtered in kwargs | PASS |
| ruff clean | ruff check: All checks passed | PASS |

### Test Results

- pytest (scoped): 19 passed, 0 failed (test_agent_registry.py)
- pytest (full): pre-existing failures only (~51), same baseline as prior audits
- ruff: All checks passed

### Upstream Commits

- 540d968 fix: single Agent() construction in _build_agent (#827, builder)

### Confidence: .97

### Action: archive

[[2026-03-15]] Sun 15:56

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| validator calls Agent() once | test_agent_registry.py L296: patches Agent, call_count==1 | PASS |
| builder calls Agent() once | test_agent_registry.py L312: same pattern builder role | PASS |
| validator passes filtered toolsets | test_agent_registry.py L328: mocks apply_role_policy, filtered in kwargs | PASS |
| ruff clean | ruff check: All checks passed | PASS |

### Test Results

- pytest (scoped): 19 passed, 0 failed (test_agent_registry.py)
- ruff: All checks passed

### Upstream Commit: 540d968

### Confidence: .97

### Action: archive
