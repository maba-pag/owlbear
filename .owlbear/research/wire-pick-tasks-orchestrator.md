# Wire pick_tasks into Orchestrator Workflow

> **Owning task:** #622 — Wire pick_tasks into orchestrator workflow
> **Date:** 2026-04-05 **Status:** Complete

## 1. Context and Question

Task #622 replaces the dispatcher subagent with a direct `pick_tasks` MCP tool call in the orchestrator. The dispatcher is a fully deterministic agent (`disable-model-invocation: true`) that reads the board, applies gates, sorts, and maps status→agent. The `pick_tasks` tool (defined in #619, implemented in #621) absorbs the board-read, gate, and sort logic into a single MCP call returning `{"dispatch": [{"task_id": int, "status": str}]}`.

**Key question:** What responsibilities must move from the dispatcher to the orchestrator, and what design gaps exist in the current #619/#621 AC that #622 must account for?

## 2. Sources Studied

| # | Source | Relevance | What |
|---|--------|-----------|------|
| 1 | `share/skills/w-orchestration/SKILL.md` | 1.0 | Current orchestrator loop: Step 1 dispatches dispatcher |
| 2 | `share/skills/w-dispatch-planning/SKILL.md` | 1.0 | Current dispatcher workflow: dispatch mapping, gates, stale detection |
| 3 | `share/agents/orchestrator.agent.md` | 1.0 | Orchestrator agent config: subagent table, tools, persona |
| 4 | `share/agents/dispatcher.agent.md` | 1.0 | Dispatcher agent config: zero-invocation, JSON-only output |
| 5 | `serve/orchestrator/src/owlbear/planner/selector.py` | 1.0 | STATUS_AGENT_MAP, DECOMP routing, sort logic (Python impl) |
| 6 | `serve/orchestrator/src/owlbear/planner/gates.py` | .90 | Gate predicates: atomicity, TDD, clarity |
| 7 | #619 task body (architecture decision) | 1.0 | pick_tasks tool signature and design philosophy |
| 8 | #621 task body (implementation AC) | 1.0 | pick_tasks contract: return format, gate migration |
| 9 | `share/instructions/agent-common.instructions.md` | .80 | Per-agent section mapping (removes dispatcher row) |

## 3. Analysis

### 3.1 Responsibility Migration Matrix

