---
id: 1390
title: 'P2-15: Guard Cockpit steering viewport product boundary'
status: backlog
priority: important
created: 2026-05-06T01:04:54.084895+00:00
updated: 2026-05-06T01:06:57.331717+00:00
tags:
- cockpit
- audit-remediation
- phase-2
- scope:cockpit
- type:docs
- type:test
- product-boundary
- guardrail
parent: 1363
depends_on:
- 1371
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Preserve the approved product boundary that Cockpit is a steering viewport, not a duplicate planner or agent lifecycle surface.

## Product Decision
Cockpit remains responsible for viewing, editing, moving or archiving, user blocks, health/admin, activity, and decision resolution. Task creation and agent lifecycle actions remain owned by agents, planner flows, and MCP unless a future explicit product brief changes this boundary.

## Acceptance Criteria
- Documentation and/or visible handoff copy make the Cockpit steering-viewport boundary explicit enough that future work does not accidentally add duplicate planner or MCP lifecycle controls.
- API allowlist documentation and tests or assertions continue to exclude create_task, claim/start_work, and end_work from Cockpit routes.
- UX handoff points direct users toward planner, agent, or MCP flows for task creation, claim/start, and release/end-work needs rather than adding lifecycle buttons.
- Existing valid Cockpit steering actions remain available: viewing, editing, moving or archiving, user blocks, health/admin, activity, and decision resolution.
- Verification confirms no new Cockpit route or UI affordance exposes create_task, claim/start_work, or end_work without a future explicit product brief.

## Scope
- In scope: Cockpit product-boundary docs, route allowlist guardrails, tests or assertions, and any minimal handoff copy needed to prevent drift.
- Out of scope: implementing create_task UI, claim/start_work UI, end_work UI, removing existing valid steering actions, and cache/SSE invalidation from #1346.

## Notes
This is intentionally a single guardrail task rather than a TDD implementation pair because it protects product authority through documentation and allowlist assertions, not a new functional workflow.
