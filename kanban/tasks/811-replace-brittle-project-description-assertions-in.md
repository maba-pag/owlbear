---
id: 811
title: Replace brittle project-description assertions in test_source_evaluator.py
status: archived
priority: nice-to-have
created: 2026-03-14T21:06:01.5886696+01:00
updated: 2026-03-15T07:19:31.0701963+01:00
started: 2026-03-15T07:18:55.3323726+01:00
completed: 2026-03-15T07:18:55.3323726+01:00
tags:
    - audit
    - test
    - scope:core
claimed_by: auditor
claimed_at: 2026-03-15T07:19:31.0701963+01:00
class: standard
---

Replace 2 exact project-description assertions in test_source_evaluator.py with checks against SAMPLE_PROJECT_CONTEXT fields per docs/research/brittle-prompt-assertions.md section 5.

## AC
- Replace `'always-on AI development system' in prompt_text` with `SAMPLE_PROJECT_CONTEXT['description'] in prompt_text` in `test_prompt_includes_project_description`  
- Replace `'Autonomous coding' in prompt_text` with `SAMPLE_PROJECT_CONTEXT['goals'][0] in prompt_text` in `test_prompt_includes_project_goals`  
- Keep `'OwlBear' in prompt_text` unchanged (project name is a stable constant)
- All tests in `TestEvaluateWithProjectContext` pass after changes
- SAMPLE_PROJECT_CONTEXT is a dict (use bracket access, not dot notation)

Note: This is a test-refactoring task -- no separate TDD RED phase needed. Builder modifies test file directly.

[[2026-03-15]] Sun 04:09
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Replace description assertion | Clear, verifiable  maps directly to `SAMPLE_PROJECT_CONTEXT['description']` | OK |
| Replace goals assertion | Clear, verifiable  maps to `SAMPLE_PROJECT_CONTEXT['goals'][0]` | OK |
| Keep OwlBear unchanged | Correct  project name is a stable constant | OK |
| All tests in TestEvaluateWithProjectContext pass | Fixed class name from `TestEvaluatePromptConstruction` (non-existent) | Refined |
| Bracket access for dict | Correct  SAMPLE_PROJECT_CONTEXT is a dict, not a model | OK |

### Architecture Notes
- Pure test refactoring: only `tests/test_source_evaluator.py` is touched, no production code changes
- `SAMPLE_PROJECT_CONTEXT` dict defined at line ~50 of the test file; both replaced assertions reference fields present in the dict
- `_build_prompt()` in `src/owlbear/memory/knowledge/evaluator.py` interpolates `project_context.get('description')` and `project_context.get('goals')` directly, so the dict values will appear verbatim in the prompt
- TDD waiver correct: test refactoring doesn't need a separate RED phase
- No security surface, no new dependencies, no failure modes

### Changes Made
- Fixed AC class name: `TestEvaluatePromptConstruction` -> `TestEvaluateWithProjectContext`
- Added test method names to AC lines for precision

[[2026-03-15]] Sun 04:26
## Test-Writer Notes
- Non-implementation task (test-refactoring, TDD waiver in AC)  no separate RED phase tests needed.
- Builder modifies test file directly per AC.
- Passing through to builder.

[[2026-03-15]] Sun 06:15
## Builder Notes
- Files changed: tests/test_source_evaluator.py (2 assertion lines)
- Tests: 29 passed (full file), 8 in TestEvaluateWithProjectContext
- Lint: ruff clean, format clean
- Diff: 2 insertions, 2 deletions
- Commit: 425d802

[[2026-03-15]] Sun 06:38
## Review Evidence
### Test Results
- pytest: 29 passed, 0 failed (tests/test_source_evaluator.py)
- All 8 TestEvaluateWithProjectContext tests pass

### Lint Results
- ruff: All checks passed!

### Coverage
- N/A (test-only refactoring, no production code changed)

### Pass 1 -- CRITICAL
#### Security Review
- No security issues found (test-only change, no production code touched)

#### Test Integrity
- Skipped: No TestFromAC_* classes (TDD waiver for test refactoring)

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Both new assertions reference SAMPLE_PROJECT_CONTEXT fields directly |
| Negative/error paths | ADEQUATE | Not applicable to this 2-line refactor |
| Mutation reasoning | STRONG | If description/goals changed in fixture, tests auto-adapt |
| Test independence | STRONG | Each test creates its own evaluator and mock |
| Descriptive names | STRONG | test_prompt_includes_project_description, test_prompt_includes_project_goals |

#### Data Safety
- No data safety issues (test-only change)

### Pass 2 -- INFORMATIONAL
- No informational findings

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| Replace description assertion | L194: SAMPLE_PROJECT_CONTEXT['description'] in prompt_text | PASS |
| Replace goals assertion | L206: SAMPLE_PROJECT_CONTEXT['goals'][0] in prompt_text | PASS |
| Keep OwlBear unchanged | L182: assert 'OwlBear' in prompt_text (unchanged) | PASS |
| All tests pass | 29 passed, 0 failed | PASS |
| Bracket access | Both use dict bracket access, not dot notation | PASS |

### Verdict: PASS
### Confidence: .95
### Action: kanban edit 811 --status docs --release

[[2026-03-15]] Sun 06:52
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Test-only refactoring (2 assertion lines), no behavior/API change |
| 2 | Docstrings complete | No | N/A | Only tests/test_source_evaluator.py changed (test file, no public API) |
| 3 | sources/overview.md | No | N/A | No external patterns adopted |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/brittle-prompt-assertions.md exists, referenced in task body |
| 6 | No impact | -- | -- | Items 1-4 N/A, item 5 pass |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/811-* files found)

[[2026-03-15]] Sun 07:19
## Audit (2026-03-15)
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Replace description assertion | L194: SAMPLE_PROJECT_CONTEXT[description] in prompt_text | PASS |
| Replace goals assertion | L206: SAMPLE_PROJECT_CONTEXT[goals][0] in prompt_text | PASS |
| Keep OwlBear unchanged | L182: assert OwlBear in prompt_text (unchanged) | PASS |
| All TestEvaluateWithProjectContext pass | 29 passed, 0 failed (8 in class) | PASS |
| Bracket access, not dot notation | Both use dict[key] syntax | PASS |

### Test Results
- pytest: 29 passed, 0 failed
- ruff: All checks passed

### Commit: 425d802 (1 file, +2/-2)
### Confidence: .97
### Action: archive

[[2026-03-15]] Sun 07:19
## Audit
AC: 5/5 PASS. pytest 29/29. ruff clean. Commit 425d802 (+2/-2). Confidence .97. Archived.
