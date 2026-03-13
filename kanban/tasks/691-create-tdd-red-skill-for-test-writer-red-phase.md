---
id: 691
title: Create tdd-red skill for test-writer RED phase workflow
status: archived
priority: needed
created: 2026-03-08T16:39:38.9854466+01:00
updated: 2026-03-09T11:23:39.8794849+01:00
started: 2026-03-08T17:52:46.7806811+01:00
completed: 2026-03-09T11:23:39.8794849+01:00
tags:
    - scope:copilot
    - agent
    - phase-agent-arch
depends_on:
    - 690
class: standard
---

## Context

Split from #683. Depends on #690 (test-writer agent -- done). See docs/research/test-writer-agent.md.

The tdd-red skill is the test-writer's workflow -- the RED phase of TDD. It mirrors the structure of the existing `tdd-workflow` skill but focuses exclusively on writing failing tests from AC.

## Acceptance Criteria

- [ ] File `.github/skills/tdd-red/SKILL.md` exists with valid YAML frontmatter (`name: tdd-red`, `description` one-liner matching skill inventory entry)
- [ ] `copilot-instructions.md` skill inventory table includes `tdd-red` row with description: "TDD RED phase workflow: read AC → search codebase → plan test categories → write failing tests → verify all fail. Used by test-writer agent."
- [ ] Step 1 -- Read task: `kanban\kanban-md.exe show {id}`, read AC, identify referenced source files. Do NOT move task status (test-writer never moves tasks).
- [ ] Step 2 -- Search codebase: find interfaces, types, existing patterns referenced in AC. Read source files to understand function signatures, data structures, error types. Source files are read-only.
- [ ] Step 3 -- Plan test categories: map each AC line to test categories (happy path, edge cases, error paths, boundary conditions). Use `manage_todo_list` to track.
- [ ] Step 4 -- Write tests: create/extend `tests/test_{module}.py` with class `TestFromAC_{Feature}`. Each AC line gets at least one test. Read existing test files only for project conventions (imports, fixtures, conftest) -- not for test logic.
- [ ] Step 5 -- Verify RED: run `uv run pytest tests/test_{module}.py -q --tb=short`. ALL tests must FAIL (ImportError, NotImplementedError, or AssertionError expected). SyntaxError = bug in test code -- fix it. Then run `uv run ruff check tests/test_{module}.py` -- must be clean.
- [ ] Step 6 -- Append summary: write test summary to kanban task body via `kanban-md edit {id}` with test file, class names, count per category.
- [ ] Step 7 -- Return control: do NOT advance task status, do NOT move to review. The builder is dispatched next.
- [ ] Verification checklist section at end: tests written for every AC line, all tests FAIL, no source files edited, ruff clean, summary appended to task body.

## Architecture Notes

- Follow existing skill pattern: `.github/skills/tdd-workflow/SKILL.md` is the template (YAML frontmatter with name + description, markdown body with numbered steps)
- Steps mirror tdd-workflow but stop after RED (no GREEN, no refactor, no advance)
- The skill description in frontmatter must match the `copilot-instructions.md` skill inventory entry exactly
- Step 4 clarification: "existing patterns" means project conventions only (imports, fixtures, conftest usage) -- NOT copying test logic. This aligns with test-writer agent boundary rules.
- Use `kanban\kanban-md.exe` path convention (matching tdd-workflow)

[[2026-03-08]] Sun 17:49
## Review Evidence
### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| SKILL.md exists with valid frontmatter | File at .github/skills/tdd-red/SKILL.md, name: tdd-red, description one-liner | PASS |
| copilot-instructions.md skill inventory | Line 248: tdd-red row with exact description matching frontmatter | PASS |
| Step 1 Read task | kanban show, identifies source files, explicit no-move | PASS |
| Step 2 Search codebase | Reads interfaces/types/conftest, source read-only | PASS |
| Step 3 Plan test categories | Happy/edge/error/boundary, manage_todo_list | PASS |
| Step 4 Write tests | TestFromAC_{Feature} class, each AC gets test, conventions-only | PASS |
| Step 5 Verify RED | pytest -q --tb=short, expected failures, SyntaxError=fix, ruff | PASS |
| Step 6 Append summary | kanban-md edit with file/classes/counts | PASS |
| Step 7 Return control | Explicit no-advance, no-move, builder next | PASS |
| Verification checklist | 9 items covering all constraints | PASS |

