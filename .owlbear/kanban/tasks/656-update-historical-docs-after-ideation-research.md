---
id: 656
title: Update historical docs after ideation→research rename
status: backlog
priority: nice-to-have
created: 2026-04-06T07:19:45.7935685+02:00
updated: 2026-04-06T15:09:55.2256816+02:00
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
