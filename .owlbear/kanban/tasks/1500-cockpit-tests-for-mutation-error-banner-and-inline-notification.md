---
id: 1500
title: 'Cockpit: Tests for mutation error banner and inline notification'
status: research
priority: needed
created: 2026-05-12T02:38:27.742252+00:00
updated: 2026-05-12T02:38:47.388327+00:00
tags:
  - cockpit
  - frontend
  - testing
parent: 1494
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective\nAdd Vitest unit tests and Playwright E2E tests for the new PDS notification components.\n\n## Acceptance Criteria\n- Vitest: PBanner appears on simulated move/edit failure, correct state prop, dismiss clears\n- Vitest: PBanner auto-clears on next successful mutation\n- Vitest: PBanner survives task selection change (selectedTaskId change doesn't clear error)\n- Vitest: PInlineNotification appears in ArchivalModal on failure, retry action works\n- Vitest: PInlineNotification appears in ResolveModal on failure\n- Playwright E2E: Banner visible after simulated API error, dismissible, clears on retry success\n\n## Source\nResearch doc: .owlbear/research/cockpit-mutation-error-banner.md (task #1494)