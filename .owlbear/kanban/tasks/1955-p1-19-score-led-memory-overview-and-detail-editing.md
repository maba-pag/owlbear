---
id: 1955
title: 'P1-19: Score-led memory overview and detail editing'
status: build
priority: medium
created: 2026-07-17T04:54:05.097197+02:00
updated: 2026-07-17T04:54:49.688056+02:00
tags:
  - phase-1
  - scope:cockpit-web
  - ui
  - memory
parent: 1958
depends_on:
  - 1954
ac:
  - 'AC-1: Given entries with differing or equal scores across the seven canonical
    states, the rendered Memory page shows title, scope agents, categories, and two-decimal
    score, orders score descending then state priority, creation time, and ID, and
    can filter contested, disputed, and stale entries.'
  - 'AC-2: Given an expanded entry, detail shows content plus ID, categories, confidence,
    state, Outstanding marks with star and count, score, source agent, scope agents,
    created, updated, approved, and contested task; score, scope, and categories also
    remain in the summary, while unremarkable_count and didnt_use_count are absent.'
  - 'AC-3: Given edit mode on a non-deleted entry, title, content, categories, confidence,
    and scope agents are controls while ID, state, Outstanding marks, score, source
    agent, timestamps, and contested task remain visible read-only; a deleted entry
    has no edit action and an approved edit renders the returned curated state.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
The operator can scan entries by current score, inspect the confirmed metadata, and edit mutable fields without losing read-only lifecycle context.

## Planning Source
- OpenSpec: `openspec/changes/expose-memory-lifecycle-in-cockpit`
- Capability requirements: Score-led memory overview, Complete lifecycle-state visibility, Operator-relevant memory details, Detail-aligned editing

## Scope
- In scope: frontend memory API types, state filters, ordering, overview, expanded detail, and edit presentation.
- Out of scope: resolve mutation, contested-task navigation, backend semantics, score colors, pinning, and raw negative counters.

## Presentation Contract
Score, scope agents, and categories remain intentionally duplicated between summary and detail. Outstanding assessments are labeled `Outstanding marks` with a star icon and count, not `Starred`.

Proof guidance: run focused package component checks; capture a screenshot only when visual framing or responsive non-overlap cannot be established from maintained assertions.