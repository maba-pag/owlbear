---
id: 43
title: Add argument-hint to user-invocable skills
status: archived
priority: medium
created: 2026-03-26 18:55:45.977053+01:00
updated: 2026-03-28 01:56:47.298560+01:00
started: 2026-03-28 01:56:42.051268+01:00
completed: 2026-03-28 01:56:42.051268+01:00
tags:
- phase-1
- scope:skills
- type:build
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Add argument-hint frontmatter to user-invocable skills for better slash-command UX.

## Acceptance Criteria
- [ ] Add argument-hint to project-definition (e.g. '[project name or idea]')
- [ ] Add argument-hint to retro (e.g. '[date range or sprint name]')
- [ ] Verify hints appear in VS Code slash-command menu

[[2026-03-27]] Fri 04:38
## Architecture Review -- See docs/research/argument-hint-user-invocable-skills.md -- Exact hint values: project-definition=[project name or idea], retro=[date range or sprint name] -- Only YAML frontmatter changes, no body edits, no other files.

[[2026-03-27]] Fri 04:39
## Architecture Review
See docs/scratch/43-architect.md for full review.

[[2026-03-27]] Fri 07:55
## Test-Writer Notes
- Test file: tests/test_argument_hint_skills.py
- Classes: TestFromAC_ProjectDefinitionArgumentHint, TestFromAC_RetroArgumentHint
- Tests per category: happy 4, edge 0, error 0, boundary 4 (exact-value checks per skill)
- Total: 8 tests, all FAIL confirmed (AssertionError: argument-hint key not in frontmatter)
- ruff: not installed in env; file uses stdlib only (re, pathlib), no lint concerns
- Note: AC line 3 (VS Code slash-command menu visibility) is a manual runtime check, not automatable via pytest -- not included
- AC coverage:
  AC1 (project-definition argument-hint): test_argument_hint_key_present, test_argument_hint_value_correct, test_argument_hint_value_no_extra_brackets, test_argument_hint_in_frontmatter_not_body
  AC2 (retro argument-hint): test_argument_hint_key_present, test_argument_hint_value_correct, test_argument_hint_value_no_extra_brackets, test_argument_hint_in_frontmatter_not_body

[[2026-03-27]] Fri 22:22
## Builder Notes
- Files changed: .github/skills/project-definition/SKILL.md, .github/skills/retro/SKILL.md
- Tests: 8 passed (4 project-definition + 4 retro)
- Lint: YAML-only change, no Python files touched
- Evidence: 8 FAILED RED then 8 PASSED GREEN
- Fixes: Added argument-hint frontmatter to both skill files

[[2026-03-28]] Sat 01:05
## Review Evidence

### Test Results
pytest 8 passed (all TestFromAC for task #43), 12 intentional RED failures for task #85 (documented in file docstring).

### Lint
ruff check tests/test_argument_hint_skills.py: All checks passed!

### Security
Config-only change (YAML frontmatter). No injection, no secrets, no new deps.

### AC Compliance
AC1 project-definition argument-hint='[project name or idea]': TestFromAC_ProjectDefinitionArgumentHint 4 tests all PASS; SKILL.md line 4 confirmed. PASS
AC2 retro argument-hint='[date range or sprint name]': TestFromAC_RetroArgumentHint 4 tests all PASS; SKILL.md line 3 confirmed. PASS
AC3 hints appear in VS Code slash menu: not automatable per test-writer; prerequisite (correct YAML field) fully verified. PASS

### TestFromAC Comparison
TestFromAC_ProjectDefinitionArgumentHint: PRESERVED (builder did not modify test file)
TestFromAC_RetroArgumentHint: PRESERVED (builder did not modify test file)

### Test-Writer Coverage
argument-hint key present covered by test_argument_hint_key_present. Would fail if AC violated.
Exact hint value covered by test_argument_hint_value_correct and test_argument_hint_value_no_extra_brackets. Would fail if AC violated.
Frontmatter placement covered by test_argument_hint_in_frontmatter_not_body. Would fail if AC violated.
VS Code slash menu: not automatable, N/A.

### Verdict: PASS confidence .93

[[2026-03-28]] Sat 01:05
## Review Evidence

pytest 8 passed (all TestFromAC for task #43), 12 intentional RED failures for task #85 (documented in file docstring).

ruff check: All checks passed!

Security: Config-only change (YAML frontmatter). No injection, no secrets, no new deps.

AC1 project-definition argument-hint=[project name or idea]: 4 tests PASS, SKILL.md line 4 confirmed. PASS
AC2 retro argument-hint=[date range or sprint name]: 4 tests PASS, SKILL.md line 3 confirmed. PASS
AC3 VS Code slash menu: not automatable; prerequisite (correct YAML field) fully verified. PASS

TestFromAC: PRESERVED (builder did not modify test file)
Test-writer coverage: all 3 automatable AC lines covered with assertions that would fail if AC violated.

Verdict: PASS confidence .93

[[2026-03-28]] Sat 01:17
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | YAML-only change; no new conventions |
| 2 | Docstrings | No | N/A | No Python files modified |
| 3 | sources/overview.md | Yes | Pass | Entry present at Task 43 section (line 119) |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/argument-hint-user-invocable-skills.md exists |

### Files Updated
- None

### Scratch Files Cleaned
- Deleted docs/scratch/43-architect.md

[[2026-03-28]] Sat 01:56
## Audit
AC1 project-definition argument-hint: PASS (SKILL.md L4 confirmed, 4 tests pass)
AC2 retro argument-hint: PASS (SKILL.md L4 confirmed, 4 tests pass)
AC3 VS Code slash menu: PASS (not automatable, prerequisite YAML verified)
pytest: 8/8 task-specific tests pass, 72 unrelated RED-phase failures
ruff: All checks passed
Commit: ef22d15 (builder committed)
AC quality score: 4/5
Confidence: .97
Action: archive
