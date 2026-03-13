# OpenAI Symphony — Multi-Agent Orchestration Research

> **Owning task:** #584 — Research: openai/symphony
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

OwlBear needs patterns for autonomous task execution: polling a task board, dispatching agents to isolated workspaces, managing concurrency, retries, and reconciliation. Symphony is OpenAI's spec + reference implementation for exactly this — an always-on daemon that reads issues from a tracker and dispatches coding agents autonomously.

**Key question:** Which Symphony patterns are adoptable in OwlBear (Python 3.12, PydanticAI, kanban-md) and what architectural gaps does it reveal?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| openai/symphony (SPEC.md + Elixir impl) | <https://github.com/openai/symphony> | 1.0 — primary subject |
| Harness Engineering blog post | <https://openai.com/index/harness-engineering/> | 0.9 — design philosophy |
| Codex ExecPlans cookbook | <https://developers.openai.com/cookbook/articles/codex_exec_plans> | 0.8 — task planning pattern |

## 3. Analysis

### 3.1 Architectural Comparison

| Aspect | Symphony | OwlBear | Gap |
|--------|----------|---------|-----|
| Task source | Linear (issue tracker API) | kanban-md (file-based) | OwlBear has no poll loop for auto-dispatch |
| Dispatch | Poll → filter → sort → dispatch | User-initiated via CLI/Slack | No autonomous dispatch |
| Workspace isolation | Per-issue directory under `workspace.root` | Single shared workspace | Critical gap — no isolation |
| Concurrency | `max_concurrent_agents` + per-state limits | Sequential (one agent at a time) | No parallelism |
| Agent protocol | Codex app-server (JSON-RPC over stdio) | PydanticAI agent.run() | Already adequate for OwlBear |
| Retry/backoff | Exponential backoff with continuation retries | `tenacity` on HTTP; no task-level retry | Gap — need task-level retry |
| Reconciliation | Per-tick state refresh, stall detection, terminal cleanup | None | Gap — no reconciliation |
| Workflow config | `WORKFLOW.md` (YAML front matter + prompt) | `copilot-instructions.md` + agent files | Partial overlap |
| Hooks | `after_create`, `before_run`, `after_run`, `before_remove` | `HookRegistry` with event system | OwlBear hooks are richer |
| Observability | Structured logs + optional HTTP dashboard + JSON API | `ObservabilityHook` + `EventStore` | OwlBear has basics |

### 3.2 Key Patterns Worth Adopting

| Pattern | Description | Confidence | Effort |
|---------|-------------|------------|--------|
| **Poll-dispatch loop** | Periodic tick: reconcile → validate → fetch tasks → sort → dispatch | .85 | Medium |
| **Workspace isolation** | Per-task directory with lifecycle hooks | .80 | Medium |
| **Continuation turns** | After normal completion, re-check if task still active, send continuation prompt | .75 | Low |
| **Exponential backoff retry** | Task-level: `min(10000 * 2^(attempt-1), max_backoff_ms)` | .90 | Low |
| **Reconciliation** | Per-tick: stall detection + state refresh for running tasks | .80 | Medium |
| **WORKFLOW.md / ExecPlan** | Self-contained task prompt with template variables | .70 | Low |
| **`linear_graphql` tool pattern** | Client-side tool injected into agent session for tracker writes | .65 | N/A (kanban-md) |

### 3.3 Patterns to Skip (YAGNI)

| Pattern | Reason |
|---------|--------|
| Linear integration | OwlBear uses kanban-md, not Linear |
| HTTP dashboard / REST API | Premature for OwlBear's current stage |
| Codex app-server protocol | OwlBear uses PydanticAI directly, not app-server subprocess |
| Per-state concurrency limits | Over-engineering for single-workspace OwlBear |

### 3.4 Research Checklist

