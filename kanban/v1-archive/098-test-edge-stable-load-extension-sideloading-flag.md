---
id: 98
title: Test Edge Stable --load-extension sideloading flag
status: archived
priority: someday
created: 2026-02-27T03:15:10.3521445+01:00
updated: 2026-03-02T09:14:05.4605922+01:00
started: 2026-02-27T03:32:44.4664477+01:00
completed: 2026-03-02T09:14:05.4605922+01:00
tags:
    - phase-6
    - browser
    - research
class: standard
---

## Intent
Visually distinguish OwlBear-controlled browser tabs from normal user tabs.

## Constraint (2026-02-27)
Edge and all other browsers are locked down by IT admins. Extension sideloading is blocked — only whitelisted addons can be installed. Any solution must work WITHOUT browser extensions.

## Original approach (invalidated)
Test Edge Stable --load-extension flag to sideload a custom extension. This is impossible due to IT policy.

## Research needed
Find alternative approaches that achieve the same goal without extensions:
- Title prefix via document.title (already implemented via CDP in BrowserToolset)
- CSS injection via CDP
- Tab grouping via CDP (Chrome DevTools Protocol)
- Other CDP-based visual indicators
- Userscript managers if whitelisted

The title prefix approach already exists in BrowserToolset.setup() — evaluate if this is sufficient or if additional visual cues are needed.
