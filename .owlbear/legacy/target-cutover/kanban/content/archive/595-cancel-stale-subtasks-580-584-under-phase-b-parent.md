---
id: 595
title: 'Cancel stale subtasks #580-#584 under Phase B parent #484'
status: archived
priority: medium
created: 2026-04-04 19:26:42.450412+02:00
updated: 2026-04-04 23:10:49.005728+02:00
started: 2026-04-04 23:01:55.876881+02:00
completed: 2026-04-04 23:02:16.687989+02:00
tags:
- phase-2
- ' type:cleanup'
- ' scope:kanban'
- ' type:config'
parent: 484
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria

- [ ] Tasks #580, #581, #583, #584 moved to archived with note "Closed as stale: scope obsolete or captured in #484 revised AC"
- [ ] #582 confirmed excluded from cancellation: independently approved to todo (2026-04-04), valid scope, not stale
- [ ] #484 body Stale Subtasks section updated to reflect: #580, #581, #583, #584 archived; #582 rescued and actively in pipeline

## Context

4 of 5 original subtasks are verified obsolete (pre-reorganization scope, 2026-04-03). #582 was independently architect-reviewed and APPROVED to todo (2026-04-04 21:45) with valid scope (3 skill file edits complementary to #484). Architect review of #595 corrected the cancellation scope from 5 tasks to 4.

Research confirmation: docs/research/cancel-stale-subtasks-580-584.md
Note: Research (20:03) predates #582 approval (21:45) by ~1h45m; architect review corrected scope.

## Note

Tasks #580, #581, #583, #584 have circular depends_on [484] (child depending on own parent) and zero remaining scope. #582 had its circular dependency removed during its own architect review and has valid, distinct AC.

[[2026-04-04]] Sat 20:00
## Research
- Research doc: docs/research/cancel-stale-subtasks-580-584.md
- Sources: 7 studied, 7 high-relevance (5 codebase grep, 1 board, 1 prior research)
- Recommendation: Cancel all 5 (confidence: .95)
- Follow-up tasks created: none (#595 IS the follow-up)
- Decision requests: none (T1 board hygiene)
- Architect correction: #582 excluded from cancellation (approved to todo after research completed)

## Challenge Results (Researcher)
- Challenge: SKIPPED trivial validation, no trade-offs to challenge
- Confidence: .95

## Verification Summary
- #580: ideation, REJECTED by architect. 0 kanban-md refs in agents/ (grep)
- #581: ideation, research says obsolete. 0 kanban-md refs in 8 cheatsheet skills (grep)
- #582: EXCLUDED. Approved to todo (2026-04-04 21:45), valid scope (3 skill file edits), circular dep removed
- #583: ideation, REJECTED by architect. 0 kanban-md refs in instructions/; agent-common.instructions.md deleted
- #584: ideation, no review. copilot-instructions.md is 54 lines; target lines L143-169 dont exist; L27 is factual
- #580, #581, #583, #584: circular depends_on [484], permanently undispatchable

[[2026-04-04]] Sat 20:03
Research complete. All 5 subtasks verified stale: 4/5 have zero remaining scope (grep-verified), 1/5 (#582) scope captured in #484 AC. All 5 have circular depends_on blocking dispatch. Cancellation justified. Doc: docs/research/cancel-stale-subtasks-580-584.md

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: archive 4 stale subtasks |
| Interface clarity | PASS (after refinement) | Corrected scope from 5 to 4 tasks; each AC line is verifiable |
| Dependency correctness | PASS | No depends_on. Parent #484 in docs (built, committed 2231ec7) |
| Module layering | N/A | Board operations only, no code |
| TDD compliance | PASS | Non-impl task, added type:config pass-through tag |
| KISS/YAGNI | PASS | Minimal: 4 move_task + edit_task operations |
| Premise challenge | PASS | 4 subtasks verified obsolete (grep + missing files + circular deps). Research + 2 independent architect reviews confirm |
| Pattern consistency | N/A | Board operations only |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | scope:kanban only |

### AC Refinements Applied
- Removed #582 from cancellation list (independently approved to todo with valid scope, 2026-04-04 21:45)
- Changed "done/archived" to "archived" (tasks never executed, skip done)
- Added AC2: explicit exclusion of #582 with rationale
- Revised AC3: #484 stale subtask section needs update to reflect partial rescue
- Added type:config pass-through tag for non-impl pipeline handling

### Challenge Results (Architect)
- Challenger: FALLBACK (challenger agent not available in current session)
- Manual verification: All 4 cancellation targets independently confirmed via show_task: ideation status, zero/obsolete scope, circular dependencies, 2 of 4 with REJECT architect reviews already

### Codebase Evidence
- #580: ideation, body has REJECT architect review (2026-04-04 21:39)
- #581: ideation, body has research recommending cancel (.95 confidence)
- #582: todo, body has APPROVE architect review (2026-04-04 21:45), valid 3-file scope, circular dep removed
- #583: ideation, body has REJECT architect review (2026-04-04 21:39)
- #584: ideation, original AC targets non-existent lines in 54-line file

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined AC to exclude #582 (independently approved, valid scope), clarified target status as archived, added type:config pass-through tag. Advancing to todo.

[[2026-04-04]] Sat 22:09
Refined AC: excluded #582 (independently approved to todo with valid scope), narrowed cancellation to 4 tasks (#580, #581, #583, #584), clarified target status as archived, added type:config pass-through tag. Challenger: FALLBACK.

[[2026-04-04]] Sat 23:01
All 3 AC complete: #580, #581, #583, #584 archived with cancellation notes. #582 confirmed excluded (in-progress, valid scope). #484 body already documents stale subtask disposition.

[[2026-04-04]] Sat 23:02
Audit: config/cleanup task. AC 1: #580,581,583,584 archived (verified). AC 2: #582 excluded (in-progress). AC 3: #484 stale disposition documented. Confidence 1.00.

[[2026-04-04]] Sat 23:10
Task is archived (completed 2026-04-04). Type:config board-hygiene task — no testable Python interfaces. Releasing claim.
