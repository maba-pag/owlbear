---
id: 1949
title: 'P1-13: Ordered Memory purge flow'
status: build
priority: medium
created: 2026-07-17T03:04:26.420225+02:00
updated: 2026-07-17T03:04:43.870061+02:00
tags:
  - phase-1
  - scope:cockpit-web
  - state
  - api
parent: 1951
depends_on:
  - 1948
ac:
  - 'AC-1: Given successive accepted thresholds whose preview responses arrive out
    of order, the public Memory purge flow exposes only the preview associated with
    the current threshold and exposes confirmation as unavailable until that preview
    succeeds.'
  - 'AC-2: Given a current successful preview and confirmation, the public flow sends
    the same threshold to POST /api/memories/purge, exposes the returned purged/skipped/failed
    receipt, and invokes its completion callback once.'
  - 'AC-3: Given negative, fractional, empty, or nonnumeric threshold input, the public
    flow exposes a validation error and sends no purge request; given preview or execution
    failure, it exposes the request error without invoking completion.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
A headless Memory purge flow binds execution authority to the current accepted threshold and exposes stable preview, confirmation, error, completion, and receipt state to its caller.

## Scope
In scope: frontend API contracts and headless flow state for ephemeral threshold, validation, preview ordering, execution, receipt, errors, and completion callback.

Out of scope: rendered header, dialog, receipt presentation, and responsive layout.

## Contract Authorities
- HTTP paths and envelopes: task #1948 and OpenSpec Design decision 3.
- Headless interaction precedent: Cockpit `useCleanupFlow`.
- Threshold and ordering semantics: OpenSpec Design decision 5.

Proof guidance: run package-local Vitest at the public headless flow and real client-contract boundary with fetch replaced below it; make no rendered DOM or geometry claim.