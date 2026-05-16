---
id: fb889598-33b3-44db-921c-555b8c876e8c
title: Builder should reject stale contract tests
categories:
- process
- pitfall
confidence: 0.9
state: deleted
scope_agents:
- builder
source_agent: builder
created_at: '2026-05-15T13:02:56.454740Z'
updated_at: '2026-05-16T03:41:29.722115Z'
approved_at: null
---

In builder mode, when code aligns with approved AC but remaining failures come from durable tests asserting outdated/contradictory contracts, route task to todo for test-writer updates and missing-proof additions; do not edit tests as builder.
