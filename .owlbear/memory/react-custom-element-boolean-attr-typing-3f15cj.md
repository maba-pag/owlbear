---
id: 421dfc75-a207-4070-9733-b0fa4b9f6add
title: React custom element boolean attr typing in vite-env
categories:
- pitfall
- tool-usage
confidence: 0.86
state: curated
scope_agents:
- builder
source_agent: builder
created_at: '2026-05-14T23:39:40.857236Z'
updated_at: '2026-05-15T03:02:51.004001Z'
approved_at: null
---

In Cockpit TSX, custom element attrs like <p-sheet open> require JSX intrinsic typing to allow boolean values (open?: boolean | string). If typed as string only, Vite build fails before Playwright webServer startup.
