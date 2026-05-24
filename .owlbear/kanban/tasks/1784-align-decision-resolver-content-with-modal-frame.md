---
id: 1784
title: Align task and decision detail content with modal frames
status: research
priority: important
created: 2026-05-24T01:22:56.044270+02:00
updated: 2026-05-24T01:56:07.117158+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - visual-proof
  - ux
  - discussion
parent: 1773
depends_on:
  - 1780
ac:
  - At 1024px, the Decision resolver content, dividers, text area, and footer 
    actions sit visually inside the modal frame, not into the backdrop.
  - The resolver remains inside the viewport after the frame alignment fix.
  - The layout remains usable at 1200, 1440, and 2000px widths.
  - No implementation begins until the user approves this task.
  - At 1024px, Kanban task detail content sits visually inside the modal frame, 
    not into the backdrop.
  - At 1024px, Decision detail/resolver content sits visually inside the modal 
    frame, not into the backdrop.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
After #1780, the Decision resolver surface and actions are inside the 1024px viewport, but the resolver content still visually overhangs the PDS modal's white frame at the right and bottom. The screenshot shows horizontal divider lines and footer controls extending into the grey backdrop area, making the dialog feel broken even though viewport containment passes.

## Evidence
- `.owlbear/scratch/1716-wide-cockpit/1784-1024-resolver-frame-check.png`
- Geometry probe at 1024x900: `resolve-modal-surface` left=147.94, right=979.94, width=832; Close button right=979.94. PDS modal host shadow root/backdrop spans viewport, while the visible white panel appears narrower than the child surface.

## Current Interpretation
Observed supported-width UX harm. This is not the same as #1780's viewport clipping; #1780 made content fit the viewport. The remaining problem is child content not fitting the PDS modal frame/visual surface.

## Value
Decision resolution is a high-trust workflow. A modal whose content protrudes past its frame can make the resolver feel unstable or unfinished, especially at the 1024px support floor.

## Decision Needed
Discuss whether to adjust resolver structure/width/padding so all content sits inside the PDS modal frame, or use a custom modal surface if PDS slot geometry cannot support this layout cleanly.

[[2026-05-24T01:56:07+02:00]]
## User Feedback
User confirmed this should be fixed, and broadened the scope: both Kanban task detail and Decision detail/resolver views overhang horizontally. This is not only a Decision resolver issue; the task detail modal frame/content relationship needs the same scrutiny.

Important: this is approval that the issue is real and worth looking at, not automatic approval to implement. Discuss exact solution before code changes.
