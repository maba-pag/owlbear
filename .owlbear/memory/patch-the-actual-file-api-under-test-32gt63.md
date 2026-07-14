---
approved_at: null
categories: [pitfall, tool-usage]
confidence: 0.82
contested_by_task: null
created_at: '2026-05-17T01:37:45.136816Z'
didnt_use_count: 0
id: c4e2df9c-991d-4199-81c6-b9a719ccd8ed
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: copilot
state: deleted
title: Patch the actual file API under test
unremarkable_count: 0
updated_at: '2026-07-14T23:48:15.235765+00:00'
---

Tests that patch `builtins.open` do not exercise code that calls `Path.read_text()` or other path APIs. When proving source-of-truth or filesystem behavior, patch or simulate the exact API the implementation uses.
