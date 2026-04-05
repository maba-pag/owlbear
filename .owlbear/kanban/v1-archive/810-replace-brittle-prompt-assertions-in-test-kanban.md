---
id: 810
title: Replace brittle prompt assertions in test_kanban_pipeline.py
status: archived
priority: nice-to-have
created: 2026-03-14T21:05:54.3854281+01:00
updated: 2026-03-15T06:29:34.1854637+01:00
started: 2026-03-15T06:29:29.7723598+01:00
completed: 2026-03-15T06:29:29.7723598+01:00
tags:
    - audit
    - test
    - scope:core
class: standard
---

Replace 10 exact-substring assertions in TestOrchestratorKanbanPrompt with defn.tools metadata checks and regex patterns per docs/research/brittle-prompt-assertions.md section 5.

## AC
- Replace substring assertions with defn.tools membership checks where testing capability presence (e.g. 'kanban_pick in defn.system_prompt' becomes 'kanban in defn.tools')
- Replace section-heading substring checks with case-insensitive regex (e.g. re.search(r'(?i)##.*kanban', defn.system_prompt))
- Replace status-lifecycle substring checks with regex (e.g. re.search(r'(?i)todo.*in-progress', prompt))
- All 6 existing tests in TestOrchestratorKanbanPrompt pass after changes
- No test removed  only assertion strategies changed
- Import re at top of file

Note: This is a test-refactoring task  no separate TDD RED phase needed. Builder modifies test file directly.

[[2026-03-15]] Sun 04:09
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| defn.tools membership checks for capability presence | Correct -- defn.tools is list[str], orchestrator declares 'kanban'. Exact list membership is resilient. | Keep |
| Section-heading checks with case-insensitive regex | Sound -- re.search(r'(?i)##.*kanban', ...) tolerates rewording while verifying structural presence. | Keep |
| Status-lifecycle substring checks with regex | Sound -- status names (todo, in-progress) are domain constants, regex appropriate. | Keep |
| All 6 existing tests pass after changes | Verifiable -- counted 6 methods, 10 assertion lines. Count matches. | Keep |
| No test removed, only assertion strategies changed | Verifiable mechanically via git diff. | Keep |
| Import re at top of file | Trivial, clear. | Keep |
| TDD RED exemption for test-refactoring | Appropriate -- no new behavior, only assertion strategy changes. | Keep |

### Architecture Notes
- Single domain: test refactoring only, no source changes.
- Pattern follows test_agent_definitions.py (tools list checks, structural assertions) -- already proven in codebase.
- Research doc (docs/research/brittle-prompt-assertions.md section 5) provides complete mapping table for every replacement.
- defn.tools parsed from YAML frontmatter in parse_agent_definition() (src/owlbear/core/agent_def.py). Orchestrator tools list: [delegation, filesystem, ask_user, kanban, terminal].
- Several tool-name assertions collapse to the same 'kanban' in defn.tools check. This is intentional (10 assertions -> 7 checks per research doc).

### Changes Made
- Approved as-is -- AC is precise and verifiable.

### Dependencies
- None required.

[[2026-03-15]] Sun 04:26
## Test-Writer Notes
- Non-implementation task (test-refactoring with TDD RED exemption) -- no separate tests applicable.
- Passing through to builder.

[[2026-03-15]] Sun 05:07
## Builder Notes
- Files changed: tests/test_kanban_pipeline.py
- Tests: 14 passed (6 in TestOrchestratorKanbanPrompt), ruff clean
- Changes: added import re; replaced 10 substring assertions with 4 defn.tools membership checks + 4 regex patterns
- No tests removed, all 6 methods preserved
- Commit: d18f5f4

[[2026-03-15]] Sun 05:21
## Review Evidence

### Test Results
- pytest: 14 passed, 0 failed (all 6 TestOrchestratorKanbanPrompt + 8 others)
- No warnings or errors

### Lint Results
- ruff: All checks passed!

### Coverage
- N/A: test-only refactoring, no source modules changed

### Pass 1 -- CRITICAL
#### Security Review
- No security issues. Test-only change, no source code, no user input handling.

#### Test Integrity
- No TestFromAC_* classes (TDD RED exemption for test-refactoring). Skipped.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Structural checks (defn.tools membership, regex). 3 tests share identical assertion but intentional per research doc. |
| Negative/error paths | ADEQUATE | N/A for prompt-content tests. No error paths to cover. |
| Mutation reasoning | ADEQUATE | Removing 'kanban' from tools catches 4 tests. Removing section headings catches 1. Each domain guarded. |
| Test independence | STRONG | Each test parses orchestrator.md independently. No shared state. |
| Descriptive names | ADEQUATE | Names describe the concern, some method names slightly misaligned with new assertion strategy. |

#### Data Safety
- No data safety issues. Test-only changes.

### Pass 2 -- INFORMATIONAL
- 3 tests (kanban_pick, dependency_awareness, delegation_pattern) now have identical assertion bodies. Documented as intentional in research doc section 5. Could consolidate in future.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Replace substring with defn.tools membership | Lines 238, 254, 261, 270: 'kanban' in defn.tools | test_prompt_mentions_kanban_pick, dependency_awareness, failure_handling, delegation_pattern | PASS |
| Section-heading checks with case-insensitive regex | Line 232: re.search(r'(?i)##.*kanban', defn.system_prompt) | test_prompt_contains_kanban_pipeline_section | PASS |
| Status-lifecycle checks with regex | Lines 247-248: re.search(r'(?i)todo.*in-progress') + re.search(r'(?i)review') | test_prompt_mentions_status_lifecycle | PASS |
| All 6 existing tests pass | pytest: 14 passed, all 6 TestOrchestratorKanbanPrompt pass | All 6 methods | PASS |
| No test removed | git diff: 6 methods before and after, no deletions | N/A | PASS |
| Import re at top | Line 10: import re | N/A | PASS |

### Verdict: PASS
Confidence: .95

### Action Taken
kanban edit 810 --status docs --release

[[2026-03-15]] Sun 05:59
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Test-only refactoring, no behavior/API change |
| 2 | Docstrings complete | No | N/A | Only tests/test_kanban_pipeline.py changed (test file) |
| 3 | sources/overview.md | No | N/A | No external patterns adopted |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/brittle-prompt-assertions.md exists, referenced in task body |
| 6 | No impact | -- | -- | Items 1-4 N/A, item 5 pass |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/810-* files found)

[[2026-03-15]] Sun 06:29
## Audit (2026-03-15)
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| defn.tools membership checks | L238,254,261,270: 'kanban' in defn.tools (4 checks) | PASS |
| Section-heading regex | L232: re.search(r'(?i)##.*kanban', defn.system_prompt) | PASS |
| Status-lifecycle regex | L247-248: re.search(r'(?i)todo.*in-progress') + re.search(r'(?i)review') | PASS |
| All 6 tests pass | pytest: 14 passed (6 in TestOrchestratorKanbanPrompt), 0 failed | PASS |
| No test removed | git diff d18f5f4: 6 methods before/after, 10ins 12del | PASS |
| import re at top | Line 10: import re | PASS |

### Test Results
- Task-scoped: 14 passed, 0 failed
- Full suite: 3378 passed, 70 failed (all pre-existing), 2 skipped
- Ruff: All checks passed

### Confidence: .97
### Action: archive