1. **Theoretical validity** — Sound. Symphony solves the exact problem OwlBear will face: automating task pickup, dispatch, and completion from a board. The poll → reconcile → dispatch pattern is proven in production at OpenAI (1,500+ PRs from ~3 engineers).
2. **Prior art** — Symphony (OpenAI), Harness Engineering (OpenAI blog), Codex ExecPlans (OpenAI cookbook). All 3 sources validate the daemon-dispatch model.
3. **Technical feasibility** — Python 3.12 asyncio can implement the poll loop (`asyncio.sleep` + task groups). PydanticAI agents replace Codex app-server. kanban-md CLI replaces Linear API. No blockers.
4. **Architecture fit** — OwlBear already has `run_daemon()` in `daemon.py` (receive → turn → send loop), `HookRegistry`, `BootstrapResult`. The poll-dispatch pattern extends the existing daemon loop. Workspace isolation is additive.
5. **Implementation approach** — Extend `run_daemon()` with a poll tick. Add `WorkspaceManager` for per-task directories. Add task-level retry with backoff. Add reconciliation checks.

## 4. Recommendation (.85 confidence)

Adopt Symphony's **poll-dispatch-reconcile** pattern as OwlBear's autonomous execution mode. The core pattern is:

1. **Poll tick** — Read kanban board for tasks in `todo` status, sort by priority
2. **Dispatch** — Claim task (move to `in-progress`), create workspace, build prompt, run agent
3. **Reconcile** — After each tick, check running tasks' board status, detect stalls
4. **Retry** — On failure, exponential backoff retry; on success, continuation check

**Do NOT adopt** workspace isolation yet — OwlBear works in a single repo. Instead, adopt the dispatch loop and reconciliation patterns first.

**Risk:** The kanban-md CLI is file-based and lacks an API — polling means shelling out to `kanban-md list`. Mitigation: `KanbanToolset` already wraps this; acceptable overhead.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement poll-dispatch loop in daemon" --priority needed --tags "phase-9,scope:core,agent" --body "Extend run_daemon() with a configurable poll tick that reads todo tasks from kanban-md, sorts by priority, and dispatches to the builder agent pipeline.\n\nSee docs/research/symphony.md S3.2\n\nAC:\n- [ ] Poll interval configurable via settings (default 30s)\n- [ ] Fetches todo tasks via KanbanToolset\n- [ ] Sorts by priority (critical > needed > important > nice-to-have > someday)\n- [ ] Dispatches up to max_concurrent_agents tasks per tick\n- [ ] Moves dispatched tasks to in-progress\n- [ ] Skips blocked tasks"

kanban\kanban-md.exe create "Add task-level retry with exponential backoff" --priority important --tags "phase-9,scope:core,agent" --body "When an agent run fails on a kanban task, schedule retry with exponential backoff: delay = min(10000 * 2^(attempt-1), max_retry_backoff_ms).\n\nSee docs/research/symphony.md S3.2\n\nAC:\n- [ ] RetryEntry model with attempt, due_at, error fields\n- [ ] Backoff formula matches Symphony spec\n- [ ] Max 5 retry attempts before marking task blocked\n- [ ] Continuation retry (1s delay) after successful completion if task still active"

kanban\kanban-md.exe create "Add reconciliation to daemon poll loop" --priority important --tags "phase-9,scope:core,agent" --body "Per-tick reconciliation: check running tasks' kanban status, detect stalls, clean up terminal tasks.\n\nSee docs/research/symphony.md S3.2\n\nAC:\n- [ ] Stall detection: if no agent activity for stall_timeout (default 5min), kill and retry\n- [ ] State refresh: re-read kanban status for running tasks each tick\n- [ ] Terminal cleanup: if task moved to done externally, stop agent\n- [ ] Reconcile runs before dispatch each tick"

kanban\kanban-md.exe create "Research ExecPlan pattern for OwlBear task prompts" --priority nice-to-have --tags "research,scope:agent" --body "Evaluate OpenAI's ExecPlan (PLANS.md) pattern for structuring OwlBear task prompts. Self-contained living documents with Progress, Decision Log, Surprises sections.\n\nSee docs/research/symphony.md S3.2 and https://developers.openai.com/cookbook/articles/codex_exec_plans\n\nAC:\n- [ ] Research checklist completed\n- [ ] Decision on whether to adopt ExecPlan format for kanban task bodies"
```
