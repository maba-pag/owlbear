---
id: 593
title: 'Rewrite #486 AC to match current architecture'
status: archived
priority: medium
created: 2026-04-04 19:16:32.657697+02:00
updated: 2026-04-05 10:30:52.995510+02:00
started: 2026-04-05 10:30:52.995510+02:00
completed: 2026-04-05 10:30:52.995510+02:00
tags:
- scope:agents
- ' scope:skills'
- ' type:docs'
- ' phase-2'
depends_on:
- 484
class: standard
archival_reason: completed
archival_refs: []
---

## Objective

Rewrite the acceptance criteria for #486 (Phase C: Consolidate kanban references) to match the current workspace architecture.

## Context

Research (docs/research/consolidate-kanban-references.md) found that 2/7 original AC items reference `agent-common.instructions.md` which does not exist, and 2/7 describe states that already hold. The AC was written before the skills-based architecture solidified.

## Acceptance Criteria

- [ ] AC items 4–5 replaced: remove `agent-common.instructions.md` references, point to `r-pipeline-protocol` where the section-header mapping already lives
- [ ] AC item 2 revised: distinguish generic MCP callouts (safe to remove) from context-specific worked examples (keep)
- [ ] AC item 3 revised: agent files don't have kanban cheatsheets — remove or replace with accurate scope
- [ ] New AC: consolidate 7 identical Step 0 claiming blocks in w-* skills
- [ ] New AC: test compatibility verified (tool name strings preserved in skill bodies)
- [ ] Revised AC fits within the dependency chain (#484 → #486) — h-kanban-md retention honored

[[2026-04-04]] Sat 19:45
## Research
- Research doc: docs/research/rewrite-486-ac.md
- Sources: 6 studied, 5 high-relevance (all codebase/kanban)
- Recommendation: Replace 7 stale AC items with 7 verifiable items targeting selective consolidation (confidence: .82)
- Follow-up tasks created: none (this task IS the follow-up; revised AC is the deliverable)
- Decision requests: none (T1 — documentation refactor)

## Challenge Results
- Challenger: reconsider (confidence .72)
- Confidence in original: .82 (revised from .80 after incorporating feedback)
- Key challenges: C1 (cheatsheet heading — rebutted), C2 (survival matrix — accepted, added §3b), C4 (w-mem-curation scope — accepted, added §3c), C5 (AC 7 verifiability — accepted, replaced with concrete criteria)
- Researcher response: accepted 4/7, rebutted 2, noted 1 minor

[[2026-04-04]] Sat 19:59
Research validated prior findings; proposed 7-item replacement AC with test survival matrix. Doc: docs/research/rewrite-486-ac.md

[[2026-04-04]] Sat 21:47
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: rewrite #486's AC |
| Interface clarity | N/A | Deliverable is kanban task body edits |
| Dependency correctness | MOOT | #484 in review, but task is redundant |
| Module layering | N/A | Kanban metadata only |
| TDD compliance | PASS | Non-impl task (type:docs) |
| KISS/YAGNI | N/A | Deliverable already exists |
| Premise challenge | FAIL | Deliverable already incorporated into #486 during its architecture review |
| Pattern consistency | N/A | No changes to evaluate |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | Kanban documentation |

### Challenge Results
- Challenger: SKIPPED (REJECT verdict)

### Evidence of Redundancy
1. #486 already at todo with fully rewritten AC (7 verifiable items)
2. #486 AC matches proposed replacement from docs/research/rewrite-486-ac.md section 4
3. #486 architecture review explicitly consumed #593 research and recommends #593 archive
4. No remaining deliverable for #593 to produce

### Verdict: REJECT
### Action Taken: Rejected to ideation. Deliverable subsumed by #486 architecture review. Recommend dispatcher archive.

[[2026-04-05]] Sun 10:30
## Redundancy Confirmed (validation pass)\n- #486 now **archived** (audit confidence 1.00) — deliverable fully consumed\n- Research doc `.owlbear/research/rewrite-486-ac.md` complete (130 lines, 6 sources)\n- No remaining deliverable, no follow-up tasks needed\n- Archiving per architecture review recommendation
