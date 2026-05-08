---
id: 1436
title: 'Fix HealthBadgeRepair_1168 assertion mismatch from #1393 RepairPanel changes'
status: backlog
priority: needed
created: 2026-05-08T12:04:38.739894+00:00
updated: 2026-05-08T12:04:57.786767+00:00
tags:
- cockpit
- frontend
- scope:cockpit-web
parent: 1363
depends_on:
- 1393
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Task #1393 changed `RepairPanel.tsx` confirmation dialog copy to include detailed irreversible/quarantine wording per AC6. The adjacent test suite `HealthBadgeRepair_1168.test.tsx` has 2 tests in `TestFromAC_RepairConfirmCopyExact` that still assert the old shorter wording.

## Acceptance Criteria

- [ ] AC1: Update the 2 assertion strings at ~L340 and ~L351 in `serve/cockpit/web/src/__tests__/HealthBadgeRepair_1168.test.tsx` to match the new confirmation text from #1393
  - Old: `"Fixed files are restored, unfixable files are quarantined. Continue?"`
  - New: `"Fixed files are restored, quarantined files are moved to the quarantine directory (.owlbear/scratch/quarantine), and failed files remain corrupted. This action can be irreversible and cannot be undone."`
- [ ] AC2: `npm test` passes with no failures in `HealthBadgeRepair_1168.test.tsx`
- [ ] AC3: No other test files broken by the change