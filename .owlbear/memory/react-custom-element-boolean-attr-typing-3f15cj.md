---
id: 421dfc75-a207-4070-9733-b0fa4b9f6add
title: Custom element boolean attrs in vite-env need boolean JSX typing
categories:
- pitfall
- tool-usage
confidence: 0.86
state: curated
scope_agents:
- builder
source_agent: builder
created_at: '2026-05-14T23:39:40.857236Z'
updated_at: '2026-05-15T21:06:53.399819Z'
approved_at: null
---

In Cockpit TSX, custom element attrs like `<p-sheet open>` need JSX intrinsic typings that allow boolean values, not just strings. If a boolean attr is typed as string-only, Vite can fail the build before Playwright webServer startup.
