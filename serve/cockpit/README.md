# OwlBear Cockpit

Browser-based kanban UI for the OwlBear pipeline. Serves a React SPA backed by a FastAPI read/write API, both in a single `uv run cockpit` process.

---

## Quick Start

```bash
# Prerequisites: built frontend
cd serve/cockpit/web && npm run build && cd -

# Launch (defaults to http://127.0.0.1:8420)
uv run cockpit

# Options
COCKPIT_PORT=9000 uv run cockpit          # custom port
COCKPIT_NO_OPEN=1 uv run cockpit          # suppress browser auto-open
KANBAN_DIR=/path/to/.owlbear/kanban uv run cockpit  # custom board dir
```

---

## Architecture

```
Browser (React + Porsche DS)
    │  fetch /api/*
    ▼
FastAPI app  ──  read routes  ──▶  adapter.py  ──▶  KanbanEngine (read)
             └─  mutation routes  ──▶  [adapter.valid_transitions() pre-check]
                                  └──▶  KanbanEngine (write)
```

The **adapter** (`adapter.py`) is a thin boundary that wraps the five allowed read-only engine methods. Mutation routes call the engine directly but may call `adapter.valid_transitions()` for pre-flight validation (e.g. `move_task` validates the target status before writing).

---

## Engine Surface — Allowlist

The cockpit exposes a subset of `KanbanEngine`'s public API. All access goes through the adapter unless noted.

### Via adapter (read-only)

| Method | Purpose |
|--------|---------|
| `list_tasks(**kwargs)` | Task summaries for board columns |
| `show_task(task_id)` | Full task detail for the detail tab |
| `board_config()` | Statuses + priorities for column rendering |
| `valid_transitions(status)` | Validates drag-drop targets; also used by `move_task` route |
| `list_sessions(**kwargs)` | Work session data for the activity tab |

### Direct engine calls (mutations)

| Method | Route | Notes |
|--------|-------|-------|
| `engine.show_task()` | `POST /tasks/{id}/move` | Pre-check read before moving |
| `engine.move_task()` | `POST /tasks/{id}/move` | After `valid_transitions` pre-check |
| `engine.show_task()` + `engine.edit_task()` | `POST /tasks/{id}/edit` | Reads current task; diffs tags/deps |
| `engine.show_task()` + `engine.release_task()` | `POST /tasks/{id}/release` | Reads for existence check |

### Excluded methods — why

| Method | Reason excluded |
|--------|----------------|
| `create_task()` | No create flow in the UI — pipeline agents create tasks |
| `claim_task()` | Agent lifecycle operation, not user-initiated |
| `start_work()` / `end_work()` | Agent lifecycle operations, not user-initiated |
| `sweep()` | Background maintenance — not triggered from the UI |
| `refresh_config()` | Config reload; engine manages this internally |
| `agent_name` property | Internal constructor binding — not an operation |
| `revision` property | Internal write counter — not needed by UI |

---

## Shell-to-Surface Contract

The shell (`Shell.tsx`) owns the layout grid. Surfaces live in the `workspace` grid area and are registered via React Router. Adding a surface requires exactly **three touchpoints** — no shell layout changes are needed.

### Grid areas (from `Shell.css`)

| Area | Element | Fixed? |
|------|---------|--------|
| `status-bar` | `<header>` — traffic light, task count | ✓ shared |
| `nav-rail` | `<nav>` — surface navigation buttons | add button here |
| `workspace` | `<main>` — `<Routes>` renders here | add route here |
| `sidecar` | `<aside>` — Detail / Activity tabs | ✓ shared |


### Three touchpoints

**1 — Route** (in `Shell.tsx`, inside `<Routes>`):

```tsx
<Route path="/foo" element={<FooSurface />} />
```

**2 — Nav-rail button** (in `Shell.tsx`, inside `<nav>`):

```tsx
<button data-surface="foo">
  <p-icon name="some-icon" aria-hidden="true" />
  Foo
</button>
```

**3 — Component file**:

```
serve/cockpit/web/src/FooSurface.tsx
```

The component receives no required props from the shell. It owns its own data fetching.

---

## Hello-World Walkthrough — Adding a Second Surface

This walkthrough adds a minimal "Hello" surface that fetches `/health` and displays the result. No backend changes are required.

### Step 1 — Create the component

Create `serve/cockpit/web/src/HelloSurface.tsx`:

