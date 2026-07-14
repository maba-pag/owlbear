---
approved_at: null
categories: [pitfall, domain-knowledge]
confidence: 0.84
contested_by_task: null
created_at: '2026-05-19T08:52:32.103433Z'
didnt_use_count: 0
id: c243ab11-26a9-4aec-a460-50fd5c946e21
outstanding_count: 0
scope_agents: [verifier, builder]
score: 0.0
source_agent: reviewer
state: deleted
title: Lazy route config reviews need eager-vs-lazy durable proof
unremarkable_count: 0
updated_at: '2026-07-14T23:53:46.055869+00:00'
---

When a routeConfig component field moves to React.lazy, do not PASS on task-local lazy-route tests alone. Verify adjacent durable tests no longer assume typeof component === 'function', still prove the default route remains eager, and await Suspense resolution for real-route integration tests.
