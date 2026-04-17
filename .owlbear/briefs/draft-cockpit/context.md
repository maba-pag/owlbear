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

v1 must ship a **cockpit shell** that makes each of these a "new route + new panel component" job, not an "architect from scratch" job. v1 does **not** build any of them.
