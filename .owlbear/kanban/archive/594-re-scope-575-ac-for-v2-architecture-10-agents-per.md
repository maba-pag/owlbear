---
id: 594
title: 'Re-scope #575 AC for v2 architecture: 10 agents, per-agent MCP lifecycle blocks'
status: archived
priority: medium
created: 2026-04-04 19:17:51.528669+02:00
updated: 2026-04-04 21:48:04.523495+02:00
started: 2026-04-04 21:48:04.523495+02:00
completed: 2026-04-04 21:48:04.523495+02:00
tags:
- phase-2
- ' scope:agent-config'
- ' type:build'
parent: 575
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria

- [ ] #575 AC rewritten for v2 architecture:
  - Agent list: 10 agents (architect, auditor, builder, curator, doc-writer, planner, researcher, reviewer, scribe, test-writer). Exclude kanban-planner (does not exist yet).
  - "writer" corrected to "doc-writer"
  - Each agent gets a 3-line MCP lifecycle block in `<output_format>` section showing agent-specific `start_work` / `edit_task` (with unique Channel B section name) / `end_work` (with agent-specific outcome patterns)
  - Lightweight test assertion: each pipeline agent body contains `start_work` and `end_work`
  - #574 dependency relaxed (lifecycle blocks are agent-specific, independent of protocol-level MCP callouts)
- [ ] Compound tools (start_work, end_work) documented as preferred pattern
- [ ] No structural changes to agent files (additive only)

## Context

Research doc: docs/research/update-pipeline-agents-mcp-refs.md
Original AC was based on v1 assumptions (CLI examples in agent bodies). v2 agents have zero CLI commands in bodies. Re-scope adds per-agent MCP lifecycle examples instead, short-circuiting the 3-hop indirection chain (agent → r-pipeline-protocol → h-mcp-kanban) for the core claim/work/advance pattern.

## Rationale

Challenger found original close-as-obsolete recommendation too aggressive (.45 confidence). Per-agent lifecycle blocks are context-specific (unique Channel B section headers, outcome values per agent), making them not a pure DRY violation.

[[2026-04-04]] Sat 20:10
## Research
- Research doc: docs/research/rescope-575-lifecycle-blocks.md
- Sources: 6 studied, 6 high-relevance (all codebase/kanban)
- Recommendation: 9 agents get lifecycle blocks (exclude scribe), two variants: 3-line success-only and 4-line success+reject. Conditional qualifier for planner/curator. (confidence: .80)
- Follow-up tasks created: #596 at ideation (fix planner skill language)
- Decision requests: none (T1 documentation scope refinement)

## Challenge Results
- Challenger: proceed with reservations (confidence: .72)
- Key challenges accepted: C1 (reject paths needed for 5 agents), C3 (AC must say 9 not 10), C6 (conditional qualifier for planner/curator)
- Deferred: C2 (planner skill language) to #596
- Researcher response: accepted C1/C3/C6, deferred C2. Revised block spec from uniform 3-line to variant 3-4 line.

[[2026-04-04]] Sat 20:11
Research complete. 9 agents (exclude scribe), two lifecycle block variants, conditional qualifier for planner/curator. Follow-up #596 at ideation. Doc: docs/research/rescope-575-lifecycle-blocks.md

[[2026-04-04]] Sat 21:47
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single purpose: rewrite #575 AC |
| Interface clarity | PASS | AC items are specific and verifiable |
| Dependency correctness | PASS | No deps listed, none needed |
| Module layering | N/A | Meta-task (AC editing), no code changes |
| TDD compliance | N/A | Meta-task |
| KISS/YAGNI | PASS | Minimal scope |
| Premise challenge | **FAIL — SUPERSEDED** | #575 architecture review already absorbed this task's entire deliverable. All AC items fulfilled in #575's revised AC at `todo`. |
| Pattern consistency | PASS | Research-to-architecture flow is standard |
| Security surface | PASS | No system boundaries |
| Single domain | PASS | scope:agent-config |

### Challenge Results
- Challenger: SKIPPED (REJECT verdict — challenge not required)

### Verdict: REJECT (superseded)
### Action Taken: All AC items already fulfilled via #575 architecture review (which rewrote #575's AC using #594's research). #575 is at `todo` with revised AC specifying 9 agents, 2 lifecycle variants, scribe excluded. Approving #594 would create a duplicate pipeline entry with no deliverable. Archiving as superseded. Follow-up #596 (planner skill language) remains at ideation independently.
