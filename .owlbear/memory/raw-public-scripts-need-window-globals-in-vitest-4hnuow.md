---
approved_at: '2026-05-16T23:01:22.448968Z'
categories: [pitfall, tool-usage, domain-knowledge]
confidence: 0.85
contested_by_task: null
created_at: '2026-05-14T03:01:24.945577Z'
didnt_use_count: 4
id: c026706e-d4c7-4a1a-9147-4825667b825e
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.85
source_agent: builder
state: approved
title: Raw public scripts need window globals in Vitest
unremarkable_count: 0
updated_at: '2026-07-22T00:35:55.406807+00:00'
---

For raw public JavaScript files executed through `new Function` in Vitest/jsdom, use explicit `window.*` globals such as `window.localStorage` and `window.document`. Bare browser globals can throw `ReferenceError` or trigger `no-undef` because the file is not bundled like application TSX.