| Responsibility | Current owner | After #622 | Migration complexity |
|----------------|--------------|------------|---------------------|
| Board read + gate + sort | Dispatcher (via pick_tasks after #621) | pick_tasks MCP tool | None — already in tool |
| Status → agent mapping | Dispatcher (selector.py) | Orchestrator w-orchestration | Low — copy table |
| Crash failure exclusion | Dispatcher (selector.py) | Orchestrator loop | Low — set-difference filter |
| DECOMP → planner routing | Dispatcher (selector.py) | Orchestrator post-filter | Medium — see §3.2 |
| Scope/tag filtering | Dispatcher (list_tasks tag param) | Orchestrator via pick_tasks param | Medium — see §3.3 |
| Gate warnings | Dispatcher output | Dropped | Low — see §3.4 |
| Stale detection + retry_hint | Dispatcher Recipe 2 | Orchestrator state tracking | Medium — see §3.5 |
| Pending DR counting | Dispatcher Recipe 0 | Dropped (scribe handles) | None |

### 3.2 DECOMP Routing (gap in #619/#621 AC)

pick_tasks returns `{task_id, status}` — no body. The orchestrator can't detect `"Needs decomposition:"` tasks. Only ~3 tasks on the board currently use this marker, set by architects on backlog tasks.

| Option | Pros | Cons |
|--------|------|------|
| A. Add `needs_decomp` to pick_tasks output | Single call, no extra reads | Changes #621 AC; requires body read in tool |
| **B. Orchestrator show_task post-filter** | No #621 AC change; bounded | 0-3 extra MCP calls per cycle |
| C. Ignore; let agent discover | Zero overhead | Wasted agent dispatch on wrong agent |

**Recommendation (revised after challenge):** Option B. After receiving pick_tasks result, orchestrator calls `show_task` for tasks at `backlog` status (where DECOMP is set by architects). If body contains `"Needs decomposition:"`, remap agent to `planner`. Cost: 0-3 additional calls per cycle, same pattern as stale-task reads.

### 3.3 Scope Filtering (gap in #619/#621 AC)

pick_tasks is "zero-config" per #619, but the orchestrator needs tag-based scope filtering (e.g., user says "Orchestrate: phase-2"). Without filtering, pick_tasks returns all eligible tasks.

| Option | Pros | Cons |
|--------|------|------|
| A. Add `scope: str` param | Full scope semantics | Leaks orchestrator concepts into tool |
| **B. Add `tag: str` param** | Minimal passthrough to `_run_kanban --tag` | Narrows "zero-config" slightly |
| C. Post-filter via show_task | No tool change | 25 show_task calls to check tags — expensive |

**Recommendation (revised after challenge):** Option B. Add `tag: str | None = None` param to pick_tasks, passed through to `_run_kanban` as `--tag {value}`. This is a CLI passthrough, not orchestrator logic in the tool. Default `None` preserves zero-config semantics. Requires updating #621 AC (T2 advisory — see §5).

### 3.4 Gate Warnings

Currently the dispatcher produces `gate_warnings` and the orchestrator tracks `gate_warned` counts. With pick_tasks, gate failures are silent — tasks don't appear in results.

**Recommendation:** Drop gate_warnings. Stale detection covers tasks that aren't progressing. **Caveat:** tasks that perpetually fail gates (e.g., title contains "and") are a blind spot — they're never dispatched, so stale detection doesn't catch them. Accepted risk; requires periodic manual board review.

### 3.5 Stale Detection and First-Stale State

The dispatcher's first-stale detection compares current statuses against previous dispatch. This requires the orchestrator to track `last_dispatched: dict[int, str]` (task_id → status from previous cycle). This is new persistent state in the orchestrator, bounded to max 20 entries (DISPATCH_CAP).

The orchestrator already tracks `stale_retried` and `gate_warned`. Adding `last_dispatched` is the same pattern. For retry_hint, call `show_task` only for detected stale tasks (1-2 per cycle).

## 4. Recommendation (confidence: .82)

Wire pick_tasks into w-orchestration with these changes:

1. **w-orchestration Step 1** — replace `runSubagent("dispatcher", ...)` with `pick_tasks(limit=25, tag={scope})`, then map status→agent locally, filter crash_failures, and check DECOMP via show_task for backlog tasks.
2. **Add status→agent mapping table** and **DECOMP routing logic** to w-orchestration.
3. **Add `last_dispatched` state** for first-stale detection; bound to 20 entries.
4. **Remove dispatcher** from orchestrator's subagent table and agents list.
5. **Archive w-dispatch-planning** with header marking it reference-only.
6. **Drop gate_warnings** and pending DR counting (scribe covers DRs).
7. **Update #621 AC** to add `tag: str | None = None` parameter.

Challenge: RECONSIDER — confidence in original: .75 → revised to .82
Challenger blocked items 3 (DECOMP via field) and 4 (scope param semantics). Accepted both counter-proposals: DECOMP via show_task post-filter, scope via `tag` passthrough.

## 5. Follow-up Tasks

- **T2 advisory:** Update #621 AC to add `tag` parameter (modifies "zero-config" design)
- **T1:** Update w-orchestration skill with pick_tasks call, mapping table, DECOMP, stale state
- **T1:** Update orchestrator.agent.md — remove dispatcher from agents/subagents
- **T1:** Archive w-dispatch-planning skill with header update
- **T1:** Update r-pipeline-protocol dispatcher references
- **T1:** Update agent-common.instructions.md — remove dispatcher row
