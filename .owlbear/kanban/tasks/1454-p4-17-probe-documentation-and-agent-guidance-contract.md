---
id: 1454
title: 'P4-17: Probe documentation and agent guidance contract'
status: backlog
priority: needed
created: 2026-05-08T19:32:31.483304+00:00
updated: 2026-05-08T21:51:22.026260+00:00
tags:
- phase-4
- scope:docs
- type:test
- verification-probe
- docs
- guidance
- deployment-readiness
parent: 1437
depends_on: []
blocked: false
block_reason:
claimed_at: 2026-05-08T21:51:22.026260+00:00
archival_reason:
archival_refs: []
---

## Context
Brief: see parent #1437.

## Scope
In scope: documentation and agent-guidance inspection probes for the fixed-topology deployment contract.
Out of scope: source changes and full-suite proof.

## Acceptance Criteria
1. Test-writer records a documentation inspection checklist covering fixed topology constants, no seed config.yml, scan-based ID allocation, read-only pick_tasks, start_work claim reclamation, resolve_drs, create_dr, Cockpit cleanup, list filter semantics, and MCP error envelopes.
2. Test-writer records a guidance inspection checklist for pipeline instructions and skills that mention config.yml, manual DR files, pick_tasks side effects, sweep behavior, or MCP tool annotations.
3. Test-writer records search patterns that identify stale guidance claims about configurable statuses, next_id, activity_log toggles, automatic DR resolution, automatic sweep, or move_task idempotency.
4. Test-writer adds no pytest, vitest, or full-suite execution as functional proof; verification evidence is limited to documentation artifact inspection and search output captured in task notes.