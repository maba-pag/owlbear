# Agent MCP Lifecycle Audit — Task #575

> **Owning task:** #575 — P2-04: Update pipeline agent files with MCP tool references alongside CLI
> **Date:** 2026-04-05 **Status:** Complete

## 1. Context and Question

Task #575 AC calls for updating 11 pipeline agents with MCP tool alternatives
alongside CLI examples. Research question: is this work still needed after the v2
architecture reorganization, and if so, what is the correct scope?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | share/agents/*.agent.md (16 files, 9 pipeline) | Codebase | .95 |
| 2 | share/skills/h-mcp-kanban/SKILL.md (Agent Lifecycle) | Codebase | .95 |
| 3 | tests/test_mcp_tool_references_483.py (L161–164: removal comment) | Codebase | .90 |
| 4 | tests/test_mcp_tool_references_574.py (8 failing tests) | Codebase | .90 |
| 5 | .owlbear/research/rescope-575-lifecycle-blocks.md (#594) | Research | .85 |
| 6 | Task #594 body (archived as superseded, AC never rewritten) | Kanban | .85 |
| 7 | share/skills/r-pipeline-protocol/SKILL.md (MCP refs) | Codebase | .80 |

## 3. Analysis

### 3a. AC Validity

| AC Item | Current State | Assessment |
|---------|--------------|------------|
| "11 pipeline agents" | 10 exist; kanban-planner absent, "writer" = doc-writer | **Wrong** |
| "MCP alternatives alongside CLI" | v2 agents have zero CLI commands in body | **Obsolete premise** |
| "scribe" included | Scribe never claims tasks, no kanban protocol section | **Should exclude** |
| "Compound tools as preferred" | h-mcp-kanban SKILL.md already documents this | **Already done** |
| "No CLI refs removed" | No CLI refs exist to preserve | **N/A** |
| "Pass #572 tests" | Agent body tests removed at reorg (L161–164 comment) | **Tests don't exist** |

### 3b. Current Agent Lifecycle Factoring

All 9 pipeline agents follow identical structure in `### Kanban protocol`:

```
- Section header: `## {Agent-Specific Section}`    ← Channel B identity
- On {outcome}: `end_work(outcome="...", ...)`      ← agent-specific routing
- Follow-ups: via {agents}                          ← agent-specific
- See `h-mcp-kanban` skill for tool workflows       ← shared lifecycle pointer
```

**What's inline:** agent-specific outcomes, targets, section headers.
**What's delegated:** generic lifecycle (start_work → edit_task → end_work) via h-mcp-kanban.

This is correct DRY factoring. `start_work(task_id)` is identical for all 9 agents —
no agent-specific parameters. Duplicating it 9 times violates KISS/DRY.

### 3c. Options Comparison

| Criterion | A: Close as resolved | B: Full lifecycle blocks (original rec) | C: Minimal 1-line additions |
|-----------|---------------------|----------------------------------------|----------------------------|
| DRY compliance | Best — no duplication | **Worst** — 9× identical start_work | Good — 1 line per agent |
| Agent self-documentation | Current (adequate) | Highest (redundant) | Slightly better |
| Token budget | Best — no bloat | Worst — ~27 extra lines | Minimal — ~9 extra lines |
| Maintenance burden | None | High — sync h-mcp-kanban changes to 9 files | Low |
| Empirical need | No evidence of agents failing lifecycle | Speculative | Speculative |
| Test scope | None needed | 27+ new assertions | 9 new assertions |
| Confidence | **.78** | .55 (post-challenge) | .70 |

### 3d. #574 Pipeline Protocol Regression

8 tests fail in test_mcp_tool_references_574.py. Task #574 was archived but its
MCP callout additions to agent-common.instructions.md were NOT carried over when
that file became r-pipeline-protocol/SKILL.md during the v2 reorganization.

This is an audit failure: archived task with failing acceptance tests. The correct
action is to unarchive #574 and send it back through the pipeline, not create a
laundering follow-up task.

## 4. Recommendation

**Option A: Close #575 as resolved-by-architecture.** Confidence: .78.

The v2 architecture correctly factors the MCP lifecycle:
- Generic lifecycle in h-mcp-kanban (shared, single source)
- Agent-specific outcomes inline in `### Kanban protocol`
- Tools declared via frontmatter `tools:` array

The original AC premise (CLI→MCP annotation) no longer applies. No empirical evidence
that agents fail to follow the lifecycle with the current pointer-based design.

**Separate action:** Unarchive #574 to fix the 8-test regression in pipeline protocol.

Challenge: reconsider (confidence in original B: .55, lowered from .82). Key challenges
accepted: C1 (DRY — start_work is identical for all agents), C3 (2-variant oversimplifies),
C4 (#574 is audit failure), C5 (no empirical gap). Revised to Option A.

## 5. Follow-up Tasks

1. Unarchive #574 — restore pipeline protocol MCP callouts (8 failing tests)
2. #596 already at todo — planner skill language fix (from prior research)
