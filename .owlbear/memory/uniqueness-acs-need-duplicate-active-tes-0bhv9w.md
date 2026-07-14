---
approved_at: null
categories: [pitfall, process, domain-knowledge]
confidence: 0.84
contested_by_task: null
created_at: '2026-05-17T01:38:02.875498Z'
didnt_use_count: 0
id: 8c8f2f1e-4c74-4a80-ad55-8b50de9b4431
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: copilot
state: deleted
title: Uniqueness ACs need duplicate-active tests
unremarkable_count: 0
updated_at: '2026-07-14T23:51:28.371145+00:00'
---

For ACs saying only one timer, interval, retry, or similar resource may be active, boundary tests are insufficient. Trigger a second instance while the first is still active and assert that only one survives.
