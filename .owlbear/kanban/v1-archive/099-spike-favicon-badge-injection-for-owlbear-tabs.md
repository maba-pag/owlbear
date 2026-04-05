---
id: 99
title: 'Spike: favicon badge injection for OwlBear tabs'
status: archived
priority: someday
created: 2026-02-27T03:15:19.317906+01:00
updated: 2026-03-02T09:14:07.5045447+01:00
started: 2026-02-27T03:32:44.8825842+01:00
completed: 2026-03-02T09:14:07.5045447+01:00
tags:
    - phase-6
    - browser
    - research
class: standard
---

## Intent
Provide a visible badge or icon on OwlBear-controlled browser tabs so the user can instantly tell which tabs are agent-managed.

## Constraint (2026-02-27)
Edge and all other browsers are locked down by IT admins. Extension sideloading is blocked — only whitelisted addons can be installed. Favicon injection via extension is impossible.

## Original approach (invalidated)
Inject a custom favicon badge via a browser extension. Cannot install extensions.

## Research needed
Alternative favicon/badge approaches without extensions:
- CDP Page.setDocumentContent or Runtime.evaluate to modify favicon link elements
- Inline SVG favicon with overlay badge via CDP
- CSS-based tab indicators (limited but possible via CDP injection)
- Tab grouping with color labels via CDP (Chrome/Edge support)
- Combination with existing title prefix ([OwlBear] prefix already works)

Key question: is the title prefix sufficient, or do users need stronger visual cues?
