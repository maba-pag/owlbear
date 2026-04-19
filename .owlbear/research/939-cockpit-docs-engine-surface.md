# Cockpit Docs — Engine Surface + Future-Surface Contract + Walkthrough

> **Owning task:** #939 — P3-03: Docs — engine surface + future-surface contract + hello-world walkthrough
> **Date:** 2026-04-19 **Status:** Complete

## 1. Context and Question

Task #939 requires documenting: (1) the cockpit's engine surface allowlist, (2) the shell-to-surface extensibility contract, (3) a hello-world second-surface walkthrough, (4) Work Sessions model, and (5) the `actor: "cockpit"` audit convention. All information exists in implemented code — this is a synthesis task, not a design task.

## 2. Sources Studied

| Source | Location | Relevance | What Taken |
|--------|----------|-----------|------------|
| Cockpit adapter | `serve/cockpit/src/owlbear_cockpit/adapter.py` | 1.0 | 5 read-only engine methods (the allowlist) |
| Mutation routes | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` | 1.0 | 3 direct engine calls (move, edit, release) |
| Read routes | `serve/cockpit/src/owlbear_cockpit/routes/read.py` | 0.9 | Route patterns, cache usage, filter logic |
| Shell component | `serve/cockpit/web/src/Shell.tsx` | 1.0 | Layout grid, nav-rail, route registration |
| App entry | `serve/cockpit/web/src/App.tsx` | 0.8 | Provider/router wrapping pattern |
| Shell CSS | `serve/cockpit/web/src/Shell.css` | 0.8 | Grid-area layout contract |
| main.py (launch) | `serve/cockpit/src/owlbear_cockpit/main.py` | 1.0 | SPA catch-all, engine init with `agent_name="cockpit"` |
| KanbanEngine sessions | `serve/kanban/src/owlbear_kanban/engine.py:1030-1100` | 1.0 | WorkSession derivation, filter states, timeout |
| Launch research | `.owlbear/research/937-cockpit-launch-command.md` | 0.7 | Static serving rationale, route ordering |

## 3. Analysis

### 3.1 Engine Surface Allowlist

The adapter (`adapter.py`) exposes exactly 5 read-only engine methods. Mutations bypass the adapter and call the engine directly from route handlers.

| Method | Via Adapter | Why Included/Excluded |
|--------|-------------|----------------------|
| `list_tasks()` | ✓ | Board columns need task summaries |
| `show_task()` | ✓ | Detail tab needs full task data |
| `board_config()` | ✓ | Statuses + priorities for column rendering |
| `valid_transitions()` | ✓ | Validates drag-drop targets |
| `list_sessions()` | ✓ | Activity tab data |
| `move_task()` | ✗ (direct) | Mutation — called in route handler with validation |
| `edit_task()` | ✗ (direct) | Mutation — complex kwargs construction |
| `release_task()` | ✗ (direct) | Mutation — simple, needs pre-check |
| `create_task()` | excluded | UI has no create flow (pipeline creates tasks) |
| `sweep()` | excluded | Background maintenance, not UI-triggered |
| `start_work()/end_work()` | excluded | Agent lifecycle, not user-initiated |

### 3.2 Shell-to-Surface Contract

Adding a surface requires 3 touchpoints:

1. **Route** — Add `<Route path="/foo" element={<FooSurface />} />` in `Shell.tsx`
2. **Nav-rail button** — Add `<button data-surface="foo">` in the nav-rail `<nav>`
3. **Component** — Create `src/FooSurface.tsx` with the surface content

No shell layout changes required — grid areas (`workspace`, `sidecar`) are surface-agnostic.

### 3.3 Work Sessions Model

| State | Derivation | Filter Match |
|-------|-----------|--------------|
| `running` | Open claim, last activity within timeout | `active` |
| `stuck` | Open claim, last activity exceeds timeout | `active` |
| `completed-pass` | end_work detail starts with `"success:"` | `all` |
| `completed-rejected` | end_work detail starts with `"reject:"` | `failed-or-rejected` |
| `completed-fail` | Any other end_work outcome | `failed-or-rejected` |
| `released` | release/sweep-release action | `released` |

Filter vocabulary: `active`, `all`, `failed-or-rejected`, `released`.

### 3.4 Audit Trail

`KanbanEngine(kanban_dir, agent_name="cockpit")` — all mutations write `actor: "cockpit"` to `activity.jsonl`. Convention distinguishes UI-initiated changes from agent-initiated ones.

## 4. Recommendation

**Confidence: 0.92** — Straightforward documentation synthesis. All information is verified from source code.

The README should follow a progressive-disclosure structure: quick-start (launch), then architecture (engine surface, contract), then walkthrough (hello-world), then reference (sessions, audit). This matches how a developer would approach the docs.

Challenge: SKIPPED — trivial synthesis task (no design choices, no trade-offs to challenge).

## 5. Follow-up Tasks

One follow-up task at `todo` — the doc writing itself. The research gate is satisfied; implementation is writing the README per the AC.

**Tier:** T1 (autonomous) — documentation from existing implementation, no architectural decisions.
