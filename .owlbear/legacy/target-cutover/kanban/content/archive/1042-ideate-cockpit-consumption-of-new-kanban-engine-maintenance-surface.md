---
id: 1042
title: Ideate cockpit consumption of new kanban engine maintenance surface
status: archived
priority: medium
created: 2026-04-21 08:08:06.219579+00:00
updated: 2026-05-01T17:00:34.987446+00:00
tags:
- phase:cockpit
- type:ideation
- brief:b-followup
parent:
depends_on: []
blocked: true
block_reason: 'User Decision-Request: review the engine capabilities and UX seeds
  in the body. Decide whether to build cockpit operator-console UI (which seeds, which
  to drop), defer, or close as wontfix. Do not unblock without an explicit scope direction
  or wontfix decision.'
claimed_at:
archival_reason:
archival_refs: []
---
## Context

Brief B (`.owlbear/briefs/draft-kanban-engine-b-2026-04-20/`) lands a `CockpitEngineView` with 11 methods and locks the service-side cockpit backend/API surface that serves them. Most are read/edit/move/release surfaces the cockpit already needs. Five are *new* engine/backend capabilities introduced specifically to support a possible operator-console UI in the cockpit. Brief B commits that service-side interface; it does **not** commit cockpit product/UI scope.

This task is the placeholder for ideating whether/how the cockpit grows operator-console UI to consume those capabilities. Blocked by a user Decision-Request — do not start work without explicit unblock.

## Engine capabilities now available to the cockpit

1. **`list_activity(...)`** — filtered raw activity-stream events (by `task_id`, `action`, `source`, time window). Backed by `.owlbear/kanban/activity.jsonl`.
2. **`list_sessions(filter=...)`** — derived work-session view, filters: `active`, `all`, `blocked-or-rejected`, `released`. Each session has `state` ∈ {`running`, `stuck`, `completed`, `blocked`, `rejected`, `released`, `expired`}, durations, etc.
3. **`scan_corruption()`** — read-only corruption scan over `tasks/` and `archive/`. Returns `list[CorruptionError]`. Intended for badge polling.
4. **`repair_storage()`** — user-triggered two-phase repair (storage `scan_and_fix` → engine creates Action Request tasks for quarantined files). Returns merged `list[RepairOutcome]`.
5. **`compact_activity()`** — manual trigger for activity-log compaction. (Engine also auto-compacts at init when `activity.jsonl` > 1 MB; this is the operator override.)

## Possible cockpit UX seeds

Not commitments, just starting points for the ideation:

- **Activity timeline panel.** Per-task or board-wide view backed by `list_activity`. Filter by source (agent/cockpit/engine), action, time window.
- **Session history view.** Backed by `list_sessions("all")`. Show stuck/blocked/rejected sessions for retro / debug.
- **Health badge in header.** Periodic poll of `scan_corruption()`. Show count + severity. Click → details view.
- **Repair flow.** Health badge → "Repair now?" modal → confirm → `repair_storage()` → results panel listing fixed/quarantined/AR-created.
- **Stuck-session inspector.** Drill-down on a `stuck`/`expired` session — show last activity, options to force-release the claim (uses existing `release_task` admin endpoint).
- **Manual compact button.** Operator-only, hidden behind a developer/maintenance disclosure. Probably YAGNI for v1.

## What this task is NOT

- Not a commitment to build any of the above.
- Not a planner-decomposable feature task. It's an **ideation seed**.
- Not blocking Brief B/C implementation. The engine and cockpit backend/API surfaces ship regardless; this task only decides whether/how cockpit UI/product work consumes them.

## Acceptance / done criteria

This task transitions to `backlog` (or further) only after:

1. The user reviews the engine capabilities and the UX seeds above.
2. A decision is made: build now / build later / never / partial.
3. If "build now" or "partial": the chosen scope is decomposed into concrete cockpit feature tasks and this stub is closed.
4. If "later" or "never": this task moves to `archived` with appropriate `archival_reason` (`dropped` or `wontfix`); no further cockpit work is created.

## References

- Brief B: `.owlbear/briefs/draft-kanban-engine-b-2026-04-20/brief.md` §3.1 (CockpitEngineView), §7 (downstream rollout matrix — cockpit row)
- Brief B: `.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md` §5 (Cockpit Engine Surface)
- Brief C: `.owlbear/briefs/draft-kanban-storage-c-2026-04-20/paper-c.md` §7 (activity stream + sessions)

## Decision Request

@user — please review and either:
- Unblock with rough scope direction (which seeds appeal, which to drop), OR
- Mark this task `wontfix` if cockpit stays as a board viewer/editor only.
