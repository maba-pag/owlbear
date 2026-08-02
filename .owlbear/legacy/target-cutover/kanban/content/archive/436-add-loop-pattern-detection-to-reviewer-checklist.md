---
id: 436
title: Add loop-pattern detection to reviewer checklist
status: archived
priority: medium
created: 2026-03-30 21:45:59.710284+02:00
updated: 2026-03-31 03:51:52.967781+02:00
started: 2026-03-31 03:51:52.967781+02:00
completed: 2026-03-31 03:51:52.967781+02:00
tags:
- scope:agents
- phase-2
class: standard
archival_reason: completed
archival_refs: []
---

## Context
The reviewer agent should check for loop patterns when reviewing builder work. If Channel B notes show repeated identical attempts without approach variation, flag as a quality concern.

See docs/research/loop-detection-instruction-patterns.md S3 for analysis.

## Acceptance Criteria
- [ ] Reviewer code-review skill includes a check for repeated identical tool calls in builder notes
- [ ] Reviewer flags builders that hit tier 3 without handoff as a quality gap

[[2026-03-30]] Mon 23:41
## Research
Doc: docs/research/reviewer-loop-pattern-detection.md

Key findings:
- Reviewer needs new Step 6.7 (CRITICAL) checking builder Channel B notes for loop patterns
- Split severity: LOOP (identical retries or tier-3 without handoff) auto-FAILs; FRICTION (retries with variation) is informational
- Adapted from deer-flow warn/stop thresholds to instruction-based post-hoc detection

Follow-up tasks created:
- #454: Add Step 6.7 loop-detection check to code-review skill (needed)
- #455: Add loop-detection red flag to reviewer agent (important)

[[2026-03-31]] Tue 03:51
## Architecture Review
**Verdict:** Merge (delete as redundant)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Reviewer code-review skill includes a check for repeated identical tool calls | Fully covered by #454 AC (Step 6.7, retry counting, approach variation) | Superseded |
| Reviewer flags builders that hit tier 3 without handoff as a quality gap | Fully covered by #454 AC (LOOP assessment triggers automatic FAIL) | Superseded |

### Architecture Notes
The researcher decomposed this umbrella task into #454 and #455 with more precise, verifiable AC. #454 covers the code-review skill Step 6.7 with a severity model (LOOP/FRICTION/CLEAN). #455 covers the reviewer agent red flag with dependency on #454.

#436's AC is entirely subsumed by #454 + #455. Approving #436 to todo would create duplicate work. Deleting as redundant.

### Changes Made
- Deleted #436 (superseded by #454, #455)
- Surviving tasks: #454 (backlog), #455 (backlog, depends_on #454)
