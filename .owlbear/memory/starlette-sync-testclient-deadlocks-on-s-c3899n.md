---
approved_at: '2026-05-17T03:17:40.429042Z'
categories: [pitfall, tool-usage, domain-knowledge]
confidence: 0.9
contested_by_task: null
created_at: '2026-05-17T01:34:41.819630Z'
didnt_use_count: 4
id: 1451c337-b093-4ed1-b56d-980c21caf98e
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.9
source_agent: copilot
state: approved
title: Starlette sync TestClient deadlocks on SSE
unremarkable_count: 0
updated_at: '2026-07-17T06:28:14.944685+00:00'
---

Starlette sync `TestClient` may never observe disconnect for SSE because streaming responses keep `more_body=True`. For header/status-only SSE tests, patch the infinite producer to stop; for stream content, prefer direct route/body-iterator checks with timeouts or async transport patterns instead of relying on sync disconnect.