```tsx
import { useState, useEffect } from 'react'

export default function HelloSurface() {
  const [status, setStatus] = useState<string>('…')

  useEffect(() => {
    fetch('/health')
      .then(r => r.json())
      .then(d => setStatus(d.status))
      .catch(() => setStatus('error'))
  }, [])

  return (
    <div style={{ padding: 24 }}>
      <h1>Hello Surface</h1>
      <p>API status: <strong>{status}</strong></p>
    </div>
  )
}
```

### Step 2 — Register the route

In `Shell.tsx`, add an import and a route inside `<Routes>`:

```diff
 import KanbanBoard from './KanbanBoard'
+import HelloSurface from './HelloSurface'
 …
 <Routes>
   <Route path="/" element={<KanbanBoard />} />
+  <Route path="/hello-surface" element={<HelloSurface />} />
 </Routes>
```

### Step 3 — Add a nav-rail button

In `Shell.tsx`, inside `<nav className="shell__nav-rail" …>`:

```diff
 <button data-surface="kanban" aria-current="page">
   <p-icon name="list" aria-hidden="true" />
   Kanban
 </button>
+<button data-surface="hello">
+  <p-icon name="information" aria-hidden="true" />
+  Hello
+</button>
```

### Step 4 — Navigate

Open `http://127.0.0.1:8420/hello-surface`. The new surface renders alongside the shared status bar, sidecar, and nav rail. No other files need to change.

---

## Work Sessions Model

`GET /api/sessions` returns derived `WorkSession` objects built from `activity.jsonl`. Sessions are reconstructed at read time — there is no separate sessions store.

### Derived states

| State | Derivation condition |
|-------|---------------------|
| `running` | Open claim; last activity timestamp within `claim_timeout` |
| `stuck` | Open claim; last activity timestamp exceeds `claim_timeout` |
| `completed-pass` | `end_work` log entry whose `detail` starts with `"success:"` |
| `completed-rejected` | `end_work` log entry whose `detail` starts with `"reject:"` |
| `completed-fail` | Any other `end_work` outcome |
| `released` | `release` action in the log |

> **Note:** `sweep-release` (engine background sweep) resets the internal open-claim state but does **not** produce a `WorkSession` entry. Only a user-initiated `release` produces a session with state `"released"`.

### Filter vocabulary

| Filter value | Included states |
|-------------|-----------------|
| `active` | `running`, `stuck` |
| `all` | all states |
| `failed-or-rejected` | `completed-fail`, `completed-rejected` |
| `released` | `released` |

Usage: `GET /api/sessions?filter=active`

### Event mapping (`activity.jsonl`)

Each line is a JSON object. The sessions endpoint reads entries with these fields:

| Field | Type | Notes |
|-------|------|-------|
| `action` | string | `claim`, `end_work`, `release`, `sweep-release`, … |
| `task_id` | int | Groups events into per-task session chains |
| `detail` | string | Outcome string for `end_work`; message for others |
| `timestamp` | ISO 8601 | Used for `running`/`stuck` age calculation |
| `actor` | string | Who triggered the action (see Audit Trail below) |

---

## Audit Trail — `actor: "cockpit"` Convention

The engine is initialised with:

```python
KanbanEngine(kanban_dir, agent_name="cockpit")
```

Every mutation that the cockpit writes to `activity.jsonl` carries `actor: "cockpit"`. This distinguishes UI-initiated changes from agent-initiated ones (e.g. `actor: "builder"`) in audit queries and session filtering.

To verify the current actor for a running instance:

```python
from owlbear_kanban import KanbanEngine
engine = KanbanEngine(kanban_dir)
print(engine.agent_name)   # → "cockpit"
print(engine.revision)     # → write operation count since startup
```

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Service liveness check |
| `GET` | `/api/board` | Board config: statuses, priorities, valid_transitions map |
| `GET` | `/api/tasks` | Task summaries (supports `status`, `priority`, `tag`, `blocked` query params) |
| `GET` | `/api/tasks/{id}` | Full task detail |
| `GET` | `/api/sessions` | Work sessions (supports `filter` query param) |
| `POST` | `/api/tasks/{id}/move` | Move task to new status; body: `{"status": "…"}` |
| `POST` | `/api/tasks/{id}/edit` | Edit task fields; body: allowlisted fields only |
| `POST` | `/api/tasks/{id}/release` | Release a claimed task |
