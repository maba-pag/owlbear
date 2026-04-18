# Context

## Initial Request

User wants to build a web UI for OwlBear. Most pressing: kanban board has no visual representation — user doesn't know what tasks are open, in progress, or who (which agent) is working on what. Stated as non-YAGNI: build an **extensible web GUI**, starting with the kanban board.

Longer horizon (open, not-in-scope-yet): drag-and-drop tasks onto chat fields / agent lists to kick off work. Mentioned as North-Star direction only; no scope impact.

## Prior Foundation (already landed)

- `draft-kanban-web-gui-prep` Brief was the explicit pre-work for this project. The engine lives at `serve/kanban/` (`owlbear_kanban`), with:
  - `board_config()` — valid statuses, priorities, display order
  - `valid_transitions(status)` — legal moves per status
  - `revision` counter — cheap change-detection for polling
  - `TaskSummary` — schema-validated list projection
  - Guidance that a GUI adapter must **not** expose `claim_task`, `start_work`, `release_task`, `end_work`, `pick_dispatchable`.

## Problem Statement (after M1 Critic loop-back)

OwlBear today is steered entirely through the CLI and filesystem. The user must list tasks via MCP, read task files by hand, open `activity.jsonl` to infer what's running, and jump into decision files to see what's pending. This is fine for an automated pipeline but **leaves the human operator blind and slow when intervention matters**.

The real problem is **not "I can't see the board"** but **"I can't quickly decide what needs my attention and act on it."** The board is the most acute blind spot because it aggregates the most state, but the underlying need is a **steering cockpit**: a single surface where the operator observes the system, spots where their judgement is required, and intervenes directly.

v1 focuses on the kanban surface because that is the highest-value beachhead. The cockpit *shell* must be structured for additional surfaces already named as near-term extensions (see below).

## Scope Shape (after M1 loop-back)

### Framing

- **"Steering cockpit"** — intervention verbs are the headline, not secondary. Not a read-only dashboard.
- **Audience:** single user on laptop + occasional demo shoulder-surfing. No auth, no multi-user.
- **Board / activity weighting:** ~70 % board, ~30 % activity. Activity is a proper panel, not a strip.
- **Acceptable staleness:** 2–5 s between agent MCP write and GUI reflection. Short-poll on the `revision` counter is sufficient for v1; no SSE / WebSocket yet.

### v1 mutations (allowed)

- Move task (status transition, constrained by `valid_transitions`)
- Reprioritise
- Block / unblock
- **Unclaim / release** (never claim)
- Edit markdown body
- Edit allowlisted YAML header fields (title, tags, priority, depends_on, parent, block_reason — not timestamps, ids, claim fields)

### v1 mutations (out)

- Task creation — agent-only
- Claim, `start_work`, `end_work`, archive, dispatch — agent-only per prep brief
- Editing timestamp / id / claim fields directly

### Display principle

- Never dump raw file contents. Parse YAML frontmatter and markdown body separately. Structured header controls + markdown body viewer/editor.
- Activity panel is derived from existing state: `claimed_by`, `claimed_at`, `claim_timeout`. `claimed + valid-claim == running` is an acceptable v1 proxy; no process monitoring.

### Intervention principle (resolves the unclaim exception)

> **Humans may RELEASE stuck work. Only agents may CLAIM or advance work-state.**

The cockpit is a *stop-and-redirect* surface, not a *start-and-run* surface. Unclaim fits; claim/start/end/dispatch don't.

### Extensibility — what v1 must earn

The cockpit is planned to host, in future Briefs:

1. Activity / agent monitor panel (closest to v1)
2. Decision-queue surface (pending decisions/actions)
3. Knowledge-search surface
4. Memory insight + curation (upgrade / delete entries)
5. Agent / skill / instruction editor
6. VS Code settings shortcut (disable all extensions / enable subsets / presets; possibly auto-switch based on orchestrator state)
7. North-Star: drag task → chat/agent dispatch

8. **Recurring-tasks / maintenance panel** — memory-curator, test-curator, agent audit prompts, etc. Surface upcoming/overdue maintenance work the user should schedule or trigger.

v1 must ship a **cockpit shell** that makes each of these a "new route + new panel component" job, not an "architect from scratch" job. v1 does **not** build any of them.

### Data-source clarification (revised at M4)

Running-state-at-a-glance (the traffic-light counts in the status bar) derives from task **claim fields** (`claimed_by`, `claimed_at`, `claim_timeout`) which live in task files. This signal is always available regardless of log state.

The **Work Sessions** activity surface (D10) requires a richer signal — one logical row per claim cycle that mutates as state changes. This needs a **dedicated sessions log** maintained by the engine (new schema, designed for this purpose). The legacy `.owlbear/kanban/activity.jsonl` format may be replaced or superseded — nothing currently consumes it, so we are free to redesign. Engine gains a `list_sessions(...)` helper as accepted scope of this project.

