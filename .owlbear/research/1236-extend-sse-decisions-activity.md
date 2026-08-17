# Extend SSE to Decisions and Activity Polling

> **Owning task:** #1236 — Research — extend SSE to decisions and activity polling
> **Date:** 2026-05-01 **Status:** Complete

## 1. Context and Question

Task #1233 research scoped SSE to task-list polling only, explicitly deferring decisions and activity to a follow-up. Task #1234 (backlog) implements the backend `/api/events` endpoint watching only `tasks/`. This research investigates: how to extend the SSE stream to cover decisions (currently 60s poll) and activity/session data (currently one-time mount fetch), what paths to watch, event model, and impact on #1234's implementation scope.

**Current polling surfaces:**

| Target | Endpoint | Hook | Interval |
|--------|----------|------|----------|
| Tasks/board | `/api/tasks` | `useBoard` | 3s |
| Decisions | `/api/decisions/pending` | `usePendingDRs` | 60s |
| Activity/sessions | `/api/sessions` | `ActivityTab` | One-time (mount) |
| Corruption scan | `/api/tasks/scan` | `useScanPolling` | 60s |

**Paths to watch:**
- Tasks: `.owlbear/kanban/tasks/*.md` (flat, no subdirs)
- Decisions: `.owlbear/kanban/decisions/pending/*.md` (new DRs appear/disappear here)
- Activity: `.owlbear/kanban/activity.jsonl` (single file, append-only)

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | watchfiles.helpmanual.io — awatch API | Library docs | 0.95 |
| 2 | github.com/sysid/sse-starlette README (v3.4.1) | Library docs | 0.9 |
| 3 | .owlbear/research/1233-realtime-cockpit-updates.md | Parent research | 1.0 |
| 4 | .owlbear/research/1234-sse-endpoint-implementation.md | Backend contract | 1.0 |
| 5 | .owlbear/research/1235-eventsource-client-implementation.md | Frontend design | 0.9 |
| 6 | serve/cockpit/src/owlbear_cockpit/routes/decisions.py | Live code | 1.0 |
| 7 | serve/kanban/src/owlbear_kanban/activity_store.py | Live code | 0.9 |

## 3. Analysis

### 3.1 Multi-Path Watching Architecture

`awatch` accepts `*paths` — multiple directories or files in a single call.

| Option | Description | OS resources | Complexity | Late-created path discovery |
|--------|-------------|-------------|------------|----------------------------|
| A: Single `awatch` with 3 explicit paths | `awatch(tasks_dir, decisions_dir, activity_file)` — skip non-existent | 1 thread | Low | None — misses paths created after subscribe |
| B: Multiple `awatch` merged via asyncio | 3 separate generators + `asyncio.TaskGroup` | 3 threads | High | None — same skip problem |
| C: Recursive watch on `kanban_dir` | `awatch(kanban_dir, recursive=True)` + path classification | 1 thread | Medium | Full — catches new dirs/files automatically |

**Recommendation: Option C.** Recursive watch on `kanban_dir` solves the late-created path problem identified by challenge review. `decisions/pending/` may not exist at subscribe time but gets created later when the first DR arrives. Recursive watching catches this automatically. The noise (lock files, resolved decisions, archive) is handled by a path-based filter.

Key watchfiles facts: (1) `awatch(*paths)` supports multiple paths; (2) `recursive=True` (default) catches newly created subdirectories; (3) both directories and single files can be watched.

### 3.2 Event Model — Typed Invalidation Events

Extend the invalidation-only model from #1233 with typed `event:` fields:

```
event: tasks-changed
data: {"mtime": 1714567890123}

event: decisions-changed
data: {"mtime": 1714567891456}

event: activity-changed
data: {"mtime": 1714567892789}
```

Client dispatches via `EventSource.addEventListener('decisions-changed', ...)` — each event type triggers its specific refetch. This preserves all existing API contracts.

### 3.3 Backend Implementation Delta

