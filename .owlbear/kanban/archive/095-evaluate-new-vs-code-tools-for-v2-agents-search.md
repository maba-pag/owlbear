---
id: 95
title: Evaluate new VS Code tools for v2 agents (search/usages, search/changes, 
  vscode/askQuestions)
status: archived
priority: medium
created: 2026-03-28 01:59:30.069530+01:00
updated: 2026-03-30 04:37:55.008020+02:00
started: 2026-03-30 04:37:50.343645+02:00
completed: 2026-03-30 04:37:50.343645+02:00
tags:
- phase-2
- scope:agents
- research
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria

- [x] Research doc exists at docs/research/vs-code-new-tools-evaluation.md with complete evaluation of search/usages, search/changes, and vscode/askQuestions
- [x] Research doc includes source analysis, tool-by-tool evaluation, summary matrix, and a final recommendation
- [x] Follow-up tasks created for each actionable recommendation: #101 (askQuestions revert), #102 (search/changes skills), #103 (search/usages skills)
- [x] Duplicate task #105 identified and archived
- [x] All follow-up tasks have completed the full pipeline (archived)

Non-implementation research task. No builder, test-writer, or reviewer work needed â€” deliverables are the research doc and follow-up task creation.

[[2026-03-29]] Sun 19:06
## Test-Writer Notes
- Non-implementation task (tagged research) — no tests applicable.
- Passing through to builder.

[[2026-03-30]] Mon 04:37
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Research doc exists with complete evaluation | docs/research/vs-code-new-tools-evaluation.md: 113 lines, sections 1-5 | PASS |
| Doc includes source analysis, tool-by-tool eval, summary matrix, recommendation | Sections 2 (Sources), 3.3 (Tool-by-Tool), 3.4 (Summary Matrix), 4 (Recommendation) | PASS |
| Follow-up tasks #101, #102, #103 created | All three exist, all archived | PASS |
| Duplicate #105 identified and archived | #105 archived with duplicate explanation | PASS |
| All follow-up tasks completed full pipeline | #101 archived, #102 archived, #103 archived | PASS |

### Test Results
- pytest: 1109 passed, 139 failed, 6 errors (all pre-existing, none related to #95)
- ruff: 2 violations in unrelated test_necessity_check_196.py

### Research Task Verification
- Research doc exists: YES
- Follow-up tasks created at ideation: YES (all now archived)
- Follow-up tasks reference research doc: YES (all bodies link to docs/research/vs-code-new-tools-evaluation.md)

### Architect Quality
- AC specificity: 5/5 -- all 5 lines are concrete, verifiable conditions
- Edge case coverage: adequate for research task
- AC quality score: 4 (AC5 is status-tracking rather than content criterion; minor)

### Quality Gap
- Research doc was never committed by upstream agents. Committed by auditor: f23a396

### Deduction breakdown: no deductions (all AC verified with evidence, no task-scope failures)
### Confidence: .98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| f23a396 | docs | docs/research/vs-code-new-tools-evaluation.md | #95 |
