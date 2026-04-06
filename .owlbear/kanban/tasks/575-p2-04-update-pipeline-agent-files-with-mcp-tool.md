---
id: 575
title: 'P2-04: Update pipeline agent files with MCP tool references alongside CLI'
status: done
priority: needed
created: 2026-04-03T11:15:13.4411362+02:00
updated: 2026-04-06T07:12:45.985583+02:00
tags:
    - phase-2
    - ' scope:agent-config'
    - ' type:build'
parent: 483
depends_on:
    - 572
    - 574
claimed_by: hill-reef
claimed_at: 2026-04-06T07:12:45.9782745+02:00
class: standard
---

## Acceptance Criteria\n\n- [ ] All 11 pipeline agent files updated with MCP tool alternatives alongside CLI examples\n- [ ] Agents: architect, auditor, builder, curator, kanban-planner, planner, researcher, reviewer, scribe, test-writer, writer\n- [ ] Each agent's inline CLI command examples show MCP equivalent (e.g., start_work/end_work for claim+show/advance+release)\n- [ ] Compound tools (start_work, end_work) documented as preferred pattern for task lifecycle\n- [ ] No existing CLI references removed (fallback preserved)\n- [ ] Must pass agent file checks in #572\n\n## Files\n\nagents/architect.agent.md, agents/auditor.agent.md, agents/builder.agent.md, agents/curator.agent.md, agents/kanban-planner.agent.md, agents/planner.agent.md, agents/researcher.agent.md, agents/reviewer.agent.md, agents/scribe.agent.md, agents/test-writer.agent.md, agents/writer.agent.md\n\n## Dependencies\n\nDepends on #574 (instructions update) so agents reference consistent MCP patterns from agent-common.

[[2026-04-05]] Sat 09:42
## Research
- Research doc: .owlbear/research/575-agent-mcp-lifecycle-audit.md
- Sources: 7 studied, 5 high-relevance (all codebase/kanban)
- Recommendation: Close as resolved-by-architecture (confidence: .78). v2 correctly factors MCP lifecycle: generic pattern in h-mcp-kanban skill (single source), agent-specific outcomes inline in kanban protocol. Original AC premise (CLI to MCP annotation) no longer applies.
- AC issues: lists 11 agents (10 exist, 9 should get blocks), names kanban-planner (absent) and writer (= doc-writer), includes scribe (never claims tasks)
- Follow-up tasks created: #625 at ideation (restore #574 pipeline protocol MCP callouts). #596 already at todo (planner skill language fix).
- Decision requests: none (all findings T1)

