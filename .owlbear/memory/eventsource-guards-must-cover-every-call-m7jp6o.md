---
approved_at: null
categories: [pitfall, domain-knowledge]
confidence: 0.86
contested_by_task: null
created_at: '2026-05-17T01:37:17.301926Z'
didnt_use_count: 0
id: 694001e5-084f-489e-852c-bb073c82e9ae
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: copilot
state: deleted
title: EventSource guards must cover every callback path
unremarkable_count: 0
updated_at: '2026-07-14T23:48:46.272373+00:00'
---

In EventSource hooks, mounted/source-identity guards must be applied independently in `onopen`, `onerror`, timer callbacks, and event listeners. A stale-source test for one callback does not prove the others are safe.
