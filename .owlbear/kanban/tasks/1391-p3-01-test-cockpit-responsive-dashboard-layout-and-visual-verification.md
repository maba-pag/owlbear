---
id: 1391
title: 'P3-01: Test Cockpit responsive dashboard layout and visual verification'
status: backlog
priority: needed
created: 2026-05-06T01:09:35.035217+00:00
updated: 2026-05-06T01:12:17.606834+00:00
tags:
- cockpit
- audit-remediation
- phase-3
- scope:cockpit-web
- type:test
- frontend
- dashboard
- visual-verification
- responsive
- pds
parent: 1363
depends_on:
- 1367
- 1375
- 1383
- 1389
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Write frontend and visual tests proving Cockpit has a usable responsive dashboard across core viewports before the design pass is implemented.

## Problem Evidence
- Shell.css uses a fixed 56px 1fr 360px grid with no responsive breakpoint or sidecar collapse.
- Desktop evidence shows a cramped skeletal board beside an oversized empty sidecar.
- Mobile evidence shows status and navigation chrome without a usable board.
- Board, column, card, empty, loading, and error styling is partly inline and hardcoded, including priority colors.

## Acceptance Criteria
- Tests prove the dashboard is usable at 320px, 768px, 1024px, and 1440px viewports without incoherent overlap.
- Tests prove mobile users can reach the board and task detail or sidecar surfaces without a hidden horizontal-scroll-only failure.
- Tests prove desktop remains dense and scan-friendly for repeated operational board review.
- Tests cover board columns, sidecar, status and navigation surfaces, cards, empty states, loading states, error states, and primary interaction affordances as one coherent experience.
- Tests prove PDS-compatible token or component usage is expected for spacing, color, typography, controls, and priority presentation where equivalents exist.
- The proof fails against the audited fixed-grid and hardcoded styling behavior and is suitable for #1392 to satisfy.

## Scope
- In scope: Cockpit frontend responsive layout, visual regression, and component-state tests for dashboard surfaces.
- Out of scope: implementing the design pass, operational sidecar admin behavior from #1394, global accessibility gate from #1396, delivery packaging, docs, and cache/SSE invalidation from #1346.

## Counterpart
Implementation task: #1392.
