---
id: 1636
title: 'P2-13: Implement CleanupPanel/RepairPanel confirm-overlay PModal migration'
status: research
priority: important
created: 2026-05-17T19:54:11.481740+02:00
updated: 2026-05-17T19:54:11.481740+02:00
tags:
  - frontend
  - pds
  - phase-2
parent: 1590
depends_on:
  - 1635
ac:
  - CleanupPanel confirming phase renders via p-modal element with open={true}, 
    not a raw div[role="dialog"] — no inline position:fixed or z-index styles 
    remain
  - RepairPanel confirming phase renders via p-modal element with open={true}, 
    not a raw div[role="dialog"] — no inline position:fixed or z-index styles 
    remain
  - Both modals use disableBackdropClick={true} and dismissButton={false} 
    (destructive-confirm pattern)
  - Escape key dismisses both confirm dialogs via PModal onDismiss → cancel 
    callback
  - All existing test suites pass (CleanupPanel.test, 
    CleanupPanel.integration.test, RepairPanel.test, RepairPanelFocusMgmt.test, 
    OverlayAnchoring.test, HealthBadgeRepair.test, SidecarUX.test)
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective

Replace the confirming-phase `div[role="dialog"]` confirm overlays in CleanupPanel.tsx and RepairPanel.tsx with PModal. Research findings in `.owlbear/research/1635-cleanup-repair-pmodal-migration.md`.

Follow-up from research #1635.

## Scope

### In Scope

- Replace raw `div[role="dialog"]` in CleanupPanel confirming phase with `<PModal>` (dialog role, `disableBackdropClick={true}`, `dismissButton={false}`).
- Replace raw `div[role="dialog"]` in RepairPanel confirming phase with `<PModal>` (same props).
- Remove inline positioning styles (`position: fixed`, `z-index`) from both confirm overlays.
- Adapt focus management to PModal container (PModal manages focus trapping internally).
- Update affected tests: OverlayAnchoring.test.tsx, RepairPanel.test.tsx AC12, RepairPanelFocusMgmt.test.tsx.

### Out of Scope

- RepairPanel's `OVERLAY_STYLE` on non-dialog phases (repairing, done, error).
- DRStatusIndicator popovers.
- HealthBadge popovers.