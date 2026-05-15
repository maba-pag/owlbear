---
id: 9b6fdc6b-290f-47a3-a14d-3901cedc1064
title: Ingest source resolution scope compatibility
categories:
- pitfall
- domain-knowledge
confidence: 0.9
state: deleted
scope_agents:
- builder
source_agent: builder
created_at: '2026-05-14T19:32:06.303541Z'
updated_at: '2026-05-15T20:58:35.498475Z'
approved_at: null
---

When extending KnowledgeSourceStore.resolve_by_url with scope filtering, keep backward-compatible one-argument call behavior for global scope. Several durable tests/mocks assert resolve_by_url(url) exactly or use single-arg lambdas; calling with scope kw unconditionally breaks them.
