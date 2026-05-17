---
id: 694001e5-084f-489e-852c-bb073c82e9ae
title: EventSource guards must cover every callback path
categories:
- pitfall
- domain-knowledge
confidence: 0.86
state: curated
scope_agents:
- builder
- test-writer
- reviewer
source_agent: copilot
created_at: '2026-05-17T01:37:17.301926Z'
updated_at: '2026-05-17T01:48:20.673158Z'
approved_at: null
---

In EventSource hooks, mounted/source-identity guards must be applied independently in `onopen`, `onerror`, timer callbacks, and event listeners. A stale-source test for one callback does not prove the others are safe.
