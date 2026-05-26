---
id: ebcfd628-7c00-43b7-831c-a2caf6614f4f
title: Scoped durable regression test helps low-cost confidence
categories:
- behaviour
confidence: 0.8
state: pending
scope_agents:
- builder
source_agent: builder
created_at: '2026-05-26T21:52:09.209946Z'
updated_at: '2026-05-26T21:52:09.209946Z'
approved_at: null
---

For retry tasks with tiny source edits, adding one nearby durable test file (e.g., tests/test_ingest_1656.py) to scoped quality-runner catches regressions without full-suite cost.
