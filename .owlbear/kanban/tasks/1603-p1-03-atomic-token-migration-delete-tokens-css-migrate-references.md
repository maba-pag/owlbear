---
id: 1603
title: 'P1-03: Atomic token migration — delete tokens.css + migrate references'
status: research
priority: important
created: 2026-05-16T03:36:06.954546+00:00
updated: 2026-05-16T03:36:06.954546+00:00
tags:
  - frontend
  - pds
  - phase-1
parent: 1590
depends_on:
  - 1600
ac:
  - grep -r '\-\-pds-' serve/cockpit/web/src/ returns zero matches (CSS and TSX)
  - tokens.css deleted; custom-tokens.css exists only for values the provenance 
    map classified as custom-keep
  - Manual dark-mode override blocks ([data-theme="dark"] and @media 
    prefers-color-scheme) removed from authored CSS
  - Tests formerly asserting --pds-* names updated to assert --p-* equivalents 
    or retired with documented rationale
proof_bundle: critical
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Atomic migration (constraint C4): delete `tokens.css`, update `--pds-*` → `--p-*` or Tailwind utility, create `custom-tokens.css` only for provenance-map custom-keep values. Update/retire test assertions: TokenArchitecture, BoardVisualDesign, PdsColorSchemeBridge, PdsMigration, ShellSecondaryCSS.

Complexity waiver: 4 AC exceeds target of 3 because token migration is explicitly atomic per constraint C4 — splitting delete/migrate/custom-tokens across tasks would violate the brief.

Scope: Token migration + test updates.
Out of scope: New components, layout changes.