---
id: 1105
title: Write append-failure injection tests for 6 engine mutators
status: archived
priority: medium
created: 2026-04-22T21:08:24.061291+00:00
updated: 2026-04-22T22:48:03.078113+00:00
tags: []
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
Split from #1104. Write failure-injection tests for all 6 engine mutators.
[[2026-04-22]]
## Research

**SUPERSEDED by #1104.** The #1104 architecture review (cycle 4) merged the scope of this task and #1106 back into #1104 as a standard TDD unit. The architect's refined AC on #1104 fully covers all 6 mutator failure-injection tests originally scoped here.

- No independent research findings — scope is identical to #1104 Tests (RED phase)
- No follow-up tasks needed — #1104 is the follow-up
- No research doc created — supersession, not analysis
- Tier: N/A — no finding to classify
- Decision requests: none

Recommend #1106 also be closed as superseded for the same reason.
[[2026-04-22]]
## Audit

### Supersession Verification
Task #1105 was superseded by #1104 during #1104's architecture review (cycle 4). The architect expanded #1104 to cover both RED tests and GREEN implementation as a standard TDD unit, absorbing #1105 (tests) and #1106 (implementation).

**Verified:**
- #1104 refined AC explicitly covers all 6 mutators (edit_task, move_task, claim_task, end_work, release_task, sweep) with failure injection on append_activity_event — matches #1105's original scope exactly
- #1104 status: `todo` (active in pipeline, awaiting test-writer)
- #1105 produced zero code deliverables — no files, no tests, no research doc
- Supersession documented clearly in Research section

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| (implicit) Document supersession | Research section: "SUPERSEDED by #1104" with rationale | PASS |
| (implicit) No orphaned deliverables | No files created; #1104 refined AC covers full scope | PASS |

### Test Results
- pytest: 1253 passed, 106 failed, 4 skipped (exit 1)
- ruff: 5 violations (all W292 in unrelated test files)
- All failures are pre-existing background debt; zero relate to #1105 (no code deliverables)

### Architect Quality: N/A
Task superseded before architect review. Original scope was a one-line split description, not formal AC. Architect work was performed on #1104 where the merge decision was made — that's the appropriate evaluation target.

### Deduction Breakdown
- Start: 1.00
- Missing formal Review Evidence section (pass-through superseded task): -0.02
- Pre-existing test failures (0 in task scope): no deduction
- Pre-existing lint (0 in task scope): no deduction

### Confidence: .98
### Action: archive