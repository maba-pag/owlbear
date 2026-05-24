---
id: 1781
title: Stabilize Cockpit UX sweep against route transition fade
status: research
priority: important
created: 2026-05-24T01:17:30.229704+02:00
updated: 2026-05-24T01:56:07.037784+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - visual-proof
  - tooling
  - discussion
parent: 1773
depends_on:
  - 1773
ac:
  - UX sweep screenshots are captured only after route content opacity is 1 and 
    transform has settled.
  - Memory and Ideas steady-state screenshots show final rendered 
    entries/content rather than faded transition frames.
  - Product UX tasks are created only from stable evidence, not transition 
    artifacts.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
During the #1773 general-UX reframe, several supported-width screenshots appear faded or skeletal even though they are meant to represent steady tab states. Examples include `1773-desktop-1024-memory-rest.png` and `1773-desktop-1024-ideas-rest.png`.

## Current Interpretation
Likely proof-readiness harm, not product UX harm yet. Shell route content uses Framer Motion with `initial={{ opacity: 0, y: 6 }}` and `animate={{ opacity: 1, y: 0 }}` over 0.18s. The sweep's two-RAF settle may still capture route transition or PDS hydration/paint settling.

## Value
General UX critique depends on trustworthy screenshots. Faded proof can make real screens look disabled, low-contrast, empty, or skeletal and can lead to wrong product tasks.

## Evidence
- `.owlbear/scratch/1716-wide-cockpit/1773-desktop-1024-memory-rest.png`
- `.owlbear/scratch/1716-wide-cockpit/1773-desktop-1024-ideas-rest.png`
- `serve/cockpit/web/src/Shell.tsx` route wrapper uses Framer Motion opacity/y transition.

## Decision Needed
Before filing product UX tasks from faded screenshots, run focused probes that wait for route-wrapper opacity/transform settling and loaded tab content.

[[2026-05-24T01:56:07+02:00]]
## User Feedback
User confirmed the faded look is a strong signal of screenshots being taken too early. Treat this as proof-readiness/tooling, not product UX. Keep using stable route-content waits before filing product tasks from screenshots.
