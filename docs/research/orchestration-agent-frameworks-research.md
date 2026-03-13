# Orchestration & Agent Frameworks — Epic Synthesis

> **Owning task:** #580 — Research: Orchestration & Agent Frameworks
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

OwlBear is a PydanticAI-based daemon with 8 agent roles dispatched through a kanban pipeline. This epic synthesizes findings from 6 child research tasks (#584–#589) and 3 prior docs to answer: what orchestration patterns should OwlBear adopt to improve multi-agent delegation, autonomous task execution, and quality enforcement?

## 2. Sources Studied

| Source | Type | Relevance | Child Task |
|--------|------|-----------|------------|
| openai/symphony | Elixir daemon, poll-dispatch-reconcile | .90 | #584 |
| ComposioHQ/agent-orchestrator | TS process orchestrator, reaction engine | .75 | #585 |
| harshkedia177/axon | Code intelligence, MCP hints | .70 | #586 |
| Ibrahim-3d/conductor-orchestrator-superpowers | Prompt framework, retrospective learning | .80 | #587 |
| quoroom-ai/room | Swarm intelligence, WIP continuity | .80 | #588 |
| nWave-ai/nWave | Wave pipeline, rigor profiles, DES hooks | .85 | #589 |
| PydanticAI multi-agent docs | Tool-based delegation, graphs, deep agents | .95 | (prior) |
| AutoGen SelectorGroupChat | LLM-based speaker selection | .70 | (prior) |
| CrewAI Crews | Sequential/hierarchical process, memory | .75 | (prior) |
| OwlBear agent-framework-research.md | Definition, registry, delegation (#128-130) | 1.0 | (prior) |
| OwlBear agent-patterns-research.md | OpenClaw, Nanobot, Disler patterns (#22) | .95 | (prior) |

## 3. Cross-Cutting Analysis

### 3.1 Orchestration Paradigms

| Paradigm | Examples | How It Works | OwlBear Fit |
|----------|----------|--------------|-------------|
| **Tool-based delegation** | PydanticAI, OwlBear (current) | Outer agent calls inner via tool function | **Current** — works, synchronous |
| **Poll-dispatch-reconcile** | Symphony | Daemon polls board, dispatches agents, reconciles state per tick | **High** — needed for autonomous mode |
| **LLM-selected routing** | AutoGen SelectorGroupChat | Model picks next speaker from candidate list | Medium — adds token cost per routing decision |
| **Sequential pipeline** | CrewAI sequential, OwlBear kanban | Tasks execute in fixed order through stages | **Current** — kanban statuses |
| **Hierarchical manager** | CrewAI hierarchical | Manager LLM delegates and validates | Low — OwlBear orchestrator already does this |
| **Swarm/queen-worker** | Quoroom Room | Queen delegates, workers execute autonomously | Medium — interesting for parallel work |
| **Graph FSM** | PydanticAI pydantic-graph (beta) | Typed nodes/edges with state machine | YAGNI — premature for OwlBear |

**Recommendation (.85):** OwlBear should add **poll-dispatch-reconcile** (Symphony pattern) as its autonomous execution mode, layered on top of the existing tool-based delegation. LLM-selected routing and graph FSM are YAGNI.

### 3.2 Highest-Value Patterns Across All Repos

Patterns ranked by cross-repo validation (appeared in 2+ sources) and OwlBear fit:

| Pattern | Sources | Confidence | Effort | Priority |
|---------|---------|------------|--------|----------|
| Poll-dispatch-reconcile loop | Symphony, Quoroom | .85 | Medium | needed |
| WIP continuity across cycles | Quoroom, Symphony (continuation turns) | .80 | Low | needed |
| Rigor profiles (quality vs speed) | nWave, Conductor (eval cycles) | .85 | Low | important |
| Retrospective learning hook | Conductor, Quoroom (session summaries) | .80 | Medium | important |
| Stuck/stale detection | Quoroom, nWave, Symphony (reconciliation) | .80 | Low | important |
| Reaction engine (event→action routing) | agent-orchestrator, Symphony | .75 | Medium | nice-to-have |
| Control-plane tool partitioning | Quoroom, nWave (DES) | .70 | Low | nice-to-have |
| Anti-rationalization tables | Conductor, nWave (enforcement) | .70 | Low | nice-to-have |
| Priority-routed notifications | agent-orchestrator | .65 | Low | nice-to-have |
| MCP next-step hints | Axon | .60 | Low | someday |

### 3.3 OwlBear Architecture Gaps

| Gap | Current State | Target State | Enabling Pattern |
|-----|---------------|--------------|------------------|
| No autonomous task pickup | User-initiated via CLI/Slack | Daemon polls kanban, auto-dispatches | Poll-dispatch-reconcile |
| No multi-cycle continuity | Each turn is independent | WIP injected as resume context | WIP continuity store |
| No quality-vs-speed dial | Same rigor for all tasks | Configurable profiles per task type | Rigor profiles |
| No post-task learning | ErrorJournal (append-only) | Structured retrospective → knowledge graph | Retrospective hook |
| No stale task detection | Stuck tasks sit unnoticed | Periodic scan, auto-block or alert | Stale detection scan |
| No formal retry cap at task level | Reviewer can reject indefinitely | Exponential backoff, max retries | Task-level retry |

### 3.4 What NOT to Adopt (KISS/YAGNI)

| Pattern | Why Skip | Source |
|---------|----------|--------|
| Git worktree isolation | Single-repo workflow; kanban boundaries suffice | agent-orchestrator |
| Board of Directors (multi-persona deliberation) | Token-expensive for daemon scale | Conductor |
| Quorum governance (agent self-governance) | OwlBear uses human approval gates | Quoroom |
| Session compression via LLM | PydanticAI history processors suffice | Quoroom |
| Graph FSM orchestration | Premature complexity; tool delegation works | PydanticAI beta |
| External agent adapters (Claude Code, Codex) | Single provider (Copilot) via PydanticAI | agent-orchestrator |
| File-based message bus | Native Python objects + hooks | Conductor |

### 3.5 PydanticAI Alignment

OwlBear's existing architecture aligns well with PydanticAI's documented patterns:

- **Agent delegation** via tool function — already implemented in `DelegationToolset`
- **Deps passing** with `ctx.deps` and `ctx.usage` — already implemented in `OwlBearDeps`
- **Deep Agents** pattern (planning, file ops, delegation, sandboxing) — partially implemented
- **Durable execution** — not yet needed but available via Temporal/DBOS/Prefect if needed
- **History processors** — available for context management without custom compaction

The poll-dispatch-reconcile pattern does NOT conflict with PydanticAI — it's the application-level loop that calls `agent.run()`, which is exactly PydanticAI's "programmatic hand-off" pattern.

## 4. Recommendation (.85 confidence)

Adopt patterns in three tiers:

**Tier 1 — Core autonomous mode (needed):**

1. Poll-dispatch-reconcile daemon loop (Symphony)
2. Task-level retry with exponential backoff (Symphony)
3. WIP continuity store (Quoroom)

**Tier 2 — Quality enforcement (important):**

4. Rigor profiles system (nWave)
5. Retrospective learning hook (Conductor)
6. Stale execution detection (nWave + Quoroom)

**Tier 3 — Polish (nice-to-have):**

7. Reaction engine for event→action routing (agent-orchestrator)
8. Anti-rationalization tables for builder/writer/auditor (Conductor)
9. Control-plane tool partitioning for orchestrator (Quoroom)

**Risk:** Over-engineering the autonomous loop before core agent quality is proven. Mitigation: implement Tier 1 first, validate with real tasks, then add Tier 2.

## 5. Follow-up Tasks

Child tasks #584–#589 already proposed ~20 granular follow-up tasks in their respective research docs. Below are the **cross-cutting epic-level tasks** that consolidate and prioritize:

```powershell
kanban\kanban-md.exe create "Implement poll-dispatch-reconcile daemon loop" --priority needed --status ideation --tags "scope:core,agent" --body "Extend run_daemon() with configurable poll tick: reconcile running tasks → fetch todo tasks from kanban → sort by priority → dispatch to builder pipeline. See docs/orchestration-agent-frameworks-research.md §3.1 and docs/symphony-research.md §3.2\n\nAC:\n- [ ] Poll interval configurable (default 30s)\n- [ ] Fetches todo tasks, sorts by priority\n- [ ] Dispatches up to max_concurrent tasks per tick\n- [ ] Moves dispatched tasks to in-progress\n- [ ] Reconcile checks running tasks each tick\n- [ ] Stall detection with configurable timeout"

kanban\kanban-md.exe create "WIP continuity store for multi-cycle agent execution" --priority needed --status ideation --tags "scope:core,agent" --body "Implement WipStore (JSONL-backed, keyed by agent+task) that persists what an agent accomplished per cycle. Inject WIP as 'CONTINUE FORWARD' directive at prompt-build time. See docs/orchestration-agent-frameworks-research.md §3.2 and docs/quoroom-room-research.md §3.3\n\nAC:\n- [ ] WipStore with save(agent, task_id, summary) and load(agent, task_id)\n- [ ] Injected into agent prompt when resuming a task\n- [ ] Cleaned up when task completes\n- [ ] JSONL storage under .owlbear/wip/"

kanban\kanban-md.exe create "Rigor profiles: configurable quality-vs-speed per task type" --priority important --status ideation --tags "scope:core,config" --body "Add rigor profile system to owlbear.toml with presets (lean/standard/thorough). Profile controls: review enabled, TDD depth, turn budget. Read at bootstrap, passed into agent deps. See docs/orchestration-agent-frameworks-research.md §3.2 and docs/nwave-research.md §3.3 P1\n\nAC:\n- [ ] 3 preset profiles in config (lean/standard/thorough)\n- [ ] Per-task override via kanban tag (rigor:lean, rigor:thorough)\n- [ ] Profile affects turn budget and review gate\n- [ ] Default profile: standard"

kanban\kanban-md.exe create "Retrospective learning hook on task completion" --priority important --status ideation --tags "scope:agent,scope:knowledge" --body "PydanticAI agent triggered on ON_TASK_DONE hook that extracts: what worked, what failed, error patterns, reusable patterns. Ingests structured RetroFindings into knowledge graph. Only fires for tasks with rejections or fix cycles. See docs/orchestration-agent-frameworks-research.md §3.2 and docs/conductor-orchestrator-superpowers-research.md §4a\n\nAC:\n- [ ] Hook fires on task completion for non-trivial tasks\n- [ ] Structured output: RetroFindings model\n- [ ] Findings ingested into knowledge graph\n- [ ] Trivial tasks skip retrospective"

kanban\kanban-md.exe create "Stale execution detector for daemon loop" --priority important --status ideation --tags "scope:core,agent" --body "Periodic scan of in-progress tasks. If no agent activity for stale_timeout (default 5min), inject warning or auto-block. See docs/orchestration-agent-frameworks-research.md §3.2, docs/nwave-research.md §3.3 P4, docs/quoroom-room-research.md §3.4\n\nAC:\n- [ ] Scan runs each daemon tick\n- [ ] Configurable stale threshold (default 5min)\n- [ ] Stuck tasks get blocked with reason\n- [ ] Alert sent via active channel"

kanban\kanban-md.exe create "Task-level retry with exponential backoff" --priority important --status ideation --tags "scope:core,agent" --body "When agent run fails on a task, schedule retry: delay = min(10s * 2^(attempt-1), max_backoff). Max 5 attempts before blocking task. See docs/orchestration-agent-frameworks-research.md §3.2 and docs/symphony-research.md §3.2\n\nAC:\n- [ ] RetryEntry model with attempt count, next_due, error\n- [ ] Exponential backoff formula\n- [ ] Max 5 retries before auto-block\n- [ ] Continuation retry (1s) after success if task still active"
```
