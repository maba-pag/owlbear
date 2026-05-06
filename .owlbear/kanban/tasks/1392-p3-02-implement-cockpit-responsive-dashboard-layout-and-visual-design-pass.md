---
id: 1392
title: 'P3-02: Implement Cockpit responsive dashboard layout and visual design pass'
status: backlog
priority: critical
created: 2026-05-06T01:09:36.552112+00:00
updated: 2026-05-06T01:12:19.335696+00:00
tags:
- cockpit
- audit-remediation
- phase-3
- scope:cockpit-web
- type:fix
- frontend
- dashboard
- visual-design
- responsive
- pds
parent: 1363
depends_on:
- 1391
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Implement the responsive Cockpit dashboard layout and visual design pass proven by #1391.

## Problem Evidence
- Shell.css uses a fixed 56px 1fr 360px grid with no responsive breakpoint or sidecar collapse.
- Current desktop layout is cramped in the board while leaving the sidecar visually empty.
- Current mobile layout exposes chrome but not a practical board workflow.
- Core board and card styling relies on inline or hardcoded values instead of the design system where suitable.

## Acceptance Criteria
- Cockpit presents a cohesive responsive dashboard layout for desktop, tablet, and mobile.
- Board, sidecar, status and navigation surfaces, cards, empty states, loading states, error states, and interaction affordances read as one Cockpit experience.
- Mobile has usable board navigation plus task detail or sidecar access without relying on hidden horizontal scrolling as the only path.
- Desktop remains dense, scan-friendly, and suitable for repeated operational use.
- PDS tokens and components are used for spacing, color, typography, and controls where equivalents exist.
- Hardcoded priority hex colors and avoidable hardcoded styling in core board/card surfaces are replaced with PDS-compatible presentation where equivalents exist.
- The visual and responsive checks from #1391 pass at 320px, 768px, 1024px, and 1440px.

## Scope
- In scope: Cockpit frontend dashboard layout, board presentation, sidecar shell presentation, status/navigation presentation, card styling, empty/loading/error states, and visual verification updates.
- Out of scope: operational sidecar behavior from #1394, global accessibility remediation from #1396, production test-harness cleanup from #1397, docs, delivery packaging, and cache/SSE invalidation from #1346.

## Counterpart
Test task: #1391.
