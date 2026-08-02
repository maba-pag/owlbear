---
id: 1936
title: Activate Cockpit Lightning CSS configuration
status: archived
priority: medium
created: 2026-07-17T02:18:02.898724+02:00
updated: 2026-07-17T03:03:42.488725+02:00
tags:
  - type:build
  - config
  - scope:cockpit
  - rigor:lean
parent:
depends_on:
  - 1935
ac:
  - Vite actually uses Lightning CSS with the PDS-required LightDark exclusion.
  - Built Cockpit CSS preserves working light and dark PDS theme behavior.
  - No durable test merely asserts that Lightning CSS configuration text exists.
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Objective
Make Cockpit's configured Lightning CSS feature exclusion effective under Vite and remove misleading structural test coverage.

## Scope
Select Vite's Lightning CSS transformer, retain the PDS-required LightDark exclusion, and remove the existing tests that merely grep configuration text. Do not add replacement presence tests.

## Validation
Prove generated CSS preserves the PDS color-scheme behavior through build output and the existing real-browser theme check, not config-string assertions.

[[2026-07-17T03:03:37+02:00]]
## Builder Notes
- Activated Vite's Lightning CSS transformer so the existing PDS-required LightDark exclusion now applies.
- Removed two durable tests that only read Vite configuration source and asserted strings existed. Added no replacement presence tests; all behavioral theme tests remain.
- Proof: production build passed under Vite 8.1.5; emitted CSS retains light-dark(); the color-scheme behavior suite passed 21 tests; the focused Chromium light/dark scheme spec passed 2 tests.
- Builder challenger decision: pass. It inspected the exact two-file diff and independently repeated build, emitted CSS inspection, Vitest, and Playwright proof with no fixes.
- Board constraint: completed archival is accepted only from terminal collect, so this task advances directly to collect for immediate archival.
