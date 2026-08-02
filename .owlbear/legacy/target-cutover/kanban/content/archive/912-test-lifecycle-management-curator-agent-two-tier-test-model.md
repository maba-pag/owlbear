---
id: 912
title: Test lifecycle management — curator agent + two-tier test model
status: archived
priority: medium
created: 2026-04-17T10:56:46.604506+00:00
updated: 2026-04-17T20:04:15.466585+00:00
tags:
- test-quality
- pipeline
- architecture
parent:
depends_on: []
blocked: false
block_reason:
claimed_by: odd-mist
claimed_at: 2026-04-17T20:02:40.719227+00:00
---
## Brief

See `.owlbear/briefs/draft-test-quality/brief.md` for full Brief.

## Problem

The TDD pipeline generates task-scoped test files that accumulate without curation. Over time the suite becomes dominated by stale, task-coupled assertions that waste time, destroy signal, and corrupt agent behavior (dismissing failures as noise).

## Approach

Nuclear reset (delete all existing tests) + lifecycle curator agent (post-archive, non-blocking). Two-tier test model: task-scoped (transient) → module-level (durable). Quality gate on promotion: only contract-level assertions promoted. Builder visibility expansion: builders run module-level tests alongside task tests.

## Outcomes

1. Green suite = trust
2. Fast suite (under 60s)
3. Automated lifecycle (no manual cleanup)
4. Right-sized suite (test files map to modules)
5. Coverage floor ≥ 90% per curator operation

## Key Decisions

- Quality gate on promotion: in v1 (contract-level required)
- Agent deletion authority: accepted post-archive
- Builder visibility: in scope
- Legacy: nuclear reset
- Curator: non-blocking, asynchronous, integration pattern TBD via action request

## Affected Skills

w-tdd-red, w-tdd-green, w-code-review, w-task-verification, h-python-conventions, r-project-standards
