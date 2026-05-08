---
id: 1456
title: 'P4-20: consolidation test: fixed-topology deployment readiness'
status: backlog
priority: important
created: 2026-05-08T19:32:35.891593+00:00
updated: 2026-05-08T19:42:12.789719+00:00
tags:
- phase-4
- scope:deployment-readiness
- type:test
- consolidation-test
- verification-probe
- kanban
- deployment-readiness
parent: 1437
depends_on:
- 1439
- 1441
- 1443
- 1445
- 1447
- 1449
- 1451
- 1453
- 1455
- 1457
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context
Brief: see parent #1437.

## Scope
In scope: final scratch-board and contract-inspection verification across completed child implementations.
Out of scope: source changes and full pytest or vitest execution.

## Acceptance Criteria
1. Test-writer records a fresh scratch-board walkthrough that starts with no config.yml and demonstrates fixed topology exposure, task creation, ID allocation from active plus archive filenames, activity event emission, and setup-created board directories.
2. Test-writer records a dispatch walkthrough showing pick_tasks leaves task and decision files unchanged while start_work reclaims one expired claim through the writer path.
3. Test-writer records a DR walkthrough showing create_dr creates a pending request and resolve_drs resolves it once without duplicate task summaries.
4. Test-writer records a maintenance walkthrough showing user-triggered cleanup releases expired claims, moves active archived tasks to archive storage, and reports skipped items.
5. Test-writer records MCP/Cockpit contract inspection for list filter semantics, tool annotations, structured error envelopes, and POST /api/tasks/cleanup response shape.
6. Test-writer records documentation/guidance inspection showing the fixed-topology deployment contract is described and stale config/automatic-side-effect claims are absent.
7. Test-writer adds no pytest, vitest, or full-suite execution as functional proof; verification evidence is limited to scratch-board walkthrough notes and contract inspection artifacts.