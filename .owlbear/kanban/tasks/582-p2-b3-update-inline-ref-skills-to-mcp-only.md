---
id: 582
title: 'P2-B3: Update inline-ref skills to MCP-only'
status: backlog
priority: needed
created: 2026-04-03T16:42:36.5956013+02:00
updated: 2026-04-05T07:48:03.4596898+02:00
tags:
    - scope:skills
    - ' scope:mcp'
    - ' phase-2'
    - ' type:build'
parent: 484
depends_on:
    - 484
class: standard
---

**Source:** docs/research/phase-b-mcp-only-kanban-migration.md §3a\n\nUpdate 5 skill files that have inline (non-cheatsheet) CLI references: dispatch-planning, decision-requests, kanban-md, orchestration, research-workflow.\n\nThe kanban-md SKILL.md requires special handling: its claiming protocol examples should use MCP syntax. The skill's purpose shifts from CLI reference to MCP claiming protocol reference (the mcp-kanban skill already covers tool parameters).\n\n**AC:**\n- [ ] dispatch-planning, decision-requests, orchestration, research-workflow use MCP calls\n- [ ] kanban-md SKILL.md claiming protocol uses MCP tool syntax\n- [ ] kanban-md SKILL.md cross-references mcp-kanban for full tool parameters\n- [ ] 0 kanban\\kanban-md.exe matches in these 5 files (grep verification)

[[2026-04-05]] Sun 07:48
## Research (Scope Correction)

### Architect REJECT Override

The 2026-04-04 architect REJECT and 2026-04-05 validation both excluded h-kanban-md from scope, classifying it as "deprecated, out of scope." Incorrect: the AC explicitly names h-kanban-md as one of the 5 target files.

### Independent Grep Verification

| File | kanban-md.exe refs | Status |
|------|-------------------|--------|
| w-dispatch-planning | 0 | DONE |
| w-decision-routing | 0 | DONE |
| w-orchestration | 0 | DONE |
| w-research | 0 | DONE |
| h-kanban-md | 16 | NOT DONE |

4/5 files already use MCP tool names exclusively (list_tasks, show_task, etc.). h-kanban-md still has 16 CLI refs (claiming L34-36, recipes L96-175, escaping L133-175).

### Residual Scope: h-kanban-md Only

h-kanban-md is deprecated and orphaned (0 references from active agents, skills, or instructions). AC items 2-4 unsatisfied.

### Recommendation: Option A, Thin Redirect (.85 confidence)

Per prior research (inline-ref-skills-mcp-migration.md section 3b): strip CLI content, retain title + deprecation notice + board config (statuses/priorities) + cross-ref to h-mcp-kanban. Result: ~20-line file. h-mcp-kanban covers lifecycle, body gotchas, tool params — no duplication.

T1 classification. Pre-approved documentation migration.

### AC After Option A
- AC1: 4 files use MCP calls (done)
- AC2: Claiming protocol removed; deprecation points to h-mcp-kanban lifecycle
- AC3: Cross-reference to h-mcp-kanban retained
- AC4: 0 kanban-md.exe matches across all 5 files

### Challenge Results
- Challenger: FALLBACK (agent not available in session)
- Prior challenge (inline-ref-skills-mcp-migration.md section 4): reconsider, accepted and incorporated
- Confidence: .85

Follow-up tasks: none (this task IS the implementation)
Decision requests: none (T1)
