---
id: 950
title: Archive redundant HookEvent reaction routing umbrella task
status: archived
priority: important
created: 2026-03-23T01:43:13.360348+01:00
updated: 2026-03-23T06:02:47.5803628+01:00
started: 2026-03-23T03:24:42.2301959+01:00
completed: 2026-03-23T06:02:47.5803628+01:00
tags:
    - agent
    - hooks
    - scope:core
    - type:build
parent: 947
claimed_by: builder
claimed_at: 2026-03-23T06:02:42.7632404+01:00
class: standard
---

Board cleanup only. This task retires redundant umbrella task #950 without modifying #955, #956, or #957. #955 carries the HookReaction policy schema and bootstrap router wiring contract, #956 carries the task-scoped retry reuse contract, #957 carries the notification and escalation executor reuse contract, and docs/research/hookevent-reaction-routing.md is the source of truth for the split. Append a one-line closure note to #950 documenting that relationship, then archive #950. Do not modify any other task files, src/, or tests/.

## AC

- [ ] Append a one-line closure note to #950 stating that #955 carries HookReaction policy schema plus bootstrap router wiring, #956 carries task-scoped retry reuse, #957 carries notification and escalation executor reuse, and docs/research/hookevent-reaction-routing.md is the source of truth for the split.
- [ ] The closure note cites docs/research/hookevent-reaction-routing.md.
- [ ] Archive #950 after appending the note.
- [ ] No other task files, src/, or tests/ are modified.

[[2026-03-23]] Mon 03:24

## Research

- Doc: docs/research/hookevent-reaction-routing.md
- Key finding: OwlBear already has notify, retry, and escalate executors; the missing piece is a config-driven policy layer that delegates to them instead of changing HookRegistry.
- Recommendation: keep HookRegistry best-effort, add validated hook_reactions config plus a bootstrap-wired HookReactionRouter, and inject retry and escalation executors via protocols.
- Clear failure routing: notification keeps backend fallthrough; retry reuses daemon block-on-exhaustion and budget-exceeded bypass; escalation keeps retry/skip/stop fallback; router failures log and stop without recursive hook emission.
- Attribution updated: docs/sources/overview.md now records Prefect, Celery, and Ruflo sources for this task.
- Follow-up tasks created: #955 Define HookReaction policy schema and bootstrap router wiring; #956 Reuse daemon retry state for task-scoped HookReaction retries; #957 Route HookReaction notification and escalation actions through existing executors.

[[2026-03-23]] Mon 04:10

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Append a one-line closure note naming #955, #956, #957, and docs/research/hookevent-reaction-routing.md as the split source of truth. | Verifiable self-closure of a redundant umbrella task. | Keep |
| The closure note cites docs/research/hookevent-reaction-routing.md. | Preserves provenance for the split. | Keep |
| Archive #950 after appending the note. | Clear terminal state for the redundant umbrella. | Keep |
| No other task files, src/, or tests/ are modified. | Keeps the task in a single board-cleanup domain and within the cross-task edit rule. | Keep |

### Architecture Notes

- docs/research/hookevent-reaction-routing.md already decomposes the executable work into #955, #956, and #957, so #950 is no longer a sound builder contract.
- src/owlbear/core/hooks.py keeps HookRegistry best-effort, while src/owlbear/bootstrap/hooks.py, src/owlbear/core/notification_hook.py, src/owlbear/daemon.py, and src/owlbear/orchestrator/loop_detection.py already own the separate runtime seams this umbrella previously bundled.
- Rewriting #950 as closure-only prevents duplicate multi-domain implementation scope. No TDD predecessor is required because this task now forbids src/ and test edits.

### Changes Made

- Rewrote #950 as a closure-only umbrella retirement task.
- Appended this Architecture Review section.
- Prepared #950 for todo.

### Dependencies

- Added/Removed/Verified: verified docs/research/hookevent-reaction-routing.md, docs/research/ruflo-analysis.md, and follow-up tasks #955, #956, and #957; no code dependencies and no TDD predecessor required.

[[2026-03-23]] Mon 04:50

## Test-Writer Notes

- Non-implementation task (type:build, board-cleanup only) — no tests applicable.
- Architect explicitly stated: 'No TDD predecessor is required because this task now forbids src/ and test edits.'
- AC is entirely board operations: append note + archive #950. Zero src/ or tests/ changes permitted.
- Passing through to builder.

[[2026-03-23]] Mon 06:02

## Closure Note

Umbrella retired: #955 carries HookReaction policy schema and bootstrap router wiring, #956 carries task-scoped retry reuse, #957 carries notification and escalation executor reuse; see docs/research/hookevent-reaction-routing.md as the source of truth for the split.
