---
id: c4e2df9c-991d-4199-81c6-b9a719ccd8ed
title: Patch the actual file API under test
categories:
- pitfall
- tool-usage
confidence: 0.82
state: curated
scope_agents:
- test-writer
- reviewer
- builder
source_agent: copilot
created_at: '2026-05-17T01:37:45.136816Z'
updated_at: '2026-05-17T01:48:20.889294Z'
approved_at: null
---

Tests that patch `builtins.open` do not exercise code that calls `Path.read_text()` or other path APIs. When proving source-of-truth or filesystem behavior, patch or simulate the exact API the implementation uses.
