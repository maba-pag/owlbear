# Re-scope #575: Per-Agent MCP Lifecycle Blocks

> **Owning task:** #594 — Re-scope #575 AC for v2 architecture: 10 agents, per-agent MCP lifecycle blocks
> **Date:** 2026-04-04 **Status:** Complete

## 1. Context and Question

Task #594 refines the research from `docs/research/update-pipeline-agents-mcp-refs.md` (Option B). The question: what exactly should each agent's MCP lifecycle block contain, which agents should receive one, and what test assertions are needed?

The original AC lists 10 agents including scribe. This research validates that list and specifies per-agent block content.

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `.github/agents/*.agent.md` (10 files) | Codebase | .95 — output_format sections, Channel B definitions |
| 2 | `.github/skills/w-*/SKILL.md` (10 workflow skills) | Codebase | .95 — existing MCP lifecycle refs in skills |
| 3 | `r-pipeline-protocol` § 3 Per-Agent Signal Mapping | Codebase | .90 — canonical Channel B section names |
| 4 | `h-mcp-kanban` Agent Lifecycle Pattern section | Codebase | .90 — standard 3-call lifecycle |
| 5 | `packages/orchestrator/src/owlbear/planner/selector.py` | Codebase | .85 — STATUS_AGENT_MAP excludes scribe |
| 6 | `w-decision-routing` L15 | Codebase | .85 — scribe "does NOT claim a task" |

## 3. Analysis

### 3a. Agent Classification

| Agent | Dispatched from board? | Claims task? | Has reject path? | Conditional lifecycle? |
|-------|----------------------|-------------|-------------------|----------------------|
| architect | Yes (backlog) | Yes | Yes (reject → ideation) | No |
| auditor | Yes (done) | Yes | Yes (reject → backlog) | No |
| builder | Yes (in-progress) | Yes | Yes (reject → todo/backlog) | No |
| curator | Yes (conditional) | Yes | No (success only) | Yes (user-invocable) |
| doc-writer | Yes (docs) | Yes | Yes (reject → review) | No |
| planner | Yes (conditional) | Yes | No (success only) | Yes (user-invocable) |
| researcher | Yes (ideation) | Yes | No (success only) | No |
| reviewer | Yes (review) | Yes | Yes (reject → varies) | No |
| **scribe** | **Never** | **Never** | N/A | N/A |
| test-writer | Yes (todo) | Yes | No (success only) | No |

Evidence for scribe exclusion: (1) absent from `STATUS_AGENT_MAP`, (2) w-decision-routing L15: "does NOT claim a task", (3) `## Output Contract` instead of `<output_format>`, (4) operates as subagent for calling agents.

### 3b. Lifecycle Block Variants

**Variant 1 — Success-only (4 agents: researcher, curator, planner, test-writer):**
```
### MCP Lifecycle
> `start_work("{id}")` → `edit_task("{id}", append_body="## {Section}\n...", timestamp=True)` → `end_work("{id}", note="...", outcome="success")`
```

**Variant 2 — Success + reject (5 agents: architect, auditor, builder, doc-writer, reviewer):**
```
### MCP Lifecycle
> `start_work("{id}")` → `edit_task("{id}", append_body="## {Section}\n...", timestamp=True)` → `end_work("{id}", note="...", outcome="success")`
> Reject: `end_work("{id}", note="...", outcome="reject", move_to="{target}")`
```

### 3c. Per-Agent Lifecycle Block Specification

| Agent | Channel B Section | Success target | Reject target | Block variant |
|-------|-------------------|---------------|---------------|---------------|
| architect | Architecture Review | → todo | → ideation | 2 |
| auditor | Audit | → archive | → backlog | 2 |
| builder | Builder Notes | → review | → todo or backlog | 2 |
| curator | Curation | success | — | 1 + conditional |
| doc-writer | Docs Gate | → done | → review | 2 |
| planner | Planning | success | — | 1 + conditional |
| researcher | Research | → backlog | — | 1 |
| reviewer | Review Evidence | → docs | → in-progress/todo/backlog | 2 |
| test-writer | Test-Writer Notes | → in-progress | — | 1 |

### 3d. Options Comparison

| Criterion | A: 10 agents (AC as-is) | B: 9 agents, exclude scribe | C: 8 agents, exclude scribe + planner |
|-----------|------------------------|----------------------------|--------------------------------------|
| Factual accuracy | Low — scribe block incorrect | **High** | Overly cautious — planner IS dispatched |
| AC change required | None | Minor (10 → 9 + rationale) | Larger revision |
| Test simplicity | 10 agents, same assertion | 9 agents, same assertion | 8 agents one way, planner different |
| Reject path coverage | Not in original AC | Add via variant 2 (challenger C1) | Same |
| Conditional handling | Not in original AC | Qualifier for curator + planner | N/A for planner |
| DRY risk | Scribe block contradicts skill | None | None |
| Confidence | .50 | **.80** | .68 |

### 3e. Skill Language Inconsistency

`w-task-decomposition` L15: "does NOT claim a task" but L92: "advance via `end_work` to release the claim." The planner is dispatched from the board (via orchestrator) and needs to claim. The skill's "does NOT claim" describes the task-creation intent, not the operational reality. Separate follow-up to fix.

## 4. Recommendation

**Option B: 9 agents get lifecycle blocks, exclude scribe** (confidence: .80)

Revised #575 AC should specify:
1. **9 agents** (architect, auditor, builder, curator, doc-writer, planner, researcher, reviewer, test-writer) — scribe excluded with rationale
2. **Two block variants:** 3-line success-only and 4-line success+reject per 3c table above
3. **Conditional qualifier** on planner and curator: "Lifecycle applies when dispatched with a task ID"
4. **Test assertion:** each of 9 agents contains `start_work` and `end_work` in body
5. **Compound tools** (start_work, end_work) documented as preferred pattern (already in h-mcp-kanban)

Challenge: proceed with reservations (confidence: .72). Key challenges accepted: C1 (reject paths needed), C3 (AC must say 9), C6 (conditional qualifier for planner/curator). C2 (planner skill language) deferred to follow-up.

## 5. Follow-up Tasks

1. **#594 itself** — revise #575 AC per this recommendation (this task advances to backlog)
2. **New task** — fix planner skill language in w-task-decomposition ("does NOT claim" vs `end_work`)