## Challenge Results
- Challenger: reconsider (confidence in original: .55, lowered from .82)
- Key challenges: C1 (DRY violation), C3 (2-variant oversimplifies), C4 (#574 is audit failure), C5 (no empirical gap)
- Researcher response: accepted C1/C3/C4/C5. Revised from full lifecycle blocks to close-as-resolved-by-architecture.

[[2026-04-06]] Mon 05:34
## Research (Validation Pass 2)
- Prior doc: .owlbear/research/575-agent-mcp-lifecycle-audit.md (2026-04-05, complete)
- Validation: all findings hold. 9 agents use pointer design, h-mcp-kanban lifecycle intact, 37 tests pass, no agent duplicates start_work/end_work
- Follow-up #625: archived (8/8 tests pass), #596: at todo
- AC still incorrect: lists 11 agents (9 exist as pipeline), names kanban-planner (absent) and writer (= doc-writer), scribe has no kanban protocol
- Recommendation confirmed: Close as resolved-by-architecture (confidence .85, up from .78)
- Challenge: skipped (validation pass, findings already challenged 2026-04-05)

[[2026-04-06]] Mon 06:08
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | N/A | Task should not proceed; premise obsolete |
| Interface clarity | FAIL | AC lists 11 agents (9 exist as pipeline), names kanban-planner (absent), writer (= doc-writer), includes scribe (no kanban protocol) |
| Dependency correctness | PASS | Both #572 and #574 archived/done |
| Module layering | N/A | Documentation task |
| TDD compliance | N/A | No implementation to test |
| KISS/YAGNI | FAIL | Duplicating lifecycle in 9 agents violates DRY when h-mcp-kanban already has the shared pattern |
| Premise challenge | FAIL | Capability exists via pointer design. No CLI commands in v2 agent bodies to annotate. |
| Pattern consistency | FAIL | Adding redundant lifecycle blocks would break v2 pointer-based factoring |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | scope:agent-config |

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| All 11 pipeline agent files updated | Only 9 pipeline agents exist. kanban-planner absent, writer = doc-writer, scribe has no kanban protocol. | INVALID |
| MCP alternatives alongside CLI examples | v2 agents have zero CLI commands in body. Premise obsolete. | OBSOLETE |
| Compound tools documented as preferred | h-mcp-kanban SKILL.md Agent Lifecycle Pattern already documents this. | ALREADY DONE |
| No existing CLI refs removed | No CLI refs exist in v2 agent bodies. | N/A |
| Must pass #572 tests | Original agent body assertions removed during v2 reorg. | INVALID |

### Codebase Evidence

- 9 pipeline agents at share/agents/: architect, auditor, builder, curator, doc-writer, planner, researcher, reviewer, test-writer
- All 9 use pointer design: "See h-mcp-kanban skill for tool workflows" in Kanban protocol section
- h-mcp-kanban SKILL.md documents Agent Lifecycle Pattern as single source of truth
- No kanban-planner.agent.md or writer.agent.md exists
- scribe.agent.md has no Kanban protocol section

### Research: Two passes (2026-04-05, 2026-04-06) recommend close-as-resolved-by-architecture, confidence .85

### Challenge Results
- Challenger: SKIPPED (REJECT verdict)

### Verdict: REJECT
### Action: Rejected to ideation. v2 architecture resolved through DRY factoring. Every AC line is factually incorrect, obsolete, or already satisfied.

[[2026-04-06]] Mon 06:43
## Research (Validation Pass 3)

### Validation Summary
- Prior doc: .owlbear/research/575-agent-mcp-lifecycle-audit.md (2026-04-05, complete)
- All prior findings confirmed. Codebase state unchanged.

### Codebase Evidence (verified 2026-04-06)
- 9 pipeline agents at share/agents/: architect, auditor, builder, curator, doc-writer, planner, researcher, reviewer, test-writer
- All 9 contain `See h-mcp-kanban skill for tool workflows` pointer (grep-verified, 9 matches)
- Zero `kanban-md` CLI references in any agent file
- h-mcp-kanban SKILL.md Agent Lifecycle Pattern documents start_work/end_work
- No kanban-planner.agent.md or writer.agent.md exists
- scribe.agent.md has no Kanban protocol section

### Follow-up Status
- #625 (restore #574 MCP callouts): archived, 5/8 tests fixed
- #596 (planner skill language): archived
- #640 (NEW): 3 remaining pipeline protocol MCP callout test failures — created at ideation

### AC Assessment (unchanged)
Every AC line is INVALID, OBSOLETE, or ALREADY SATISFIED — see architecture review above.

### Loop Detection
This is the 3rd research pass. Research→architect→reject→ideation loop detected. DR created to break the loop.

### Decision Request
DR: .owlbear/decisions/pending/575-close-as-resolved-by-architecture.md
Options: (A) close as resolved-by-architecture [recommended], (B) rewrite AC, (C) leave at ideation
Recommendation: Option A (confidence .85)

### Challenge
Skipped — validation pass only, findings already challenged 2026-04-05 and confirmed in two subsequent passes.



## Decision Resolved

User approved: **Close task #575 as resolved-by-architecture**

**Rationale from decision request:** All acceptance criteria are either invalid, obsolete, or already satisfied by v2 architecture. Three research passes (confidence .78→.85) and architecture review consensus confirm: every AC line is factually incorrect, v2 correctly factors MCP lifecycle through h-mcp-kanban skill (single source of truth), duplicating into 9 agent files violates DRY principle. Closing unblocks downstream task #625 and #596.

**Confidence:** 0.85

## Decision Resolved

**Decision:** A: Close task #575 as resolved-by-architecture

**Rationale:** Architecture review confirms all acceptance criteria are either invalid, obsolete, already satisfied, or violate DRY principle. All 9 existing pipeline agents implement the correct pattern via h-mcp-kanban skill pointers. No remaining legitimate requirements.
