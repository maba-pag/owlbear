# Update Pipeline Agent Files with MCP Tool References

> **Owning task:** #575 — P2-04: Update pipeline agent files with MCP tool references alongside CLI
> **Date:** 2026-04-04 **Status:** Complete

## 1. Context and Question

Task #575 requires updating 11 pipeline agent `.agent.md` files with MCP tool alternatives alongside CLI examples. The v2 architecture refactor (commit 2d1e9ca) restructured agent files from CLI-heavy bodies to thin persona/rules/boundaries containers that reference workflow skills. This research determines whether #575's original scope is still valid and what implementation approach fits v2.

**Key question:** Should MCP tool references be added to agent bodies, or has the v2 skill-based architecture already satisfied this need?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `.github/agents/*.agent.md` (10 pipeline agents) | Codebase | .95 — current agent body content |
| 2 | `tests/test_mcp_tool_references_483.py` L146-150 | Codebase | .95 — agent body MCP checks explicitly removed |
| 3 | `tests/test_agent_port_v2.py` L80,98 | Codebase | .90 — kanban-planner missing, "writer"=doc-writer |
| 4 | `.github/skills/h-mcp-kanban/SKILL.md` | Codebase | .90 — MCP tool reference with lifecycle pattern |
| 5 | `.github/skills/r-pipeline-protocol/SKILL.md` | Codebase | .85 — pipeline conventions with MCP pointers |
| 6 | `.github/skills/w-research/SKILL.md` (and 9 other w-* skills) | Codebase | .85 — workflow skills contain MCP tool usage |
| 7 | `docs/research/mcp-tool-references-alongside-cli.md` | Research | .80 — original #483 research (v1 assumptions) |
| 8 | Task #572 body (archived) | Board | .80 — test scope decisions and reviewer evidence |
| 9 | Task #574 body (at todo) | Board | .75 — r-pipeline-protocol MCP additions planned |

## 3. Analysis

### 3a. Current State: Zero CLI Baseline

| Check | Result | Evidence |
|-------|--------|---------|
| `kanban-md` CLI commands in agent bodies | 0 matches | grep across all `.github/agents/*.agent.md` |
| MCP tool names in agent bodies | 0 matches | grep for start_work, end_work, edit_task etc. |
| MCP tools in frontmatter | 10/10 have `owlbear-kanban/*` | All pipeline agents |
| Workflow skill references in critical_rules | 10/10 have "Follow the `w-{skill}` skill" | All pipeline agents |

### 3b. Agent Name Discrepancy

| AC Name | Filesystem | Status |
|---------|-----------|--------|
| architect, auditor, builder, curator, planner, researcher, reviewer, scribe, test-writer | Exist at `.github/agents/` | OK |
| writer | `doc-writer.agent.md` | Alias confirmed by test_agent_port_v2.py L98 |
| kanban-planner | Does not exist | RED test at test_agent_port_v2.py L80 |

AC says 11 agents; 10 exist. `kanban-planner` is a planned future agent.

### 3c. Indirection Depth to MCP Syntax

An agent discovering how to claim a task currently follows:

| Hop | File | Content |
|-----|------|---------|
| 0 | Agent `.agent.md` critical_rules | "Follow the `w-{skill}` skill" + "Read `r-pipeline-protocol`" |
| 1 | `r-pipeline-protocol` L29 | "see the `h-mcp-kanban` skill (`start_work` tool)" |
| 2 | `h-mcp-kanban` | Full `start_work()` / `end_work()` syntax |

3-hop indirection. Each agent's lifecycle is slightly different (unique Channel B section names, outcome values, verdict patterns) but this specificity is invisible until hop 2.

### 3d. Options Comparison

| Criterion | A: Close as obsolete | B: Re-scope — add per-agent MCP lifecycle | C: Implement as-written |
|-----------|---------------------|------------------------------------------|------------------------|
| v2 architecture alignment | High — thin agents, rich skills | High — small additive, no restructure | Low — adds bulk to thin agents |
| DRY compliance | Best — no duplication | Good — context-specific (unique section names/outcomes per agent) | Poor — duplicates skill content |
| Indirection depth | 3 hops (unchanged) | 0 hops for core lifecycle | 0 hops for all patterns |
| Maintenance cost | Zero | Low (~3 lines per agent, 10 agents) | High (~15-20 lines per agent) |
| AC premise validity | AC premise wrong for v2 (no CLI to annotate) | AC re-scoped to v2 reality | AC names wrong (kanban-planner missing) |
| Parent #483 impact | AC line unsatisfied; parent needs revision | Satisfies spirit of AC | Satisfies literal AC (after fixes) |
| Test infrastructure | Aligns with removed checks | Needs new lightweight test | Conflicts with removed checks |
| Risk | Long-term: new agents miss MCP lifecycle | Low | High maintenance burden |
| Confidence | .55 | **.80** | .30 |

### 3e. #572 Test Removal Assessment

The removal of agent body MCP checks (test_mcp_tool_references_483.py L146-150) was a builder-level decision during v2 migration. It was accepted by the review chain (.96 confidence) but no formal DR was filed for this scope change. This makes the removal accepted practice, not settled architecture. Re-adding lightweight checks under a re-scoped #575 is valid.

## 4. Recommendation

**Option B: Re-scope #575 to add per-agent MCP lifecycle examples** (confidence: .80)

Each pipeline agent gets a 3-line MCP lifecycle block in `<output_format>` showing the agent-specific lifecycle:

```markdown
### MCP Lifecycle
> `start_work("{id}")` → `edit_task("{id}", append_body="## {Section} Notes\n...")` → `end_work("{id}", note="...", outcome="success")`
```

Where `{Section}` is the agent's unique Channel B heading (e.g., "Builder", "Review Evidence", "Research").

**Why B over A:**
- Short-circuits 3-hop indirection for core lifecycle (challenger C4 accepted)
- Context-specific per agent (not pure DRY violation — unique section names, outcomes)
- Preserves v2 thin-agent architecture (3 lines, not 15-20)
- Satisfies parent #483 AC spirit without requiring parent revision

**Why B over C:**
- AC premise (CLI examples in agent bodies) doesn't hold in v2
- kanban-planner doesn't exist yet; "writer" needs AC fix to "doc-writer"
- Full implementation would conflict with v2 architecture

Challenge: reconsider (confidence in original close recommendation: .45). Key challenges accepted: C1 (test removal was builder decision, not architecture), C3-C4 (zero CLI ≠ zero MCP needed; indirection depth is real). Revised from Option A (.55) to Option B (.80).

## 5. Follow-up Tasks

1. **Re-scope #575 AC** — Rewrite AC for v2: 10 agents (not 11, exclude kanban-planner until it exists), "doc-writer" not "writer", add per-agent MCP lifecycle block to output_format, lightweight test assertion.
2. **Note on #574 dependency** — #574 at `todo` adds MCP callouts to r-pipeline-protocol. #575 re-scoped work is independent of #574 (lifecycle blocks are agent-specific, not protocol-level). Dependency can be relaxed.
