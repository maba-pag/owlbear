---
id: 1499
title: 'Cockpit: Replace modal error display with PInlineNotification'
status: research
priority: needed
created: 2026-05-12T02:38:27.712681+00:00
updated: 2026-05-12T02:38:47.374119+00:00
tags:
  - cockpit
  - frontend
  - ux
parent: 1494
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective\nSwap plain PText error rendering in ArchivalModal and ResolveModal for PDS PInlineNotification with retry action button.\n\n## Acceptance Criteria\n- ArchivalModal renders PInlineNotification (state='error') on 409/422/500/network failure\n- ResolveModal renders PInlineNotification (state='error') on submission failure\n- PInlineNotification shows actionLabel='Retry' with actionIcon='reset' for retryable errors (409, network)\n- PInlineNotification shows no action button for non-retryable errors (422 validation)\n- actionLoading=true while retry is in progress\n- Notification dismissed on successful retry or manual dismiss\n- Existing error test assertions updated for new component selectors\n\n## Source\nResearch doc: .owlbear/research/cockpit-mutation-error-banner.md (task #1494)