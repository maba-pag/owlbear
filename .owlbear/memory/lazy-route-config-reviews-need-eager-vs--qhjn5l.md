---
id: c243ab11-26a9-4aec-a460-50fd5c946e21
title: Lazy route config reviews need eager-vs-lazy durable proof
categories:
- pitfall
- domain-knowledge
confidence: 0.84
state: curated
scope_agents:
- verifier
- builder
source_agent: reviewer
created_at: '2026-05-19T08:52:32.103433Z'
updated_at: '2026-05-19T10:43:16.005786Z'
approved_at: null
---

When a routeConfig component field moves to React.lazy, do not PASS on task-local lazy-route tests alone. Verify adjacent durable tests no longer assume typeof component === 'function', still prove the default route remains eager, and await Suspense resolution for real-route integration tests.
