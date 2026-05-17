---
id: 1635
title: 'P2-13: Migrate CleanupPanel/RepairPanel confirm-overlay dialogs to PModal'
status: research
priority: important
created: 2026-05-17T19:35:46.931221+02:00
updated: 2026-05-17T19:35:46.931221+02:00
tags:
  - frontend
  - pds
  - phase-2
parent: 1590
depends_on:
  - 1608
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Discovered by #1608 (component complexity inventory section 6): CleanupPanel.tsx and RepairPanel.tsx contain raw div[role='dialog'] confirm overlays that need migration to PModal. These are classified as 'complex integration' in the inventory. ~2 surfaces total.