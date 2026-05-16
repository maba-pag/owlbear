---
id: 1618
title: 'P2-11: Complex integrations — modals → PModal'
status: research
priority: important
created: 2026-05-16T03:37:02.326584+00:00
updated: 2026-05-16T03:37:02.326584+00:00
tags:
  - frontend
  - pds
  - phase-2
parent: 1590
depends_on:
  - 1613
ac:
  - ConfirmDialog, ResolveModal, and ArchivalModal use PModal component
  - Focus trapping and focus return behavior preserved post-migration 
    (Playwright keyboard test)
  - Overlay dismiss on backdrop click and Escape key functional
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Custom modals → PModal. Focus trapping, focus return, dismiss behavior preserved.

Scope: Complex integrations (modals) only.
Out of scope: Simple swaps, cards, sidecar IA, filter panel.