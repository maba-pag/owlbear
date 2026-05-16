---
id: 1614
title: 'P2-03: Simple component swaps'
status: research
priority: important
created: 2026-05-16T03:37:02.195428+00:00
updated: 2026-05-16T03:37:02.195428+00:00
tags:
  - frontend
  - pds
  - phase-2
parent: 1590
depends_on:
  - 1609
ac:
  - Zero raw <select elements in source files outside test files
  - PDS web-component elements (<p-button>, <p-icon>) replaced with React 
    wrapper equivalents (PButton, PIcon)
  - Raw <button> and <h1>-<h6> elements remain only where inventory documents 
    them as intentional native
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Replace raw HTML: `<button>` → `PButton`, `<h1>`-`<h6>` → `PHeading`/`PText`, `<select>` → `PSelect`, raw web-components → React wrappers. Preserve intentional native controls where tests assert specific DOM contracts.

Scope: Simple swaps only.
Out of scope: Cards, sidecar IA, modals, filter panel.