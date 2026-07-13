---
id: 435
title: Consolidate loop detection rules in agent-common.instructions.md
status: archived
priority: medium
created: 2026-03-30 21:45:53.967800+02:00
updated: 2026-03-31 05:33:02.335277+02:00
started: 2026-03-31 05:32:35.285164+02:00
completed: 2026-03-31 05:32:35.285164+02:00
tags:
- scope:agents
- phase-2
class: standard
archival_reason: completed
archival_refs: []
---

## Context
Consolidate scattered retry guidance (red flags line 204, terminal discipline line 249) into a single 'Loop detection and retry discipline' section. Add 3-tier escalation model and category-specific retry limits per docs/research/loop-detection-instruction-patterns.md.

See docs/research/loop-detection-instruction-patterns.md for full analysis.

## Acceptance Criteria
- [ ] New section 'Loop detection and retry discipline' in agent-common.instructions.md
- [ ] 3-tier escalation table (detect/adapt/stop) with concrete action per tier
- [ ] Category-specific retry limits table (exact same command: 1 retry, same logical op: 2, same goal: 3 total)
- [ ] Existing red flag 'max 2 retries' cross-references the new section
- [ ] Terminal discipline 'No brute-force retries' cross-references the new section
- [ ] Mandatory handoff/block after tier 3 with task body update requirement

[[2026-03-30]] Mon 22:18
## Architecture Review
**Verdict:** APPROVED (merged from #432)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| New 'Loop detection and retry discipline' section | Clear, verifiable â€” section exists or doesn't | Keep |
| 3-tier escalation table (detect/adapt/stop) | Concrete tiers with actions â€” testable | Keep |
| Category-specific retry limits table | Specific numbers (1/2/3) â€” mechanically verifiable | Keep |
| Red flag 'max 2 retries' cross-references new section | Verifiable â€” check line ~204 for xref | Keep |
| Terminal discipline cross-references new section | Verifiable â€” check line ~249 for xref | Keep |
| Mandatory handoff/block after tier 3 | Clear stop condition â€” verifiable | Keep |

### Architecture Notes
This is an instruction-file-only change (agent-common.instructions.md). No code, no tests needed.

Existing retry guidance locations verified:
- Line 204: red flags section, 'max 2 retries'
- Line 249: terminal discipline, 'No brute-force retries'

Both must cross-reference the new consolidated section, not be deleted (preserves in-context scanning).

Single domain: agents/instructions. No module layering concerns. No security surface changes.

### Merge Details
- #432 (Implement loop-detection pattern) merged into this task
- #432's implementation AC was a strict subset of #435's AC with vaguer language
- #432's research context preserved in docs/research/loop-detection-instruction-patterns.md (already referenced by #435)
- #432 deleted as redundant

### TDD Note
No test task needed â€” this is a markdown instruction file edit, not application code. Reviewer verifies content directly.

### Dependencies
- None required (standalone instruction edit)
- #436 (reviewer checklist) is independent â€” can proceed in parallel

[[2026-03-30]] Mon 23:46
## Test-Writer Notes
- Non-implementation task (scope:agents, instruction-file edit only) - no tests applicable.
- Architect confirmed: no test task needed, this is a markdown instruction file edit, not application code.
- Passing through to builder.

[[2026-03-31]] Tue 03:47
## Builder Notes
- Files changed: instructions/agent-common.instructions.md
- New section added: '## Loop detection and retry discipline' (line 254)
- 3-tier escalation table: Detect/Adapt/Stop with required actions
- Category-specific retry limits table (1/2/3 retries)
- Red flag cross-reference: line 204 (max 2 retries -- see Loop detection...)
- Terminal discipline cross-reference: line 249 (No brute-force retries -- see Loop detection...)
- Tier 3 mandatory handoff/block requirement included
- Commit: caf462a

[[2026-03-31]] Tue 05:32
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| New 'Loop detection and retry discipline' section | Section at L274 of agent-common.instructions.md | PASS |
| 3-tier escalation table (detect/adapt/stop) | Table at L280-284 with Detect/Adapt/Stop, concrete actions | PASS |
| Category-specific retry limits table (1/2/3) | Table at L288-292 with exact values matching AC | PASS |
| Red flag 'max 2 retries' cross-references new section | L224: 'see Loop detection and retry discipline below' | PASS |
| Terminal discipline cross-references new section | L269: 'See Loop detection and retry discipline below' | PASS |
| Mandatory handoff/block after tier 3 | 'Tier 3 is mandatory' paragraph at L286 | PASS |

### Test Results
- pytest: 1891 passed, 162 failed (all pre-existing, none in task scope)
- ruff: clean in task scope (pre-existing issues only)

### Architect Quality
- AC specificity: all 6 lines mechanically verifiable
- Edge case coverage: no gaps, builder needed no improvisation
- Design direction: arch correctly identified no tests needed for markdown-only change
- AC quality score: 5/5

### Commit Verification
- caf462a: docs: consolidate loop detection rules (#435, builder) - 1 file, +26 -2

### Deduction breakdown
- -.02 missing reviewer evidence section in task body
### Confidence: .98
### Action: archive

[[2026-03-31]] Tue 05:33
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| c3885ac | chore | kanban/tasks/435-*.md | #435 |
