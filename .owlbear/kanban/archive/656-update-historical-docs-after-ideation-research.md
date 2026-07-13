---
id: 656
title: Update historical docs after ideation→research rename
status: archived
priority: medium
created: 2026-04-06T07:19:45.7935685+02:00
updated: 2026-04-07T12:54:51.6771696+02:00
started: 2026-04-07T12:54:51.6771696+02:00
completed: 2026-04-07T12:54:51.6771696+02:00
tags:
    - phase-4
    - ' scope:docs'
    - ' type:chore'
depends_on:
    - 641
class: standard
---

## Acceptance Criteria

- [ ] Prose references to "ideation" as a kanban status updated to "research" in `.owlbear/research/*.md`
- [ ] Prose references updated in `.owlbear/decisions/resolved/*.md`
- [ ] Pipeline flow diagrams in docs updated (ideation → research)

## Context

After #641 renames the functional status, ~150+ historical prose references remain in research docs, decision files, and task bodies. These don't break functionality but cause confusion when agents read them. Low priority — historical documents can retain original terminology as-is if needed.

## Scope

- `.owlbear/research/*.md` — prose references to "ideation" status
- `.owlbear/decisions/resolved/*.md` — prose references
- Exclude: task body files in `.owlbear/kanban/tasks/` (too many, historical record)

## Risk

Low. Prose-only changes. No functional impact.

[[2026-04-06]] Mon 15:09
## Research
- Research doc: .owlbear/research/historical-ideation-prose-cleanup.md
- Sources: 6 studied, 4 high-relevance (all codebase-internal)
- Recommendation: Accept historical docs as-is — no mass prose update (confidence: 0.85)
- Follow-up tasks created: none (YAGNI — if confusion arises, create targeted task then)
- Decision requests: none

### Key Findings
- **Blast radius**: 412 references across 215 research files + 11 across 5 decision files
- **68% are historical records** (236 CLI command snippets + 51 table snapshots) — updating these falsifies history
- **Functional rename complete**: 0 stale refs in active system files (config, Python, agents, skills, instructions)
- **Agent consumption pattern**: research docs read for context, not prescriptive execution. Self-correcting: MCP server rejects "ideation" as status.
- **AC over-scoped**: Mass update of 220 files counterproductive. Task context says "historical documents can retain original terminology as-is if needed."
- **Tier: T1** — prose-only, no functional impact

## Challenge Results
- Challenger: FALLBACK — not in agent roster
- Confidence in original: 0.85
- Key challenges: self-assessed — bulk rename falsifies historical CLI commands, provides negligible agent confusion reduction
- Researcher response: accepted — recommend closing with narrowed scope

[[2026-04-06]] Mon 16:27
## Architecture Review\n### Evaluation\n| Criterion | Assessment | Notes |\n|-----------|-----------|-------|\n| Single responsibility | PASS | One concern: docs prose update |\n| Interface clarity | FAIL | AC asks for mass updates across 220 files; research proves this counterproductive |\n| Dependency correctness | PASS | #641 archived |\n| Module layering | N/A | Docs only |\n| TDD compliance | N/A | Docs only |\n| KISS/YAGNI | FAIL | Research explicitly invokes YAGNI; 68% of refs are historical CLI commands/table snapshots |\n| Premise challenge | FAIL | Functional rename complete (0 stale refs in active system files); MCP server self-corrects by rejecting 'ideation' as status |\n| Pattern consistency | PASS | Standard docs update pattern |\n| Security surface | PASS | No security implications |\n| Single domain | PASS | Docs domain only |\n\n### Key Evidence\n- Research doc: .owlbear/research/historical-ideation-prose-cleanup.md\n- 412 references across 220 files, but 68% are historical records (CLI commands, table snapshots)\n- 0 stale refs in active system files (config, Python, agents, skills, instructions)\n- Task context itself says: 'historical documents can retain original terminology as-is if needed'\n- Research recommendation: Option C (accept as-is), confidence 0.85\n\n### Challenge Results\n- Challenger: FALLBACK (not in agent roster)\n- Architect response: self-assessed; no architecture to challenge for a task whose own research recommends closure\n\n### Verdict: REJECT\n### Action Taken: Rejected to research. The task's own research conclusively proves the work is counterproductive. Mass-updating 412 historical prose references falsifies CLI command history with negligible agent confusion reduction. The functional rename (#641) is 100% complete in all active system files. Recommend archiving this task. If future confusion arises from historical prose, create a targeted task then (YAGNI).

[[2026-04-06]] Mon 16:43
## Research (Validation Pass)
Re-validated after architect rejection. All original findings hold:
- 0 stale refs in production code (agents, skills, instructions, serve/*.py)
- test_planner_gates.py uses status="ideation" in fixture but check_clarity() uses set-exclusion logic — no functional bug
- Research doc present: .owlbear/research/historical-ideation-prose-cleanup.md
- Original confidence: 0.85, unchanged after validation

Recommendation: archive immediately — no implementation work warranted. Both research rounds and architecture review concur. Mass-updating 412 historical prose references falsifies CLI command history with negligible benefit. Task context explicitly permits retaining original terminology.

Follow-up tasks: none (YAGNI)
Decision requests: none
Tier: T1

[[2026-04-06]] Mon 17:29
## Architecture Review (2nd Pass)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: docs prose update |
| Interface clarity | FAIL | AC demands mass updates across 220 files; research proves counterproductive |
| Dependency correctness | PASS | #641 archived |
| Module layering | N/A | Docs only |
| TDD compliance | N/A | Docs only |
| KISS/YAGNI | FAIL | 68% of refs are historical CLI commands/table snapshots — updating them falsifies history |
| Premise challenge | FAIL | 0 stale refs in active system files; MCP server self-corrects by rejecting "ideation" as status |
| Pattern consistency | PASS | Standard docs update pattern |
| Security surface | PASS | No security implications |
| Single domain | PASS | Docs domain only |

### Key Evidence
- Prior arch review: REJECT (same 3 FAILs)
- Research validation pass: confirmed all findings, 0.85 confidence unchanged
- Researcher explicitly recommended "archive immediately"
- Task context itself: "historical documents can retain original terminology as-is if needed"
- No new information or scope changes since last cycle

### Challenge Results
- Challenger: SKIPPED — REJECT verdict, no challenge required
- Prior cycle challenger: FALLBACK — self-assessed, confirmed rejection rationale

### Verdict: BLOCK FOR ARCHIVAL
### Action Taken: Blocked instead of rejecting to research (which would create infinite loop). This is the 2nd architect review with identical findings. All 4 pipeline analyses (2x research, 2x architect) unanimously agree: no implementation work warranted. The functional rename (#641) is 100% complete. Recommend orchestrator archives this task immediately. If future agent confusion from historical prose materializes, create a targeted task then (YAGNI).
