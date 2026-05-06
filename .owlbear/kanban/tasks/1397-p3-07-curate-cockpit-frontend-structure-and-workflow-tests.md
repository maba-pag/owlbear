---
id: 1397
title: 'P3-07: Curate Cockpit frontend structure and workflow tests'
status: backlog
priority: needed
created: 2026-05-06T01:09:45.089526+00:00
updated: 2026-05-06T01:12:29.851242+00:00
tags:
- cockpit
- audit-remediation
- phase-3
- scope:cockpit-web
- type:refactor
- type:test
- frontend
- test-curation
- cleanup
parent: 1363
depends_on:
- 1392
- 1394
- 1396
- 1383
- 1389
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Clean up Cockpit frontend structure and durable workflow tests after the audited user-facing workflows are stabilized.

## Problem Evidence
- Shell.tsx contains production-time test harness leakage by checking mockedKanbanBoard.mock.
- usePolling.ts and useOptimistic.ts appear unused by the app and referenced only by historical tests.
- Many task-scoped RED-phase comments remain in active tests after implementation.
- Durable behavior tests and historical task artifacts are mixed together.

## Acceptance Criteria
- Production application code no longer contains test harness detection or mockedKanbanBoard.mock leakage.
- Unused production hooks are deleted or repurposed only if they serve current application behavior; stale tests that only preserve old scaffolding are removed.
- Cockpit frontend tests are consolidated around current product behavior and user workflows rather than historical task-phase assertions.
- Meaningful regression coverage remains for build behavior, health behavior, task detail workflow, decisions, dashboard layout, operational sidecar behavior, and accessibility.
- Task-scoped RED-phase comments are removed or rewritten into durable behavior descriptions where the tests remain valuable.
- Verification confirms no unrelated Cockpit product behavior is removed.

## Scope
- In scope: Cockpit frontend production test-harness cleanup, unused hook curation, stale frontend test cleanup, durable test organization, and verification of retained coverage.
- Out of scope: implementing dashboard redesign from #1392, operational sidecar behavior from #1394, accessibility remediation from #1396, delivery gate hardening from #1399, docs, and cache/SSE invalidation from #1346.

## Notes
This is intentionally a single cleanup task rather than a TDD pair because it curates existing code and test artifacts after the product workflows are covered by preceding tasks.
