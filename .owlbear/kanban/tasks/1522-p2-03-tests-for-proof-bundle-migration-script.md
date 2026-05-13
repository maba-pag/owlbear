---
id: 1522
title: 'P2-03: Tests for proof_bundle migration script'
status: backlog
priority: needed
created: 2026-05-13T02:29:59.211402+00:00
updated: 2026-05-13T02:30:19.032760+00:00
tags:
  - phase-2
  - scope:kanban
  - tdd
  - feature
  - migration
parent: 1514
depends_on:
  - 1516
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1514

## Scope
In scope: Unit tests for migration function that extracts proof_bundle from body to frontmatter
Out of scope: Engine changes, MCP tools, skill files

## Acceptance Criteria
- AC1: Migration function reads a task file with body line `Proof bundle: smoke`, extracts value `"smoke"`, and writes it to frontmatter `proof_bundle` field
- AC2: Migration function removes the matched `Proof bundle:` line from body text after extraction
- AC3: Migration function skips tasks that already have a non-None frontmatter `proof_bundle` value

Proof bundle: behavioral