The #1234 endpoint (currently tasks-only) extends from ~35 LOC to ~55 LOC:

```python
# Pseudocode for extended /api/events — recursive watch on kanban_dir
kanban_dir = engine.kanban_dir
tasks_dir = engine.tasks_dir
decisions_pending = kanban_dir / "decisions" / "pending"
activity_path = kanban_dir / "activity.jsonl"


def watch_filter(change, path: str) -> bool:
    p = Path(path)
    # Tasks: .md in tasks/ (not .tmp-)
    if p.parent == tasks_dir and p.suffix == ".md" and not p.name.startswith(".tmp-"):
        return True
    # Decisions: .md in decisions/pending/
    if p.parent == decisions_pending and p.suffix == ".md":
        return True
    # Activity: activity.jsonl specifically
    if p == activity_path:
        return True
    return False


def classify(path: str) -> str | None:
    p = Path(path)
    if p.parent == tasks_dir:
        return "tasks-changed"
    if p.parent == decisions_pending:
        return "decisions-changed"
    if p == activity_path:
        return "activity-changed"
    return None


async for changes in awatch(kanban_dir, watch_filter=watch_filter, recursive=True):
    event_types: dict[str, int] = {}
    for _, path_str in changes:
        event_type = classify(path_str)
        if event_type:
            p = Path(path_str)
            if p.exists():
                event_types[event_type] = max(event_types.get(event_type, 0), p.stat().st_mtime_ns)
    for event_type, mtime in event_types.items():
        yield {"event": event_type, "data": json.dumps({"mtime": mtime})}
```

### 3.4 Watch Filter Adaptation

Combined filter for recursive kanban_dir watch:

| Classification | Path pattern | Filter rule |
|---------------|-------------|-------------|
| `tasks-changed` | `kanban_dir/tasks/*.md` | `.md` suffix, not `.tmp-*`, parent == tasks_dir |
| `decisions-changed` | `kanban_dir/decisions/pending/*.md` | `.md` suffix, parent == decisions/pending |
| `activity-changed` | `kanban_dir/activity.jsonl` | Exact path match |
| Noise (rejected) | Lock files, resolved DRs, archive, .tmp-* | Everything else → filter returns False |

The recursive watch sees all changes under `kanban_dir` — filter rejects resolved decisions, lock files (`.activity.lock`), archive directory, and temp files. Only the three classified surfaces pass through.

### 3.5 Late-Created Path Handling (Revised)

**Critical correction from challenge review:** The original design (skip non-existent paths + pause polling) creates a stale-data bug. If `decisions/pending/` doesn't exist at subscribe and polling is paused, the first DR is never detected.

**Revised approach — two-part fix:**

1. **Backend: Recursive watch (Option C)** catches newly created `decisions/pending/` automatically. No path-existence check needed — the filter classifies whatever arrives.

2. **Frontend: SSE supplements, doesn't replace, for decisions/activity:**