## Outcomes (M2, post-Critic)

### O1 — Board at a glance
Opening the cockpit shows the full kanban board: columns by status, cards by priority. Each card visibly communicates status, priority, block state, and running state without clicking. The experience feels **finished, not utilitarian** — smooth transitions, visible hierarchy, no browser-default styling.
*Indicator:* At 1440×900 viewport with ≥200 tasks loaded, all status columns are visible (horizontal scroll permitted between columns; vertical scroll within a column). "What's in review?" and "What's blocked?" answerable at a glance. Cold-load time is explicitly **not a pass/fail criterion** — post-load smoothness is.

### O2 — Intervene without leaving the surface
The six v1 mutations (move, reprioritise, block/unblock, unclaim, edit body, edit allowlisted YAML) are reachable from the board — inline on cards for quick actions, via a detail surface (tab or panel, not prescribed) for body/header edits. Mutations go through `owlbear_kanban` and are visible to agents within the staleness budget.
*Indicator:* Quick mutations reachable in ≤2 clicks/keystrokes. A GUI move is visible to a parallel MCP `list_tasks` within 5 s. Destructive mutations require confirm (per O6).

### O3 — I know what's running, and I know my view is fresh
Two coupled signals:

1. **Activity surface** shows task-level run state in human language: *running* (claimed, claim valid), *stuck* (claimed, claim expired — needs release), *free* (unclaimed). Agent identity and claim age shown. No raw technical fields.
2. **Status region** shows cockpit → engine + MCP server connection health as a traffic light: green = up-to-date, yellow = stale (poll lag exceeds threshold), red = disconnected. Thresholds are calibration, not contract. One indicator per connected service.

*Indicator:* (a) An expired claim is unclaimable from the activity surface without reasoning about timeouts. (b) When polling stalls or engine is unreachable, the status region turns yellow/red within one poll interval and the user knows not to trust edits in flight.

### O4a — Extensibility: the shell welcomes new surfaces
Adding a second cockpit surface is a *route + component* job, not a shell rework. The engine adapter and the shell's layout/nav contract are documented so a future brief can drop a "decision queue" or "knowledge search" surface in without architectural reopening.
*Indicator:* A hello-world second surface exercise is feasible and documented. Contract between shell and surface is written down (inputs: routing, engine adapter, status region slots; outputs: primary-nav entry, workspace content).

### O4b — Cockpit layout philosophy
v1 ships an app shell with a primary-nav region (left icon rail, surface selectors), a workspace region (current surface — kanban board in v1), a status region (top bar with traffic light + running/stuck/free counts), and a sidecar region (right pane). The sidecar in v1 is **populated**, not reserved-empty: it carries the **Detail** and **Activity** tabs that pair with the kanban surface. Future surfaces may bring their own sidecar tabs or repurpose the slot. Contextual-nav (additional left-side or workspace-internal navigation) remains reserved-but-empty in v1.
*Indicator:* v1 layout matches the cockpit philosophy visually (nav / workspace / sidecar / status identifiable without a legend). The sidecar shows two tabs by default. Reserved areas (e.g. additional left-side nav for projects/consumers) are present but empty until a future surface populates them.

### O5 — Coherent, tokenized design
All UI uses a single design system's primitives and tokens. No browser-default styling in v1 surfaces. Colour, spacing, and type are centralized in a tokens layer; recolouring is a token swap. **Porsche Design System is the visual reference**, applied if it fits the chosen stack cleanly; otherwise an equally high-quality DS matching the stack is adopted. **Tech first, design second** — we pick the stack for what best serves the cockpit, then pick the DS that best matches.
*Indicator:* No hand-rolled colour hex values outside the tokens file. Custom components follow the chosen DS's primitives and tokens. Visual review confirms "single coherent design language."

### O6 — Safe intervention
- Destructive / irreversible actions (unclaim, backward status moves) require confirm.
- Optimistic UI with rollback on engine error; errors surface inline without silent data loss.
- Clear visual distinction between **agent-owned fields** (read-only in UI: id, timestamps, claim fields) and **human-editable fields**. Mutating a read-only field is impossible in the UI, not merely rejected by the engine.
- Stale-view protection relies on the status-region traffic light (O3), not per-save conflict detection. Users refresh on yellow/red before editing.

*Indicator:* Read-only fields have no interactive affordances. Unclaim and backward-status require confirm. Engine errors render inline, view state survives.

### O7 — Trustworthy foundation (Shared-tier)
- Engine↔cockpit contract is documented: which engine methods the GUI uses, which it must not.
- GUI-facing adapter layer has test coverage meeting the Shared-tier bar.
- When engine is unreachable or polling fails, the cockpit surfaces the failure via O3's status region; core surfaces do not white-screen or show silently stale data.

*Indicator:* (a) Adapter test coverage meets Shared-tier bar. (b) Docs page lists the engine surface used. (c) Induced engine failure produces visible, recoverable error state within one poll interval.

