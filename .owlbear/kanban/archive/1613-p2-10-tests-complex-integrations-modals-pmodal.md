---
id: 1613
title: 'P2-10: Tests — complex integrations (modals → PModal)'
status: archived
priority: important
created: 2026-05-16T03:36:42.443740+00:00
updated: 2026-05-16T15:04:55.472657+00:00
tags:
  - frontend
  - pds
  - phase-2
parent: 1590
depends_on:
  - 1608
ac:
  - Tests assert ConfirmDialog, ResolveModal, and ArchivalModal use PModal 
    component
  - Tests assert focus trapping, Escape-key dismiss, and backdrop-click dismiss 
    behavior on PModal instances
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: deprecated
archival_refs:
  - 1618
---
Brief: see parent #1590.

Scope: Failing tests for modal → PModal migration (focus trapping, dismiss behavior).
Out of scope: Implementation, simple swaps, cards, filter panel.