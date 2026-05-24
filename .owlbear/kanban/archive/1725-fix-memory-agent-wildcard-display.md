---
id: 1725
title: Fix memory agent wildcard display
status: archived
priority: important
created: 2026-05-23T02:51:20+0200
updated: 2026-05-24T10:50:01.604135+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - memory
  - data-display
parent:
depends_on: []
ac:
  - Reproduce the Memory tab list showing a raw `*` agent/audience value in
    visible item metadata.
  - Replace wildcard display with a human-readable label that preserves the
    underlying meaning.
  - Ensure filtering and expanded detail behavior still expose the correct
    structured value where needed.
  - Validate with focused tests and desktop screenshot evidence.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## User Feedback Context
The Cockpit tab sweep showed Memory entries rendering `*` as visible metadata next to tags. That is technically faithful to the stored value, but it reads like broken UI in a polished cockpit.

## Evidence Before Fix
- Screenshot: `.owlbear/scratch/1716-wide-cockpit/sweep-memories-20260523.png`.
- The first visible Memory items show a raw `*` line before category chips.

## Evaluation Notes
- Classification: current visual/data-display polish issue.
- Product value: Memory is a moderation/read surface; wildcard values should read as intent, not as storage syntax.
- Likely display label: `All agents`, `Any agent`, or equivalent, while keeping the stored value unchanged for filtering/API semantics.

## Evidence
- MemoryTab display now formats wildcard `*` scope as `All agents` without mutating stored entry values.
- Agent filter options omit wildcard storage syntax while wildcard-scoped entries still pass any selected agent filter.
- Focused Vitest passed: `MemoryTab_1671.test.tsx` and `MemoryTab_1672.test.tsx`, 2 files, 131 tests.
- ESLint passed for `MemoryTab.tsx` and `MemoryTab_1671.test.tsx`.
- `npm run build` passed with the existing Vite chunk-size warning.
- Screenshot evidence: `.owlbear/scratch/1716-wide-cockpit/1725-memory-wildcard-after-fix.png`.
- Metrics evidence: `.owlbear/scratch/1716-wide-cockpit/1725-memory-wildcard-after-fix-metrics.json` reports `hasRawWildcardLabel: false`, `hasAllAgentsLabel: true`, and `filterIncludesWildcard: false`.
