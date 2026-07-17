---
id: 1935
title: Upgrade Cockpit PDS runtime to 4.4
status: archived
priority: medium
created: 2026-07-17T02:17:58.405911+02:00
updated: 2026-07-17T02:51:58.662217+02:00
tags:
  - type:build
  - scope:cockpit
  - rigor:standard
parent:
depends_on:
  - 1934
ac:
  - PDS React, loader, and self-hosted runtime assets all use version 4.4.0.
  - Cockpit uses supported PDS size and Banner contracts without changing
    user-visible message behavior.
  - The assembled Cockpit shell loads its local PDS runtime and renders
    correctly in Chromium.
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Objective
Upgrade the Porsche Design System React package, custom-element loader, and self-hosted runtime assets together to 4.4.0.

## Scope
Migrate currently deprecated PDS heading and icon size aliases, move the Shell banner message to its supported slot contract, synchronize local PDS assets, and preserve valid PInlineNotification descriptions. Do not redesign Cockpit UI.

## Validation
Use the build, existing PDS runtime and banner behavior checks, the maintained focused E2E gate, and browser screenshots of the assembled shell. Add no source-presence tests.

[[2026-07-17T02:51:55+02:00]]
## Builder Notes
- Upgraded both PDS packages and all self-hosted runtime assets from 4.3.0 to 4.4.0.
- Migrated deprecated heading and icon sizes to sm/md and moved the Shell Banner message into its supported default slot. Valid PInlineNotification description props remain unchanged.
- Updated the existing Banner suite to assert visible message behavior rather than the removed prop or a mock-only data attribute. No new test files added.
- Proof: package-only build passed and detected the expected pre-sync mismatch; post-sync build passed without mismatch warning; two focused Banner suites passed 21 tests; PDS runtime/CSP and foundation Chromium specs passed 13 tests; populated live Cockpit screenshot was visually coherent; runtime probe confirmed canvas, icon, and banner definitions plus a live canvas shadow root; deprecated-contract search returned no matches.
- Builder challenger decision: pass. It inspected scope and independently passed build, 80 focused Banner/DetailTab tests, CSS lint, and HTML lint with no fixes.
- Board constraint: completed archival is accepted only from terminal collect, so this task advances directly to collect for immediate archival.
