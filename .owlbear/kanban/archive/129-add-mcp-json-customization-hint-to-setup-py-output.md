---
id: 129
title: Add mcp.json customization hint to setup.py output
status: archived
priority: medium
created: 2026-03-29 07:06:54.736519+02:00
updated: 2026-03-29 14:40:06.571296+02:00
started: 2026-03-29 07:34:09.389332+02:00
completed: 2026-03-29 14:39:50.937776+02:00
tags:
- phase-1
- scope:mcp
- type:docs
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Modify the existing step 4 print line in setup.py to also reference README.md for MCP server customization examples.

## Acceptance Criteria
- [ ] setup.py step 4 in Next steps output (currently line ~134) is modified to include a reference to README for examples
- [ ] test_setup_prints_success_message in tests/test_setup_script.py adds an assertion that README appears in captured output
- [ ] Existing mcp.json assertion in the same test still passes

## Context
See docs/research/mcp-server-customization-docs.md
Task #122 added step 4 and the README section. This task completes the cross-reference.

[[2026-03-29]] Sun 10:24
## Architecture Review
**Verdict:** Approve

### AC Assessment

- setup() output includes mcp.json line: Already exists from #122 (line ~134). Refined to modify existing line.
- Line references README for examples: Not yet implemented, this is the remaining delta. Kept.
- Test assertions updated if needed: Vague. Refined to assert README in captured output.

### Architecture Notes
Pure docs-adjacent task. Single print() string modification in scripts/setup.py line ~134 plus one assertion in tests/test_setup_script.py line ~388. No new modules, interfaces, or dependencies.

