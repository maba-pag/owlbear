---
id: 1597
title: 'P1-01: Token provenance map'
status: research
priority: important
created: 2026-05-16T03:35:25.235271+00:00
updated: 2026-05-16T03:35:25.235271+00:00
tags:
  - frontend
  - pds
  - phase-1
parent: 1590
depends_on:
  - 1594
  - 1595
  - 1596
ac:
  - 'Document classifies every --pds-* usage into: PDS equivalent (--p-*), Tailwind
    utility, custom-keep, or dead-delete'
  - 'Coverage: grep-verified zero unclassified --pds-* references across Shell.css,
    Card.css, Column.css, FilterPanel.css, SessionRows.css, ErrorBoundary.tsx, and
    any other source files'
  - Each classification includes the specific replacement token, utility class, 
    or deletion rationale
proof_bundle: skip
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Research artifact: four-way classification of every `--pds-*` reference in `serve/cockpit/web/src/`. Prerequisite for atomic token migration (#P1-03). Must identify affected test files (TokenArchitecture, BoardVisualDesign, PdsColorSchemeBridge, PdsMigration, ShellSecondaryCSS).

Scope: Provenance analysis only.
Out of scope: Code changes, token deletion.