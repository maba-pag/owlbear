---
id: f5ad5e3d-8958-45fc-b8e8-8e20a195dd84
title: Vitest/jsdom PButton role mismatch
categories:
- pitfall
- tool-usage
- domain-knowledge
confidence: 0.91
state: curated
scope_agents:
- builder
- test-writer
- reviewer
source_agent: builder
created_at: '2026-05-14T06:32:10.008051Z'
updated_at: '2026-05-14T06:48:35.608263Z'
approved_at: null
---

In cockpit frontend tests, PDS PButton may not expose an accessible role=button in jsdom queries. If AC/tests use getByRole('button'), use a native <button> or adapt tests to host-element contracts to avoid false failures.
