---
id: 1595
title: 'P0-04: Install @tailwindcss/vite + configure Stylelint for Tailwind v4'
status: research
priority: critical
created: 2026-05-16T03:35:01.729375+00:00
updated: 2026-05-16T03:35:01.729375+00:00
tags:
  - frontend
  - pds
  - phase-0
parent: 1590
depends_on:
  - 1592
ac:
  - PDS Tailwind utilities (bg-canvas, text-contrast-high, gap-md) compile 
    without error and light-dark() preserved in vite build
  - package.json pins tailwindcss ^4 and @tailwindcss/vite ^4; no PostCSS config
    exists; LightningCSS remains CSS transformer
  - npm run lint:css passes with zero violations on @theme, @utility, @apply 
    at-rules
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Install `@tailwindcss/vite` as Vite plugin (NOT PostCSS — preserves LightningCSS). Import PDS Tailwind theme from `@porsche-design-system/components-react/tailwindcss/index.css`. Pin `tailwindcss ^4` + `@tailwindcss/vite ^4`. Update Stylelint config for Tailwind v4 `@theme` / `@utility` at-rules.

Scope: Tailwind install + Stylelint config.
Out of scope: Token migration, component migration, layout.