---
id: 1560
title: 'P2-01: Decide Cockpit PDS policy and redesign constraints'
status: review
priority: critical
created: 2026-05-14T18:25:57.129252+00:00
updated: 2026-05-14T18:53:21.430526+00:00
tags:
  - phase-2
  - scope:cockpit
  - frontend
  - type:docs
  - type:design-policy
  - visual-remediation
parent: 1559
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Context
Source of truth: `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md`.
Use existing pending DR: `.owlbear/kanban/decisions/pending/1534-decision.md`. Do not create a duplicate DR for the coordinated redesign choice unless #1534 is rejected or split.

## Scope
In scope: record the redesign decision, PDS visible-control policy, sidecar IA choice, overlay strategy, mobile contract, visual gate requirement, and PDS asset-mode stance.
Out of scope: UI implementation, test implementation, and switching PDS assets to CDN mode.

## Acceptance Criteria
AC-1: Architect records the DR #1534 response or amended DR reference plus chosen values for remediation scope, sidecar IA, overlay strategy, mobile contract, visual-gate requirement, and PDS asset mode; verify by artifact inspection of this task body.
AC-2: Doc-writer adds a tracked Cockpit design policy artifact that maps PPopover, PModal, PSheet, PInputSearch, PSwitch or PCheckbox, PSelect plus PSelectOption, PTag, and PSegmentedControl to Cockpit use cases and lists exceptions with reasons; verify by diff inspection.
AC-3: Architect keeps design-dependent child tasks at backlog until AC-1 and AC-2 evidence is present; verify by board-state audit.

Proof bundle: skip

## Evidence Expectations
Decision reference, tracked policy diff, and board-state audit notes.
2026-05-14T18:29:07+00:00
Planner handoff verification: release accidental claim on newly created backlog task; no status change.
2026-05-14T18:34:21+00:00


## Planner Audit Amendment — Visual Target Gate
The initial task graph had a design-policy gate, but not a strong enough visual target gate. Add these requirements before implementation children advance:

AC-4: The tracked Cockpit design policy artifact includes a visual target/rubric for the dashboard, not only a component map. It must name audience, density target, typography hierarchy, surface/elevation rules, empty-state tone, icon/action rules, and screenshot states that reviewers will compare.

AC-5: The policy artifact explicitly records the PDS asset-mode decision: keep local pinned PDS runtime assets unless the product explicitly changes CSP/offline-after-build/consumer packaging constraints. Live CDN is not accepted as a visual remediation shortcut.

Evidence expectation: artifact diff plus references to `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md` sections 4, 7, 8, and 9.


## User Decision — 2026-05-14
Decision captured in chat via askQuestions: **Use recommended package**.

Resolved policy package for Cockpit visual remediation:
1. **Remediation scope:** approve a full coordinated Cockpit dashboard redesign cycle, not incremental local polish.
2. **PDS visible-control policy:** PDS-first for every visible production control; exceptions must be named in the policy artifact with rationale and test strategy.
3. **Visual target:** quiet, dense developer-operations cockpit; professional inspector/dashboard surface; no raw admin HTML, no marketing composition, no decorative overdesign.
4. **Sidecar IA:** redesign sidecar as an inspector. Pending DR queue may remain in the sidecar only if composed, scannable, and visually subordinate to selected-task inspection; otherwise move it to a sheet/route as recorded in the policy artifact.
5. **Overlay strategy:** `PPopover` for compact status disclosures, `PModal` for blocking confirmations/decisions, `PSheet` for dense side workflows. Treat the task context menu as an overlay surface that must be styled and tested.
6. **Mobile contract:** keep 320px no-overflow as a hard gate. Preferred direction is board-first mobile with sidecar/detail in a sheet; if that proves too costly, use a controlled unsupported/narrow-view message rather than compressed broken desktop UI.
7. **Visual gates:** require screenshot/visual-regression evidence for desktop home, selected sidecar, filters, context menu, DR/health overlays, cleanup/resolve modal, dark mode, tablet, and mobile.
8. **PDS asset mode:** keep local pinned PDS runtime assets. Do not switch to live CDN as part of visual remediation; local PDS assets already hydrate and CDN mode would change CSP/packaging without fixing composition.

Reference artifacts:
- Audit: `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md`
- Existing DR to resolve/amend through Cockpit lifecycle: `.owlbear/kanban/decisions/pending/1534-decision.md`

Next requirement for #1560: create the tracked Cockpit design policy artifact required by AC-2/AC-4/AC-5, then record board-state evidence that dependent design tasks remain gated until that artifact exists.


## Evidence — 2026-05-14 Policy Artifact
Tracked policy artifact created: `.owlbear/research/1560-cockpit-design-policy.md`.

Artifact covers AC-2/AC-4/AC-5:
- PDS component map for visible controls, overlays, filters/forms, metadata chips, activity rows, and separators.
- Visual target/rubric for a quiet, dense developer-operations cockpit.
- Surface policies for shell/status, sidecar inspector, overlays, filters/forms, cards/columns, responsive behavior, and asset mode.
- Required screenshot/structural gates.
- PDS asset-mode stance: keep local pinned runtime assets; no live CDN switch for visual remediation.

Board-state audit: dependent design tasks #1562, #1563, #1564, #1565, #1566, and #1574 remain backlog with dependency on #1560. Build tasks remain transitively blocked behind their RED/design dependencies. No duplicate DR was created; #1534 remains the formal DR lifecycle artifact for Cockpit resolution.
2026-05-14T18:43:40+00:00
Policy gate completed. User selected the recommended #1560 package in chat: full coordinated Cockpit dashboard redesign, PDS-first visible controls, sidecar-as-inspector direction, PPopover/PModal/PSheet overlay policy, 320px no-overflow mobile contract with board-first/sheet preference, screenshot/structural visual gates, and local pinned PDS asset mode. Evidence recorded in task body. Tracked policy artifact added at `.owlbear/research/1560-cockpit-design-policy.md`. Board-state audit verified dependent design tasks remain backlog/dependency-blocked until this gate completes.
2026-05-14T18:53:21+00:00
Cleanup after decision/policy handoff: release accidental claim without changing review status. #1560 evidence and commits are already recorded.