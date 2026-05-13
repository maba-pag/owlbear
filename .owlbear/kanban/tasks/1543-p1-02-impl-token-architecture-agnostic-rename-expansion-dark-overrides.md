---
id: 1543
title: 'P1-02: impl — token architecture: agnostic rename + expansion + dark overrides'
status: research
priority: critical
created: 2026-05-13T18:42:22.266810+00:00
updated: 2026-05-13T18:42:22.266810+00:00
tags:
  - phase-1
  - scope:cockpit
  - css
  - frontend
parent: 1534
depends_on:
  - 1535
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1534 (`.owlbear/briefs/draft-board-visual-design/brief.md`)

## Scope
- **In:** Restructure `tokens.css` to agnostic names, add dark overrides selector, add shadow/radius/spacing token sets, add `@media (prefers-color-scheme: dark)` fallback
- **Out:** Theme bootstrap script, useTheme hook, component CSS consumption of tokens

## Acceptance Criteria

- AC-1: `tokens.css` uses agnostic `--pds-*` names; light values in `:root`, dark overrides in `[data-theme="dark"]`
- AC-2: `@media (prefers-color-scheme: dark)` fallback applies dark overrides when no `data-theme` attribute is present on `<html>`
- AC-3: Shadow (`--pds-shadow-{sm,md,lg}`), border-radius (`--pds-radius-{sm..xl}`), and spacing (`--pds-spacing-{xs..2xl}`) token sets defined in `:root` as theme-independent values

Proof bundle: behavioral