---
id: 1828
title: Review DetailTab PDS payload timeout
status: research
priority: important
created: 2026-05-24T11:19:10.398096+02:00
updated: 2026-05-24T11:19:10.398096+02:00
tags:
  - scope:cockpit-web
  - pds
  - detail-tab
  - discussion
parent: 1773
depends_on: []
ac:
  - DetailTab title/priority edit behavior is verified with the current PDS
    controls.
  - The decision distinguishes product regression from stale/flaky test
    behavior.
  - Any approved change preserves edit POST payload correctness.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
The full Cockpit frontend suite reported a timeout in the PdsMigration DetailTab payload test for changed title and priority values in the edit POST body.

## Evidence
- Test: `serve/cockpit/web/src/__tests__/PdsMigration.test.tsx`
- Failure: `changed title appears in the POST body after save` timed out after 10000ms.

## Boundary
Treat this as a possible stale or flaky test first. Verify the actual DetailTab edit workflow and emitted payload before changing product code.

## User Decision
Decision: remove or fix the test if it is buggy; tests follow the product. Do not change product code just to satisfy a stale PDS/jsdom timeout.

Implementation direction: verify the actual mouse-driven title/priority edit-save workflow and emitted payload. If the product behavior works, adjust/delete the failing test. If the product behavior is broken, fix the product path.
