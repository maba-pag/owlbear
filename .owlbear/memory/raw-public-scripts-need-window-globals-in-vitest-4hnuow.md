---
id: c026706e-d4c7-4a1a-9147-4825667b825e
title: Raw public scripts need window globals in Vitest
categories:
- pitfall
- tool-usage
- domain-knowledge
confidence: 0.85
state: approved
scope_agents:
- builder
- verifier
source_agent: builder
created_at: '2026-05-14T03:01:24.945577Z'
updated_at: '2026-05-16T23:01:22.448961Z'
approved_at: '2026-05-16T23:01:22.448968Z'
---

For raw public JavaScript files executed through `new Function` in Vitest/jsdom, use explicit `window.*` globals such as `window.localStorage` and `window.document`. Bare browser globals can throw `ReferenceError` or trigger `no-undef` because the file is not bundled like application TSX.
