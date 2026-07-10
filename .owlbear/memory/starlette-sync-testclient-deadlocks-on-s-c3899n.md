---
id: 1451c337-b093-4ed1-b56d-980c21caf98e
title: Starlette sync TestClient deadlocks on SSE
categories:
- pitfall
- tool-usage
- domain-knowledge
confidence: 0.9
state: approved
scope_agents:
- builder
- verifier
source_agent: copilot
created_at: '2026-05-17T01:34:41.819630Z'
updated_at: '2026-05-17T03:17:40.428767Z'
approved_at: '2026-05-17T03:17:40.429042Z'
---

Starlette sync `TestClient` may never observe disconnect for SSE because streaming responses keep `more_body=True`. For header/status-only SSE tests, patch the infinite producer to stop; for stream content, prefer direct route/body-iterator checks with timeouts or async transport patterns instead of relying on sync disconnect.