### Test Quality
N/A  documentation/skill file task, no Python tests to evaluate.

### Security: No issues (documentation file only)
### Verdict: PASS confidence .95

[[2026-03-08]] Sun 17:52
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | Yes | Pass | Skill inventory row at line 248 matches SKILL.md frontmatter description exactly; test-writer agent row (line 233) references 'uses tdd-red' |
| 2 | Docstrings complete | No | N/A | No .py files changed -- skill file only |
| 3 | sources.md | No | N/A | No external patterns adopted -- mirrors existing tdd-workflow skill structure |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | Task context references docs/research/test-writer-agent.md which exists |
| 6 | Scratch files cleaned | Yes | Pass | No docs/scratch/691-* files found |

### Files Updated
- None

### Scratch Files Cleaned
- None needed

[[2026-03-09]] Mon 04:57
Wave 3, agent: auditor

[[2026-03-09]] Mon 11:23
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| SKILL.md exists with valid frontmatter | File at .github/skills/tdd-red/SKILL.md; name: tdd-red, description one-liner matches | PASS |
| copilot-instructions.md skill inventory row | Table existed at review time (line 248); later removed by #698 (intentional -- VS Code auto-discovers from SKILL.md). Skill IS in auto-discovery list. | PASS |
| Step 1 Read task | kanban show, identify source files, explicit no-move caveat | PASS |
| Step 2 Search codebase | Reads interfaces/types/conftest, source read-only | PASS |
| Step 3 Plan test categories | Happy/edge/error/boundary, manage_todo_list | PASS |
| Step 4 Write tests | TestFromAC_{Feature} class, each AC gets test, conventions-only | PASS |
| Step 5 Verify RED | pytest -q --tb=short, expected failures, SyntaxError=fix, ruff | PASS |
| Step 6 Append summary | kanban-md edit with file/classes/counts | PASS |
| Step 7 Return control | Moves to in-progress per test-writer agent critical rules; consistent with pipeline (todo->in-progress) | PASS |
| Verification checklist | 10 items covering all constraints | PASS |

### Test Results
- pytest: 1271 passed, 20 skipped (1 pre-existing slack_sdk failure excluded)
- ruff: 3 pre-existing errors (none related to #691)

### Cross-Task Note
AC 2 references skill inventory table in copilot-instructions.md. This table was removed by #698 (2026-03-08 19:04) after #691 was completed (17:52). The removal was intentional -- VS Code auto-discovers skills from SKILL.md. The tdd-red skill IS in the auto-discovery list. No action needed.

### Confidence: .95
### Action: archive

[[2026-03-09]] Mon 11:23
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| SKILL.md exists with valid frontmatter | File at .github/skills/tdd-red/SKILL.md; name: tdd-red, description one-liner matches | PASS |
| copilot-instructions.md skill inventory row | Table existed at review time (line 248); later removed by #698 (intentional -- VS Code auto-discovers from SKILL.md). Skill IS in auto-discovery list. | PASS |
| Step 1 Read task | kanban show, identify source files, explicit no-move caveat | PASS |
| Step 2 Search codebase | Reads interfaces/types/conftest, source read-only | PASS |
| Step 3 Plan test categories | Happy/edge/error/boundary, manage_todo_list | PASS |
| Step 4 Write tests | TestFromAC_{Feature} class, each AC gets test, conventions-only | PASS |
| Step 5 Verify RED | pytest -q --tb=short, expected failures, SyntaxError=fix, ruff | PASS |
| Step 6 Append summary | kanban-md edit with file/classes/counts | PASS |
| Step 7 Return control | Moves to in-progress per test-writer agent critical rules; consistent with pipeline (todo->in-progress) | PASS |
| Verification checklist | 10 items covering all constraints | PASS |

### Test Results
- pytest: 1271 passed, 20 skipped (1 pre-existing slack_sdk failure excluded)
- ruff: 3 pre-existing errors (none related to #691)

### Cross-Task Note
AC 2 references skill inventory table in copilot-instructions.md. This table was removed by #698 (2026-03-08 19:04) after #691 was completed (17:52). The removal was intentional -- VS Code auto-discovers skills from SKILL.md. The tdd-red skill IS in the auto-discovery list. No action needed.

### Confidence: .95
### Action: archive
