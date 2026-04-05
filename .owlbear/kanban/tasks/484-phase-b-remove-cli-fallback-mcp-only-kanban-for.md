---
id: 484
title: 'Phase B: Remove CLI fallback, MCP-only kanban for all agents'
status: ideation
priority: needed
created: 2026-03-31T06:20:55.32467+02:00
updated: 2026-04-05T10:15:15.3697932+02:00
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

[[2026-04-05]] Sun 07:32
## Research (Validation Pass)
- Validation of architect's REJECT finding (2026-04-04): **CONFIRMED**
- git grep kanban-md across share/ and .github/: 0 matches in agents, 0 in active skills, 0 in instructions (AC scope)
- Remaining refs: h-kanban-md (deprecated skill, 23), h-mcp-kanban (server internals, 5), owlbear-system (tech stack table, 1), h-pytest-and-linting (test marker, 1) — all out of scope
- All 7 AC items satisfied by workspace reorganization (agents/ → share/agents/, etc.)
- Recommendation: archive #484 and #582 — zero remaining scope
- Confidence: .95 (verified by independent grep, no ambiguity)
- Challenge: SKIPPED — confirming completed work, no new recommendation
- Follow-up tasks: none (subtasks #580-#584 already cancelled/archived except #582 which should be archived)
- T1 classification — no decisions needed

[[2026-04-05]] Sun 10:15
## Architecture Review (2nd pass)

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | N/A | Parent umbrella with no independent deliverable |
| Interface clarity | N/A | — |
| Dependency correctness | PASS | #483 archived |
| Module layering | N/A | — |
| TDD compliance | N/A | — |
| KISS/YAGNI | N/A | — |
| Premise challenge | **FAIL** | Nearly all scope already delivered; residual covered by #582 |
| Pattern consistency | N/A | — |
| Security surface | N/A | — |
| Single domain | N/A | — |

### Independent Verification

Grep kanban-md across current workspace (share/):

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: refs removed from agent files | share/agents/ = 0 matches | DONE |
| AC2: refs removed from skill cheatsheets | Active skills = 0. Deprecated h-kanban-md has 16+ refs | MOSTLY DONE |
| AC3: agent-common Channel B MCP-only | L6-8: edit_task with append_body, references h-mcp-kanban | DONE |
| AC4: PS escaping removed | Section does not exist in current file | DONE |
| AC5: research-docs MCP-only | share/instructions/ = 0 matches | DONE |
| AC6: 0 grep matches in agents/ and skills/ | agents/ = 0; skills/ has h-kanban-md (16, deprecated), h-mcp-kanban (5, server internals), h-pytest-and-linting (1, test marker) | NOT MET (strictly) |
| AC7: Pipeline agents function MCP-only | Current operational state | DONE |

### Correction to Prior Reviews

The 2026-04-04 architect and 2026-04-05 researcher both classified h-kanban-md as "out of scope." Incorrect: AC6 specifies "0 matches in skills/" which includes h-kanban-md. However, subtask #582 was created for this residual scope and has its own AC targeting h-kanban-md. Prior recommendations to archive #582 as "zero scope" were wrong per #582's own research (2026-04-05 07:48) confirming 16 CLI refs remain.

### Disposition

#484 is a parent umbrella. Its only unsatisfied AC (item 6) is fully covered by subtask #582, which has independent, well-researched AC. No deliverable that #484 can produce beyond what #582 will deliver.

Dependency issue: #582 depends_on [484] creates a circular reference (subtask depending on parent). Must be removed so #582 can proceed after #484 is archived.

### Challenge Results
- Challenge: SKIPPED (REJECT verdict, not required per w-arch-review Step 2.5)

### Verdict: REJECT
### Action Taken
Rejected to ideation. Recommend: (1) Archive #484, (2) Remove #582 dep on #484, (3) Review #582 independently — it has real scope.
