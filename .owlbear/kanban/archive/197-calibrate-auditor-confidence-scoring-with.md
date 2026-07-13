---
id: 197
title: Calibrate auditor confidence scoring with deduction rubric
status: archived
priority: medium
created: 2026-03-29 23:08:40.671442+02:00
updated: 2026-03-30 05:21:03.365295+02:00
started: 2026-03-30 05:20:28.073927+02:00
completed: 2026-03-30 05:20:28.073927+02:00
tags:
- agent
- quality
- scope:agents
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Replace the auditor's freeform confidence scoring with a structured deduction rubric in the task-verification skill. Current scoring is meaningless: 59%% of scores are .97.

## Acceptance Criteria
- [ ] task-verification skill (skills/task-verification/SKILL.md) Step 3 updated with deduction rubric: start at 1.0, deduct per criterion
- [ ] Deduction criteria: -.02 per AC line with no specific evidence, -.05 for lint issues, -.03 for AC quality score at 3 or below, -.02 for missing reviewer evidence section, -.05 for full-suite test failures in task scope
- [ ] Auditor agent red-flags list updated: 'Your confidence score is between .95 and .97 without explicit deduction calculation'
- [ ] Score must be accompanied by deduction breakdown (not just a number)

## Context
See docs/research/pipeline-quality-audit.md recommendation R4. Evidence: 34/58 archived tasks scored .97, 12 scored .95. 80%% cluster in .95-.97 range.

[[2026-03-30]] Mon 02:48
## Architecture Review
**Verdict:** APPROVE

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| task-verification SKILL.md Step 3 updated with deduction rubric | Clear: exact file, exact section, exact mechanic (start 1.0, deduct) | Keep |
| Deduction criteria with specific values | Clear: 5 explicit deduction criteria with numeric values, each independently verifiable | Keep |
| Auditor agent red-flags list updated with specific text | Clear: target is agents/auditor.agent.md boundaries red-flags bullet list (L131). Exact text provided. | Keep |
| Score must be accompanied by deduction breakdown | Clear: auditor output format template (Channel B) must include breakdown, not just a number | Keep |

### Architecture Notes
- **No code changes.** Both targets are markdown files (skills/task-verification/SKILL.md, agents/auditor.agent.md). TDD does not apply to instruction file edits.
- **Step 3 integration:** Current Step 3 has a threshold table and action mapping. The rubric slots in before the table as the scoring mechanism. The threshold table stays as-is (it defines what to DO with the score).
- **Channel B template update:** AC4 implies the auditor Channel B output format (auditor.agent.md output_format section) should include a deduction breakdown line alongside the existing Confidence line.
- **Red-flags location:** agents/auditor.agent.md L131 has a red-flags bullet list. New entry goes there.
- **Research grounding:** Deduction values come directly from R4 in docs/research/pipeline-quality-audit.md. Evidence: 34/58 archived tasks scored .97, 80% cluster in .95-.97 range.

### Changes Made
- Reviewed AC, no refinement needed
- Approved to todo

### Dependencies
- #192 (research: pipeline quality audit): complete, doc exists at docs/research/pipeline-quality-audit.md

[[2026-03-30]] Mon 03:38
## Test-Writer Notes
- Test file: tests/test_auditor_deduction_rubric_197.py
- Classes: TestFromAC_DeductionRubricPresent, TestFromAC_DeductionCriteriaValues, TestFromAC_AuditorRedFlagEntry, TestFromAC_DeductionBreakdownInOutput
- Total: 15 tests, all FAIL
- ruff: clean
- Note: targets are markdown; tests verify file content contracts.

[[2026-03-30]] Mon 04:22
## Builder Notes
- Files changed: skills/task-verification/SKILL.md, agents/auditor.agent.md
- Tests: 15 passed (test_auditor_deduction_rubric_197.py)
- Coverage: N/A (content tests on markdown files, no Python source changed)
- Lint: ruff clean
- Evidence: All 15 TestFromAC_ tests green; test_agent_port_v2.py pre-existing failures unaffected
- Fixes applied: None

[[2026-03-30]] Mon 04:59
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Thresholds unchanged; deduction mechanism is skill-internal, not a top-level convention |
| 2 | Docstrings | No | N/A | No Python files modified; both targets are markdown files |
| 3 | docs/sources/overview.md | No | N/A | Deduction values from internal research doc (pipeline-quality-audit.md R4), not external sources |
| 4 | README.md | No | N/A | No CLI commands added or changed |
| 5 | Research doc linked | Yes | Pass | docs/research/pipeline-quality-audit.md exists; referenced in task body and AC context |
| 6 | Scratch files | N/A | Pass | No docs/scratch/197-* files found |

### Deliverable Verification
- skills/task-verification/SKILL.md Step 3: deduction rubric present with all 5 AC criteria (-.02/AC-line, -.05/lint, -.03/AC-quality<=3, -.02/missing-reviewer, -.05/test-failures)
- agents/auditor.agent.md: deduction breakdown in Channel B output template; red-flag 'confidence between .95 and .97 without explicit deduction calculation' present

### Files Updated
- None

### Scratch Files Cleaned
- None

[[2026-03-30]] Mon 05:20
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: SKILL.md Step 3 deduction rubric | Read SKILL.md L92: 'Start at 1.0, deduct per criterion' with table | PASS |
| AC2: 5 deduction criteria values | Table at SKILL.md L94-L100 has all 5 correct values | PASS |
| AC3: Auditor red-flags updated | Text '.95 and .97 without explicit deduction calculation' in auditor.agent.md boundaries | PASS |
| AC4: Deduction breakdown in output | Channel B template includes 'Deduction breakdown' field at auditor.agent.md L72 | PASS |

### Test Results
- pytest (task-specific): 15 passed, 0 failed
- pytest (full suite): 1109 passed, 139 failed (all pre-existing, 0 in-scope)
- ruff: clean

### AC Quality: 5/5
AC lines were specific, measurable, and led to clean implementation.

### Deduction breakdown: none (all AC verified, lint clean, no in-scope failures, reviewer/writer evidence present, AC quality 5)
### Confidence: 1.0
### Action: archive

[[2026-03-30]] Mon 05:21
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 39da7ea | chore | kanban/tasks/197-*, kanban/activity.jsonl | #197 |
