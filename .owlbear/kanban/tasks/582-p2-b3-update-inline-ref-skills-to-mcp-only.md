---
id: 582
title: 'P2-B3: Update inline-ref skills to MCP-only'
status: todo
priority: needed
created: 2026-04-03T16:42:36.5956013+02:00
updated: 2026-04-05T10:20:02.7524845+02:00
tags:
    - scope:skills
    - ' scope:mcp'
    - ' phase-2'
    - ' type:build'
    - docs
parent: 484
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

[[2026-04-05]] Sun 10:19
Releasing claim for AC refinement and architecture review append.

[[2026-04-05]] Sun 10:19
## Architecture Review

### Refined AC (binding, supersedes original)
- [ ] AC1: w-dispatch-planning, w-decision-routing, w-orchestration, w-research contain 0 kanban-md.exe refs (pre-verified done, no action needed)
- [ ] AC2: h-kanban-md/SKILL.md reduced to thin redirect (~20 lines): YAML frontmatter (keep deprecated description) + title + deprecation notice + Board Configuration section (statuses/priorities from current L126-L130) + cross-refs to h-mcp-kanban (tool params, lifecycle) and r-pipeline-protocol (claiming conventions)
- [ ] AC3: h-kanban-md/SKILL.md contains 0 kanban-md.exe references (strip L11, L34-36, L96-175 — all CLI command/recipe/escaping content)
- [ ] AC4: grep verification: 0 matches for kanban-md.exe across share/skills/{w-dispatch-planning,w-decision-routing,w-orchestration,w-research,h-kanban-md}/

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: strip CLI content from h-kanban-md, replace with thin redirect |
| Interface clarity | PASS (after refinement) | Original AC2 ambiguous ("uses MCP tool syntax" vs remove-and-redirect); refined AC specifies exact end-state |
| Dependency correctness | PASS | No dependencies; 4/5 files pre-verified clean |
| Module layering | N/A | Documentation-only task |
| TDD compliance | N/A | No Python code; docs pass-through tag added |
| KISS/YAGNI | PASS | Thin redirect is minimal approach; no content duplication with h-mcp-kanban |
| Premise challenge | PASS | h-kanban-md has 16 CLI refs and 0 active consumers — cleanup justified |
| Pattern consistency | PASS | Deprecation notice pattern already in place (L7-9) |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | Documentation migration only |

### Codebase Evidence
- h-kanban-md has 0 references from active agents/skills/instructions (grep verified)
- h-mcp-kanban covers: lifecycle (Agent Lifecycle Pattern), body gotchas, compound tools, tool params
- h-mcp-kanban does NOT cover board config (statuses/priorities) — retained in h-kanban-md
- 16 CLI refs all in h-kanban-md: L11, L34-36, L96, L102, L108, L114, L120, L133, L136, L145, L148, L157, L160, L175
- config.yml at .owlbear/kanban/config.yml is source of truth for board config

### Challenge Results
- Challenger: PROCEED (0.85)
- Key findings: zero active consumers confirmed; board config retention justified (not in h-mcp-kanban); PS escaping section obsolete with MCP
- Architect response: accepted

### Verdict: APPROVE (via REFINE)
### Action Taken: Refined AC2 from ambiguous "uses MCP tool syntax" to specific thin-redirect spec. Added docs pass-through tag. Advanced to todo.
