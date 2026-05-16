---
id: 1608
title: 'P2-01: Component complexity inventory'
status: research
priority: important
created: 2026-05-16T03:36:20.585323+00:00
updated: 2026-05-16T03:36:20.585323+00:00
tags:
  - frontend
  - pds
  - phase-2
parent: 1590
depends_on:
  - 1603
ac:
  - 'Document classifies every raw interactive/display element as: simple swap, complex
    integration, or intentional native (with rationale for each intentional-native
    decision)'
  - Dependency graph produced showing which component migrations can proceed in 
    parallel
  - 'Inventory accounts for: buttons, headings, selects, lists, web-component elements,
    modals, and form controls'
proof_bundle: skip
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Research artifact: classify remaining raw HTML elements by migration complexity. Prerequisite for component migration tasks. Must preserve intentional native controls where tests assert specific DOM contracts (e.g., sidecar collapse button, theme toggle).

Scope: Inventory/analysis only.
Out of scope: Code changes, component replacement.