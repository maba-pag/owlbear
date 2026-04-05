---
id: 484
title: 'Phase B: Remove CLI fallback, MCP-only kanban for all agents'
status: ideation
priority: needed
created: 2026-03-31T06:20:55.32467+02:00
updated: 2026-04-04T23:55:40.1162575+02:00
tags:
    - scope:mcp
    - ' scope:agents'
    - ' scope:skills'
    - ' type:build'
    - ' phase-2'
depends_on:
    - 483
class: standard
---

## Objective\n\nRemove all CLI fallback references from agent files, skill files, and instructions. MCP tools become the sole kanban interface for agents.\n\n## Acceptance Criteria\n\n- [ ] All kanban\\kanban-md.exe references removed from agent files (10 files)\n- [ ] All kanban\\kanban-md.exe references removed from skill cheatsheets (10 files)\n- [ ] agent-common.instructions.md Channel B section uses MCP-only syntax\n- [ ] PowerShell escaping guidance removed from agent-common.instructions.md (pipe escaping, arrow parsing, temp-file pattern — all obsolete with MCP)\n- [ ] research-docs.instructions.md updated to MCP-only\n- [ ] No agent references kanban-md.exe directly (grep verification: 0 matches in agents/ and skills/)\n- [ ] All pipeline agents still function correctly with MCP-only path\n\n## Scope\n\nSame ~22 files as Phase A. Historical research docs (docs/research/*.md) keep their CLI references — they're records, not instructions.\n\n## Dependencies\n\n- Depends on: #483 (Phase A complete and validated)

[[2026-04-03]] Fri 16:43
## Research\nDoc: docs/research/phase-b-mcp-only-kanban-migration.md\n\nKey findings:\n- 144 CLI refs across 27 files (11 agents, 13 skills, 2 instructions, 1 copilot-instructions)\n- AC undercounts: says 10 agents/10 skills, actual is 11/13. Architect should correct.\n- MCP coverage gaps: no delete_task or handoff tools. Architect must decide: add to MCP or document as terminal-only exceptions.\n- copilot-instructions.md should be in scope (loaded by all agents)\n- PS escaping section in agent-common becomes fully obsolete\n\nSubtasks created:\n- #580 P2-B1: Agent files MCP-only (11 files, 44 refs)\n- #581 P2-B2: Skill cheatsheet tables (8 files, ~82 refs)\n- #582 P2-B3: Inline-ref skills (5 files, ~13 refs)\n- #583 P2-B4: Instruction files rewrite (2 files, 8 refs)\n- #584 P2-B5: copilot-instructions.md MCP-primary (~7 refs)\n\n## Challenge Results\n- Challenger recommendation: block (confidence in original: .55)\n- Key challenges: AC undercounting (accepted), delete/handoff MCP gaps (accepted), copilot-instructions exclusion (accepted), dependency timing (accepted), T2 reclassification (rebutted)\n- Researcher response: revised confidence .80 to .70, expanded scope to include copilot-instructions, documented MCP gaps for architect decision, maintained T1 classification (pre-approved user plan)

[[2026-04-04]] Sat 23:55
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | N/A | Task has zero remaining scope — see Premise Challenge |
| Interface clarity | N/A | — |
| Dependency correctness | PASS | #483 archived |
| Module layering | N/A | — |
| TDD compliance | N/A | — |
| KISS/YAGNI | N/A | — |
| Premise challenge | **FAIL** | All AC items already satisfied. See evidence below. |
| Pattern consistency | N/A | — |
| Security surface | N/A | — |
| Single domain | N/A | — |

### Premise Challenge — Scope Already Complete

The workspace reorganization (agents/ → .github/agents/, skills/ → .github/skills/, instructions/ → .github/instructions/) rewrote all targeted files. CLI references were eliminated as part of that restructuring. Verified via grep:

| AC Line | Evidence | Status |
|---------|----------|--------|
| kanban-md refs removed from agent files (10) | grep kanban-md .github/agents/ = 0 matches | Already done |
| kanban-md refs removed from skill cheatsheets (10) | grep .github/skills/ = 0 in active skills; only deprecated h-kanban-md has refs | Already done |
| agent-common Channel B uses MCP-only | L6-8: references edit_task with append_body, points to h-mcp-kanban | Already done |
| PS escaping guidance removed | Section does not exist in current file | Already done |
| research-docs.instructions.md MCP-only | grep .github/instructions/ = 0 matches | Already done |
| No agent refs kanban-md.exe (grep 0) | Confirmed: 0 matches in agents/ and active skills/ | Already done |
| Pipeline agents function on MCP-only | Current operational state | Already done |

Remaining kanban-md references (not in scope): h-kanban-md/SKILL.md (deprecated), h-mcp-kanban/SKILL.md (2 server-internal refs), copilot-instructions.md (1 tech stack table ref).

Subtask status: #580, #581, #583, #584 archived (cancelled, zero scope). #582 at ideation (also stale). Recommend archiving #582.

### Challenge Results
- Challenge: SKIPPED (REJECT verdict, not required per w-arch-review Step 2.5)

### Verdict: REJECT
### Action Taken: Rejected to ideation. All AC items already satisfied by workspace reorganization. No deliverable possible. Recommend archiving parent #484 and remaining subtask #582.
