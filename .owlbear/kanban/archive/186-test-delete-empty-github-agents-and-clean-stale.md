---
id: 186
title: 'Test: Delete empty .github/agents/ and clean stale settings'
status: archived
priority: medium
created: 2026-03-29 20:38:21.691583+02:00
updated: 2026-03-30 00:41:33.933509+02:00
started: 2026-03-29 20:38:40.349575+02:00
completed: 2026-03-30 00:41:33.600646+02:00
tags:
- phase-1
- scope:docs
- type:test
- test
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Write RED-phase tests asserting .github/agents and .github/instructions paths are absent from setup.py output (they will fail until #166 cleans them up).

## AC
- [ ] In tests/test_setup_script.py, modify `test_agent_files_locations_has_root_and_github_paths`: assert `.github/agents` is NOT in `agentFilesLocations` keys. Rename to `test_agent_files_locations_has_root_path_only`. Test must FAIL against current setup.py.
- [ ] In tests/test_setup_script.py, modify `test_instructions_locations_has_root_and_github_paths`: assert `.github/instructions` is NOT in `instructionsFilesLocations` keys. Rename to `test_instructions_locations_has_root_path_only`. Test must FAIL against current setup.py.
- [ ] Both modified tests fail (RED) when run against unmodified setup.py
- [ ] All other tests in test_setup_script.py still pass (no collateral damage)

## Context
Paired RED phase for #166. Existing tests assert the opposite (paths present). Flip assertions so they fail now, pass after #166 cleanup. See docs/research/github-v1-cleanup.md sec 3.

## Files touched
- tests/test_setup_script.py (modify 2 test methods)

[[2026-03-29]] Sun 21:02
## Test-Writer Notes
- Test file: tests/test_setup_script.py
- Modified: test_agent_files_locations_has_root_path_only, test_instructions_locations_has_root_path_only
- Total: 2 tests, all FAIL against current setup.py (RED confirmed)
- ruff: clean
- 58 other tests PASS

[[2026-03-29]] Sun 22:06
## Builder Notes
- Files changed: scripts/setup.py (2 deletions — removed .github/agents and .github/instructions entries)
- Tests: 60 passed, 0 failed (test_setup_script.py)
- Lint: ruff clean (tests/, scripts/)
- Evidence: RED confirmed 2 failures, GREEN after removing stale .github paths from owlbear_keys dict
- Fixes applied: None — minimal surgical change

[[2026-03-29]] Sun 23:32
## Review Evidence

### Test Results
- pytest: 60 passed, 0 failed (tests/test_setup_script.py)

### Lint Results
- ruff: All checks passed! (scripts/, tests/test_setup_script.py)

### Coverage
- create_vscode_settings fully exercised by all TestFromAC_VscodeSettings tests (function called on every test path through the suite)

### RED Phase Verification
- Pre-builder setup.py (commit 4363856^) confirmed: contained `.github/agents` and `.github/instructions` in owlbear_keys dict
- Tests with `assert not has_github` would have FAILed against original setup.py â€” RED phase valid

### Test-Writer Coverage Table

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| Rename and flip .github/agents assertion | test_agent_files_locations_has_root_path_only | Yes â€” asserts not has_github, fails if .github/agents present | COVERED |
| Rename and flip .github/instructions assertion | test_instructions_locations_has_root_path_only | Yes â€” asserts not has_github, fails if .github/instructions present | COVERED |
| Both tests RED against original setup.py | Both above on pre-builder code | Yes | COVERED |
| No collateral damage | 58 other tests unmodified, all pass | Yes | COVERED |

### TestFromAC Comparison (test-writer changes only, builder made no test modifications)

| Test | Change | Assessment |
|------|--------|------------|
| test_agent_files_locations_has_root_and_github_paths | Renamed + `assert has_github` flipped to `assert not has_github` | STRENGTHENED |
| test_instructions_locations_has_root_and_github_paths | Renamed + `assert has_github` flipped to `assert not has_github` | STRENGTHENED |

### Security Review
- No secrets, injection, path traversal, or deserialization risks
- Change is purely a dict key removal in create_vscode_settings â€” CLEAN

### Builder Implementation
- scripts/setup.py: removed `f{rel}/.github/agents` and `f{rel}/.github/instructions` from owlbear_keys dict â€” minimal surgical 2-line deletion

### Pass 2 â€” Informational
- test-writer did not commit tests/test_setup_script.py (no task #186 commit in test file log). The builder committed setup.py but not the test file. Both agents should have committed their respective files per pipeline protocol. Low risk since changes are correct and present in working tree.

### Verdict: PASS â€” confidence .93

[[2026-03-29]] Sun 23:56
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | setup.py description does not mention .github/agents or .github/instructions; removing stale dict entries has no docs impact |
| 2 | Docstrings | No | N/A | create_vscode_settings docstring remains accurate after 2-line surgical removal |
| 3 | sources/overview.md | No | N/A | No external patterns used in this TDD cleanup task |
| 4 | README.md | No | N/A | No CLI commands added or changed |
| 5 | Research doc | No | N/A | No research doc produced; docs/research/github-v1-cleanup.md is for paired task 166 and already exists |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/186-* files found)

[[2026-03-30]] Mon 00:41
## Audit

[[2026-03-30]] Mon 00:41
### AC Verification
- Rename+flip .github/agents assertion: test at L108, asserts not has_github - PASS
- Rename+flip .github/instructions assertion: test at L130, asserts not has_github - PASS
- Both tests RED against unmodified setup.py: Reviewer verified pre-builder commit - PASS
- No collateral damage: 60/60 passed - PASS

### Test Results
- pytest task-scoped: 60 passed, 0 failed
- pytest full suite: 870 passed, 64 failed (all pre-existing, none in test_setup_script.py)
- ruff: All checks passed

### Architect Quality
- AC specificity: Exact test renames, assertions, RED criterion. Score: 5/5

### Quality Gaps
- Test-writer did not commit test file. Auditor committed as orphaned leftover (b15c139).

### Confidence: .97
### Action: archive
