---
id: 8c8f2f1e-4c74-4a80-ad55-8b50de9b4431
title: Uniqueness ACs need duplicate-active tests
categories:
- pitfall
- process
- domain-knowledge
confidence: 0.84
state: curated
scope_agents:
- test-writer
- reviewer
- builder
source_agent: copilot
created_at: '2026-05-17T01:38:02.875498Z'
updated_at: '2026-05-17T01:48:31.664956Z'
approved_at: null
---

For ACs saying only one timer, interval, retry, or similar resource may be active, boundary tests are insufficient. Trigger a second instance while the first is still active and assert that only one survives.
