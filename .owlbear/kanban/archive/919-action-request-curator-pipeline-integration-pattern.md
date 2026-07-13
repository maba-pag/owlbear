---
id: 919
title: Action request — curator pipeline integration pattern
status: archived
priority: medium
created: 2026-04-17T11:52:32.640374+00:00
updated: 2026-04-17T20:04:12.105606+00:00
tags:
- test-quality
- type:user-action
- scope:copilot
parent: 912
depends_on:
- 918
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #912

## AC

- Action request created in `.owlbear/decisions/pending/912-curator-integration.md`
- Describes integration options with trade-offs:
  - (a) Parallel dispatch: orchestrator dispatches curator alongside non-test-touching agents after archive
  - (b) Queue-based: curator maintains its own work queue, processes on next idle cycle
  - (c) Archive-triggered: orchestrator auto-dispatches curator immediately on archive event
  - (d) Separate orchestrator cycle: dedicated curator sweep after N archives accumulate
- Each option assessed for: latency, complexity, risk of test-suite interference
- Task blocked pending user decision
- No implementation — design decision gate only
