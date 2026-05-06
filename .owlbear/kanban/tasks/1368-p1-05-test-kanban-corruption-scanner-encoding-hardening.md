---
id: 1368
title: 'P1-05: Test kanban corruption scanner encoding hardening'
status: backlog
priority: critical
created: 2026-05-06T00:58:38.511616+00:00
updated: 2026-05-06T01:00:11.343396+00:00
tags:
- cockpit
- audit-remediation
- phase-1
- scope:kanban
- type:test
- backend
- corruption-scan
- encoding
parent: 1363
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Purpose
Write focused Python tests for non-UTF8 kanban task/archive files in the corruption scanner.

## Problem Evidence
- POST /api/tasks/scan returns 500 on real repo data because detect_corruption() reads UTF-8 and does not handle UnicodeDecodeError for archived files.
- Storage parsing handles encoding fallback more gracefully, so scanner behavior is inconsistent.
- Archived tasks with non-UTF8 bytes were observed under .owlbear/kanban/archive.

## Acceptance Criteria
- Tests cover a non-UTF8 task or archive markdown fixture and prove corruption scanning does not crash.
- Tests assert the intended behavior for unreadable encoding: explicit corruption/encoding scan item with file_path, code, and detail, or the same accepted fallback policy as storage.
- Existing valid-file scan behavior remains covered and unchanged.
- The proof is located at the kanban engine/scanner layer, not only at the Cockpit route boundary.
- The proof fails against the audited broken behavior and is suitable for #1369 to satisfy.

## Scope
- In scope: kanban corruption scanner tests and fixture coverage for encoding handling.
- Out of scope: Cockpit UI error rendering and route-level catch-all masking.

## Counterpart
Implementation task: #1369.
