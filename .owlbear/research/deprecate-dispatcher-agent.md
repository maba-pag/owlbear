# Deprecate Dispatcher Agent Definition

> **Owning task:** #623 — Deprecate dispatcher agent definition
> **Date:** 2026-04-05 **Status:** Complete

## 1. Context and Question

Task #623 (child of #619) requires marking the dispatcher agent (`share/agents/dispatcher.agent.md`) as deprecated and removing it from the orchestrator's subagent list. The dispatcher is `disable-model-invocation: true` — a pure function being replaced by the `pick_tasks` MCP tool (#621). #622 wires pick_tasks into the orchestrator workflow; #623 marks the agent file as deprecated; #629 cleans up cross-cutting references.

**Key questions:** (1) What deprecation pattern should the agent file follow? (2) What is the exact scope boundary between #623 and #629? (3) Are there unexpected references not covered by #622 or #629?

## 2. Sources Studied

| # | Source | Rel. | What taken |
|---|--------|:----:|------------|
| S1 | `share/skills/h-kanban-md/SKILL.md` | .95 | Workspace deprecation pattern: description prefix, body callout |
| S2 | `share/agents/dispatcher.agent.md` | .95 | Current agent definition: 93 lines, YAML frontmatter, persona, rules |
| S3 | `share/agents/orchestrator.agent.md` L1-20 | .95 | Dispatcher listed in `agents:` list at L10 |
| S4 | `.github/copilot-instructions.md` | .85 | Confirmed: zero dispatcher references |
| S5 | #629 AC (task body) | .90 | Cross-cutting cleanup scope: agent-common, r-pipeline-protocol, README, h-agent-structure |
| S6 | #622 AC (task body) | .90 | w-orchestration (13 refs) + w-dispatch-planning (archive) + orchestrator.agent.md body refs (9 refs) |
| S7 | Codebase grep: 38 refs across 8 files | .95 | Complete reference inventory |
| S8 | `.owlbear/research/migrate-dispatcher-to-pick-tasks.md` | .85 | Parent task research confirming migration rationale |

## 3. Analysis

### 3.1 Deprecation Pattern

| Aspect | h-kanban-md pattern (S1) | Alternative: YAML `deprecated: true` |
|--------|--------------------------|---------------------------------------|
| Description | `"(DEPRECATED): original — use X instead"` | Separate YAML key |
| Body | `> **Deprecated.** explanation` | No body convention |
| Precedent | 1 existing instance in workspace | 0 instances; not a standard VS Code agent frontmatter key |
| Discoverability | High — visible in skill/agent lists | Medium — requires frontmatter parsing |
| Risk | None | Unknown if VS Code/Copilot CLI recognizes the key |

**Recommendation (.92): Follow h-kanban-md pattern.** Only proven deprecation convention in this workspace. No `deprecated:` YAML key exists anywhere — introducing one without validation is speculative.

### 3.2 Reference Inventory and Scope Boundary

38 dispatcher references across 8 files. Responsibility mapping:

| File | Refs | Owner task | Rationale |
|------|:----:|:----------:|-----------|
| `share/agents/dispatcher.agent.md` | 3 | **#623** | Deprecation marking |
| `share/agents/orchestrator.agent.md` L10 (agents: list) | 1 | **#623** | Remove from subagent list |
| `share/agents/orchestrator.agent.md` (body: L31,55,81,101,114,118,129,142) | 8 | **#622** | Already in #622 AC |
| `share/skills/w-orchestration/SKILL.md` | 13 | **#622** | Already in #622 AC |
| `share/skills/w-dispatch-planning/SKILL.md` | 5 | **#622** | Archive callout in #622 AC |
| `share/instructions/agent-common.instructions.md` | 1 | **#629** | In #629 AC |
| `share/skills/r-pipeline-protocol/SKILL.md` | 2 | **#629** | In #629 AC |
| `share/agents/README.md` | 1 | **#629** | In #629 AC |
| `share/skills/h-agent-structure/SKILL.md` | 1 | **#629** | In #629 AC |
| `share/skills/w-task-decomposition/SKILL.md` L19 | 1 | **GAP** | "dispatcher-dispatched" — not in any task AC |
| `.github/copilot-instructions.md` | 0 | N/A | No references found |

**Gap found:** `w-task-decomposition/SKILL.md` L19 mentions "dispatcher-dispatched" — not covered by #622, #623, or #629 AC.

### 3.3 AC Item 4 Overlap

#623 AC: "No remaining references to dispatcher as a live subagent in any active agent/skill file."

This is unachievable by #623 alone — 27 references across 6 files are owned by #622 and #629, which run independently. Two interpretations:

| Interpretation | Implication | Recommendation |
|----------------|-------------|----------------|
| A. Literal: verify all refs removed | #623 must run AFTER #622 AND #629 | Adds #629 as dependency — breaks pipeline parallelism |
| B. Verify #623's own scope is clean | #623 handles agent file + orchestrator agents list | **Preferred** — matches subtask decomposition intent |

**Recommendation (.85): Narrow AC item 4** to "No remaining references to dispatcher in orchestrator `agents:` list" and add verification note that #629 handles cross-cutting cleanup.

## 4. Recommendation (.88 confidence)

Proceed with #623 using narrow scope:

1. **Deprecate dispatcher.agent.md** — follow h-kanban-md pattern (description prefix + body callout + explanation of pick_tasks replacement)
2. **Remove `dispatcher` from orchestrator.agent.md `agents:` list** (L10)
3. **copilot-instructions.md** — N/A, no references exist
4. **Narrow AC item 4** — verify dispatcher removed from orchestrator agents list; defer cross-cutting refs to #629
5. **Keep file** — do not delete, per AC

Challenge: T1 (autonomous) — executing pre-approved migration plan from #619. Deprecation was approved in #619's architecture review. No new decision needed.

Tier: **T1 — Autonomous.** Execution of approved subtask within existing migration plan.

## 5. Follow-up Tasks

| Action | Target | Rationale |
|--------|--------|-----------|
| Add w-task-decomposition L19 to #629 AC | #629 | Gap: "dispatcher-dispatched" ref not covered by any task |
| Narrow #623 AC item 4 | #623 | Avoid overlap with #629; unachievable without #629 completing first |
