---
id: d16bcf80-7b6c-45d4-824b-c5df5d245d0b
title: AST merge scripts can drop pytest fixtures
categories:
- pitfall
- tool-usage
confidence: 0.84
state: deleted
scope_agents:
- builder
- test-writer
- reviewer
source_agent: copilot
created_at: '2026-05-17T01:34:05.971805Z'
updated_at: '2026-05-17T02:59:59.231712Z'
approved_at: null
---

After scripted AST merges, verify pytest fixture decorators and per-package pass-count parity. Scripts that append only top-level functions/classes can drop `@pytest.fixture` decorators or skip colliding class methods, causing fixture-not-found errors and test-count regressions.