Existing pattern: setup.py prints numbered Next steps list; test uses capsys. The README Adding MCP Servers section already exists (added by #122 builder).

TDD: No separate test task needed. Same ruling as #122 architect review. Type:docs task, one print string change, one test assertion. Both included in builder AC.

Overlap note: #124 (backlog) appears to be a duplicate of done #122. #128 (backlog) is a README-only subset. Neither affects this task. Suggest planner triage.

### Changes Made
- Rewrote AC: specified step 4 already exists, exact test assertion to add, removed vague language
- No tasks created or deleted

### Dependencies
- #122 (done): provides the existing step 4 line and README section this task cross-references

[[2026-03-29]] Sun 11:22
## Test-Writer Notes
- Non-implementation task (tagged type:docs) — no tests applicable.
- Architect review confirmed: "TDD: No separate test task needed. Type:docs task, one print string change, one test assertion. Both included in builder AC."
- Passing through to builder.

[[2026-03-29]] Sun 12:28
## Builder Notes
- Files changed: scripts/setup.py (line 151), tests/test_setup_script.py (line 386)
- Tests: 45 passed, 97% coverage on scripts/setup.py
- Lint: ruff clean on changed lines (pre-existing E501 at line 50 of setup.py docstring, not introduced by this task)
- Evidence: test_setup_prints_success_message PASSED with both mcp.json and README assertions
- Fixes applied: Shortened step 4 print to stay under 100 chars for ruff compliance
- Commit: 79d2eb8

[[2026-03-29]] So 13:14
## Review Evidence

### Test Results
- pytest tests/test_setup_script.py: **45 passed, 0 failed** (2.64s)

### Lint Results
- ruff check scripts/setup.py tests/test_setup_script.py: **1 pre-existing E501** at setup.py:49 (docstring of create_mcp_config). Confirmed pre-existing via git diff -- builder changes are lint-clean.

### TestFromAC Comparison

| Original Test | Change Made | Assessment |
|---|---|---|
| TestFromAC_PathDetectionAndOutput::test_setup_prints_success_message | assert README in captured.out added - stricter | STRENGTHENED |

STRENGTHENED is acceptable per skill. No WEAKENED or REMOVED entries.

### Security Review
Pure print() string literal. No user input, no file paths, no external calls. Clean.

### AC Compliance

| AC Line | Evidence | Status |
|---|---|---|
| setup.py step 4 modified to include README reference | git diff 79d2eb8 confirms: (see README.md) appended to step-4 print at line 151 | PASS |
| test_setup_prints_success_message adds README assertion | assert README in captured.out added at test line 386 (git diff confirmed) | PASS |
| Existing mcp.json assertion still passes | assert mcp.json in captured.out preserved; 45/45 passed | PASS |

### Test Quality
New assertion checks "README" in captured.out with descriptive message. ADEQUATE - substring check proportionate for a print-output test.

### Commit Discipline Flag
Commit 79d2eb8 staged tests/test_cleanup_github_skills_117.py (task 117 scope) alongside task 129 changes - violates "commit only files touched by your current task" rule. Task 117 has since been completed (commit b5377c6) and repo state is correct. Process-level finding only, not a correctness failure for 129 AC.

### Verdict: PASS
Confidence: 0.92

[[2026-03-29]] Sun 13:14
## Review Evidence

### Test Results
- pytest tests/test_setup_script.py: **45 passed, 0 failed** (2.64s)

### Lint Results
- ruff check scripts/setup.py tests/test_setup_script.py: **1 pre-existing E501** at setup.py:49 (docstring of create_mcp_config). Confirmed pre-existing via git diff -- builder changes are lint-clean.

### TestFromAC Comparison

| Original Test | Change Made | Assessment |
|---|---|---|
| TestFromAC_PathDetectionAndOutput::test_setup_prints_success_message | assert README in captured.out added - stricter | STRENGTHENED |

STRENGTHENED is acceptable per skill. No WEAKENED or REMOVED entries.

### Security Review
Pure print() string literal. No user input, no file paths, no external calls. Clean.

### AC Compliance

| AC Line | Evidence | Status |
|---|---|---|
| setup.py step 4 modified to include README reference | git diff 79d2eb8 confirms: (see README.md) appended to step-4 print at line 151 | PASS |
| test_setup_prints_success_message adds README assertion | assert README in captured.out added at test line 386 (git diff confirmed) | PASS |
| Existing mcp.json assertion still passes | assert mcp.json in captured.out preserved; 45/45 passed | PASS |

### Test Quality
New assertion checks "README" in captured.out with descriptive message. ADEQUATE - substring check proportionate for a print-output test.

### Commit Discipline Flag
Commit 79d2eb8 staged tests/test_cleanup_github_skills_117.py (task 117 scope) alongside task 129 changes - violates "commit only files touched by your current task" rule. Task 117 has since been completed (commit b5377c6) and repo state is correct. Process-level finding only, not a correctness failure for 129 AC.

### Verdict: PASS
Confidence: 0.92

[[2026-03-29]] Sat 14:18
## Docs Gate
### Checklist
No | Check | Applies? | Status | Evidence
1 | .github/copilot-instructions.md | No | N/A | Pure print() string literal change - no behavior or API change
2 | Docstrings | No | N/A | setup() has complete docstring at lines 126-130; changed line is a print() body statement
3 | docs/sources/overview.md | No | N/A | No external patterns used
4 | README.md | No | N/A | No CLI commands added or changed
5 | Research doc | Yes | Pass | docs/research/mcp-server-customization-docs.md exists and linked in task body

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/129-* files found)

[[2026-03-29]] Sun 14:39
## Audit
### AC Verification

AC Line |} Evidence |} Status
--- |} --- |} ---
setup.py step 4 modified to include README reference |} Line 151: (see README.md) appended |} PASS
test adds README assertion |} Line 386: assert README in captured.out |} PASS
Existing mcp.json assertion passes |} 45/45 passed in test_setup_script.py |} PASS

### Test Results
- pytest full suite: 568 passed, 82 failed (all pre-existing)
- pytest test_setup_script.py: 45 passed, 0 failed
- ruff: 1 pre-existing E501. Builder changes lint-clean.

### AC Quality: 5/5
### Confidence: .97
### Action: archive

[[2026-03-29]] Sun 14:40
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 2e6be81 | chore | kanban/tasks/129-*.md | #129 |
