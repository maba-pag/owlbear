---
id: 1369
title: 'P1-06: Harden kanban corruption scanner encoding handling'
status: backlog
priority: critical
created: 2026-05-06T00:58:39.965961+00:00
updated: 2026-05-06T01:00:22.167953+00:00
tags:
- cockpit
- audit-remediation
- phase-1
- scope:kanban
- type:fix
- backend
- corruption-scan
- encoding
parent: 1363
depends_on:
- 1368
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Purpose
Harden kanban corruption scanning so non-UTF8 task and archive markdown files cannot crash Cockpit scans.

## Problem Evidence
- detect_corruption() can raise UnicodeDecodeError on archived files, surfacing as a Cockpit scan 500.
- Storage parsing has a more graceful encoding path, leaving scanner behavior inconsistent.
- Real archived task files with non-UTF8 bytes exist in .owlbear/kanban/archive.

## Acceptance Criteria
- Corruption scanning never crashes on non-UTF8 task or archive markdown files.
- The chosen policy is explicit and documented in behavior: unreadable files produce corruption/encoding scan items with file_path, code, and detail, or scanner parsing follows the same accepted fallback policy as storage.
- Existing valid-file scan behavior remains unchanged.
- The fix lives in the kanban engine/scanner layer rather than only catching exceptions in Cockpit routes.
- The tests from #1368 pass.

## Scope
- In scope: kanban scanner encoding behavior for task and archive markdown files.
- Out of scope: Cockpit health UI rendering, frontend retry UX, and cache/SSE invalidation from #1346.

## Test Dependency
Satisfies #1368.
