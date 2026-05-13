---
id: 1524
title: 'Consolidation test: structured task specification'
status: backlog
priority: important
created: 2026-05-13T02:30:11.908839+00:00
updated: 2026-05-13T02:34:15.314747+00:00
tags:
  - phase-4
  - scope:kanban
  - consolidation-test
  - feature
parent: 1514
depends_on:
  - 1516
  - 1518
  - 1520
  - 1523
  - 1521
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1514

## Scope
In scope: End-to-end integration tests spanning model, engine, MCP, and migration layers
Out of scope: Skill file verification, Cockpit UI

## Acceptance Criteria
- AC1: Create task via engine with `ac=["criterion1"]` and `proof_bundle="behavioral"`, then `show_task` returns both fields with correct values
- AC2: Edit task via engine with `add_ac=["criterion2"]` and `proof_bundle="smoke"`, then `show_task` reflects both changes
- AC3: After running migration on a task file with body `Proof bundle: critical`, `show_task` returns `proof_bundle: "critical"` in frontmatter and body no longer contains the `Proof bundle:` line

Proof bundle: behavioral