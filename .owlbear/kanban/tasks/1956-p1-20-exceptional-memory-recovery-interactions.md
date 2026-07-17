---
id: 1956
title: 'P1-20: Exceptional memory recovery interactions'
status: build
priority: low
created: 2026-07-17T04:54:13.687765+02:00
updated: 2026-07-17T04:54:49.595942+02:00
tags:
  - phase-1
  - scope:cockpit-web
  - ui
  - navigation
parent: 1958
depends_on:
  - 1954
  - 1955
ac:
  - 'AC-1: Given contested_by_task parseable as a non-negative task ID, activating
    the detail reference dispatches the existing Cockpit task-detail event and Shell
    opens that task; null provenance shows an em dash and malformed provenance renders
    inert text.'
  - 'AC-2: Given a contested, disputed, or stale entry, detail shows Resolve and a
    successful current-token mutation refreshes the rendered entry to approved; pending,
    curated, approved, and deleted entries show no Resolve action.'
  - 'AC-3: Given a resolve response with MEM_CONFLICT, the page retains the exceptional
    entry state and expanded detail and shows the existing mutation error feedback.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
The operator can follow active challenge provenance and explicitly resolve contested, disputed, or stale entries with stable success and conflict feedback.

## Planning Source
- OpenSpec: `openspec/changes/expose-memory-lifecycle-in-cockpit`
- Capability requirements: Contested-task navigation, Human-only exceptional-state resolution

## Scope
- In scope: frontend resolve client and action, existing task-detail event integration, entry refresh, and mutation feedback.
- Out of scope: backend/domain semantics, MCP tools, overview/detail layout redesign, and new routing mechanisms.

## Interaction Contract
Use the existing Cockpit task-detail event for parseable non-negative task IDs. Null provenance renders an em dash; malformed provenance remains inert text.

Proof guidance: exercise the rendered Memory page and Shell event/client integration; fetch may be replaced below the frontend HTTP client boundary, but the resolve action and task event must remain real.