| Surface | SSE role | Polling behavior when SSE connected |
|---------|---------|--------------------------------------|
| Tasks | Replaces polling (per #1235) | Paused — tasks dir always exists |
| Decisions | Supplements polling | 60s poll continues; SSE event triggers early refetch |
| Activity | Supplements one-time fetch | No poll to pause; SSE event triggers live refetch |

This means `usePendingDRs` keeps its 60s interval regardless of SSE state. When a `decisions-changed` event fires, it triggers an immediate refetch (ahead of timer). If the path doesn't exist yet, no events fire, and polling still works. Zero contradiction.

### 3.6 Frontend Integration (Revised)

| Hook | Current | With SSE | Pause polling? |
|------|---------|----------|----------------|
| `useBoard` | 3s poll | `tasks-changed` replaces timer | Yes — tasks dir always exists |
| `usePendingDRs` | 60s poll | `decisions-changed` triggers early refetch | No — supplementary only |
| `ActivityTab` | One-time fetch | `activity-changed` triggers refetch | N/A — no continuous poll |

The `useEventSource` hook from #1235 exposes typed event subscription. Adding `decisions-changed` and `activity-changed` listeners is additive — but requires the `useEventSource` hook and `paused` option from #1235 to exist first. These are **not yet implemented** (as noted by challenger). The frontend work depends on #1235's hooks being built.

**ActivityTab refactor needed:** Currently uses a one-shot `useEffect` fetch. To receive SSE-triggered refreshes, it needs to expose a `refetch` callable — either via `usePollingFetch` (with interval=Infinity or disabled polling) or via a simpler `useFetch` wrapper. This is new frontend work, not "just add listeners."

### 3.7 Scan Polling — Excluded from SSE

Corruption scan (`/api/tasks/scan`, 60s) checks task file and archive integrity. While task-file changes do overlap with scan scope, the scan also covers archive directories independently. Including scan in SSE would require either (a) a separate `scan-changed` event (redundant — scan is a computation, not raw state) or (b) triggering scan refetch on `tasks-changed` (conflates purposes). Keep scan at independent 60s interval. The cost of a stale scan result for ≤60s is negligible.

### 3.8 Activity.jsonl Watching — Compaction Consideration

The activity file is primarily append-only but undergoes periodic compaction (`compact_activity_log` in `activity_store.py`) which uses `atomic_write` — replacing the file atomically via rename. Watchfiles treats rename-into-place as a `modified` event on the target path. This means both appends and compactions emit `activity-changed` — correct behavior in both cases (client should refetch either way).

### 3.9 Impact on #1234 Scope

| Strategy | Description | Implementation cost | Risk |
|----------|-------------|--------------------| -----|
| Extend #1234 | Build multi-path from the start | +20 LOC, same architecture | Scope approval needed — #1234 currently approved for tasks-only |
| Separate task | #1234 = tasks-only, new task = extend watcher + add event types | Mild refactor | Clean separation of concerns |

**Revised recommendation: Separate follow-up task.** The challenger correctly noted that #1234's scope was explicitly approved as tasks-only by #1233 research, and expanding it without a new scope decision is authority drift. Create a new implementation task that extends the watcher after #1234 lands. The refactor is minimal (change `awatch(tasks_dir, recursive=False)` to `awatch(kanban_dir, recursive=True)` + add filter/classifier).

## 4. Recommendation

After #1234 (tasks-only SSE) lands, extend the watcher to `kanban_dir` recursive mode with path-based event classification. SSE supplements (not replaces) decisions polling and adds live activity updates. Three typed events: `tasks-changed`, `decisions-changed`, `activity-changed`.

**Key design principles (revised after challenge):**
- Recursive watch on `kanban_dir` — catches late-created paths (decisions/pending, activity.jsonl)
- Decisions polling continues at 60s — SSE triggers early refetch, doesn't pause polling
- Activity gains live updates via SSE — currently one-time mount fetch
- Separate implementation task from #1234 — respects approved scope boundaries

**Confidence: 0.72**

Challenge: reconsider — confidence in original: 0.29. Challenger identified critical stale-data bug (paused polling + missing paths), authority drift (expanding #1234 without approval), frontend delta undercount (useEventSource/paused don't exist yet), and scan invalidation gap. All addressed: switched to recursive watch, made SSE supplementary for decisions, acknowledged frontend dependency chain, and recommended separate follow-up task. Core approach (typed invalidation events via single SSE stream) was not disputed.

## 5. Follow-up Tasks

1. **Extend SSE watcher to multi-surface** (backend) — after #1234, change to recursive kanban_dir watch, add path classifier and typed events. Depends on: #1234.
2. **Wire `usePendingDRs` to SSE early-refetch** (frontend) — listen for `decisions-changed`, call refetch() ahead of 60s timer. Keep 60s poll active. Depends on: #1235 (useEventSource hook), follow-up 1.
3. **Wire `ActivityTab` to SSE live updates** (frontend) — refactor from one-shot useEffect to refetchable pattern, listen for `activity-changed`. Depends on: #1235, follow-up 1.
