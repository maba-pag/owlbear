---
approved_at: '2026-05-16T22:05:05.637998Z'
categories: [pitfall, process]
confidence: 0.85
contested_by_task: null
created_at: '2026-05-13T21:09:42.972951Z'
didnt_use_count: 2
id: ecee51b4-81d6-4d64-9676-626610cf6749
outstanding_count: 0
scope_agents: [verifier, builder, shaper]
score: 0.85
source_agent: reviewer
state: approved
title: Named CSS selectors need selector-scoped proof
unremarkable_count: 0
updated_at: '2026-07-21T09:13:41.512546+00:00'
---

When a CSS source-contract AC names a class or selector, require proof against that selector itself. Generic class presence plus a file-wide regex can false-green after declarations move elsewhere; the rendered element and CSS assertion both need to target the named selector.
