---
id: 456
title: Implement audit-centric dispatch-cycle trace ID
status: archived
priority: medium
created: 2026-03-30 23:47:25.363350+02:00
updated: 2026-04-03 01:13:11.367111+02:00
started: 2026-04-03 01:13:11.367111+02:00
completed: 2026-04-03 01:13:11.367111+02:00
tags:
- scope:agents
- phase-2
- type:build
class: standard
archival_reason: completed
archival_refs: []
---

## Context
Add a cycle_id (uuid4 hex) to the orchestrator dispatch loop and audit models for debugging correlation. Audit-only approach per docs/research/dispatch-cycle-trace-id.md.

## Acceptance Criteria
- [ ] DispatchEvent and CompletionEvent models include cycle_id: str field
- [ ] run_loop() generates uuid4().hex per cycle, passes to dispatch_wave() and dispatch_entry()
- [ ] ACP session_name format updated to owlbear-{cycle_id[:8]}-{agent}-{task_id}
- [ ] AuditLog.query() accepts optional cycle_id filter
- [ ] Existing tests updated for new field; new tests verify cycle_id propagation
