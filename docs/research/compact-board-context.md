# Compact Board-State Context Injection for Agents

> **Owning task:** #744 — Evaluate compact board-state context injection for agents
> **Date:** 2026-03-13 **Status:** Complete

## 1. Context and Question

OwlBear agents currently lack situational awareness of the project board state.
The `ContextInjectionHook` runs `kanban-md context` at SESSION_START (~8,276 tokens)
and stores the result in event payload data, but this output is **not wired into
the agent system prompt**. Meanwhile, `KnowledgeQueryService` injects per-turn
semantic search results via `inner.run(instructions=...)`.

The question: how should we inject a compact board-state snapshot into agent
prompts, at what frequency, and through which injection point?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| Mission Control `generate-context.ts` | <https://github.com/MeisnerDan/mission-control/blob/main/mission-control/scripts/generate-context.ts> | .85 |
| MC README — Token-Optimized API | <https://github.com/MeisnerDan/mission-control> | .80 |
| PydanticAI — Instructions (runtime) | <https://ai.pydantic.dev/agents/#instructions> | .90 |
| Claude Code — Memory / CLAUDE.md | <https://code.claude.com/docs/en/memory> | .70 |
| OwlBear `KnowledgeQueryService` | `src/owlbear/memory/knowledge/query_service.py` | .95 |
| OwlBear `ContextInjectionHook` | `src/owlbear/core/context_hook.py` | .95 |
| OwlBear `ContextManager` | `src/owlbear/memory/context.py` | .90 |
| OwlBear `agent.turn()` | `src/owlbear/core/agent.py` | .95 |

## 3. Analysis

### 3.1 MC's generate-context.ts Approach

MC generates a static `ai-context.md` file (~650 tokens) via `pnpm gen:context`.
It reads all JSON data files and produces sections: Active Projects, Inbox,
Pending Decisions, Eisenhower Matrix, Kanban Pipeline, In-Progress Tasks
(with subtask progress + blocked indicators), Goals, Brain Dump, Agent Workload,
Quick Stats. This is a **batch-generated file**, not live data.

Pros: Rich summary, low token cost. Cons: Stale between generations, requires a
custom generator script, MC-specific sections (Eisenhower, Brain Dump, Goals)
are irrelevant to OwlBear.

### 3.2 kanban-md Output Comparison

| Command | Chars | ~Tokens | Content |
|---------|-------|---------|---------|
| `kanban-md context` | 33,104 | 8,276 | Full board + task bodies |
| `kanban-md list --compact` (all) | 8,994 | 2,249 | One-line per task, all statuses |
| `kanban-md list --compact` (active only) | ~880 | ~220 | Active tasks (in-progress, review, todo) |

Active-only compact output is **3x more efficient than MC's ~650 tokens** while
providing comparable situational awareness for OwlBear agents.

### 3.3 Injection Point Comparison

| Criterion | KnowledgeQueryService | ContextInjectionHook | ContextManager | New per-turn provider |
|-----------|----------------------|---------------------|----------------|----------------------|
| Mechanism | `run(instructions=)` | SESSION_START event | `Agent(instructions=)` | `run(instructions=)` |
| Timing | Per-turn | Session start | Agent init | Per-turn |
| Wired to prompt? | Yes | **No** (event data only) | Yes (static) | Yes |
| Fit for board state | Wrong concern (vector search) | Not wired to prompt | Stale at init-time | **Best fit** |

**KnowledgeQueryService is NOT the right injection point** because:
- It embeds prompts and does vector similarity search — board state is not
  semantically relevant to arbitrary queries
- Board state should **always** be included, not conditionally based on search relevance
- Mixing vector search results with static board data violates single responsibility

### 3.4 Architecture Options

| Option | Token cost | Freshness | Latency | Code needed | KISS |
|--------|-----------|-----------|---------|-------------|------|
| A: MC-style static file gen | ~650 | Stale | None (pre-gen) | ~100 LOC generator | Medium |
| B: Compact active in `turn()` | ~220 | Real-time | ~50ms subprocess | ~30 LOC | **High** |
| C: Cached compact (TTL 60s) | ~220 | Near-real-time | ~50ms first, 0 cached | ~50 LOC | High |
| D: Wire ContextInjectionHook | ~220 | Session-start | None at turn-time | ~20 LOC wiring | High |

## 4. Recommendation (.80 confidence)

**Option C — Cached compact board injection via a `BoardContextProvider`.**

A lightweight service that:
1. Runs `kanban-md list --compact --status in-progress --status review --status todo`
2. Caches the result with a configurable TTL (default 60s)
3. Returns ~220 tokens of board state
4. Gets concatenated with knowledge context in `turn()` before passing to
   PydanticAI's runtime `instructions=` parameter

**Why not MC's approach?** MC's generator is designed for a richer data model
(Eisenhower, Goals, Inbox, Brain Dump) that OwlBear doesn't have. Our `kanban-md`
CLI already provides adequate compact output. Building a custom generator would
violate YAGNI.

**Why not KnowledgeQueryService?** Semantic vector search and static board state
are fundamentally different concerns. Board state should always be injected
regardless of prompt content.

**Why cached?** Subprocess per turn adds ~50ms latency. Board state changes
rarely during a single agent session. A 60s TTL cache eliminates repeated
subprocess calls while keeping data near-real-time.

**Risk:** Subprocess dependency on `kanban-md.exe` binary. Mitigate with
graceful degradation (return empty string on failure, log warning).

## 5. Follow-up Tasks

- **#770** — Implement BoardContextProvider with TTL caching (important)
- **#771** — Wire BoardContextProvider into agent turn() instructions (important, depends on #770)
- **#772** — Fix ContextInjectionHook: wire kanban_summary to system prompt (nice-to-have)
