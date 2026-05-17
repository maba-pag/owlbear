---
id: d15dc27d-2e6a-434a-b62f-43726dd8e66c
title: Loop-breaker counts use task evidence sections
categories:
- pitfall
- process
confidence: 0.84
state: curated
scope_agents:
- reviewer
- architect
- auditor
source_agent: copilot
created_at: '2026-05-17T01:38:08.448995Z'
updated_at: '2026-05-17T01:48:31.749372Z'
approved_at: null
---

For review loop-breaker decisions, count `## Review Evidence` sections in the task file itself. Do not rely on memory or summaries, and account for substantive architecture rewrites before treating repeated sections as the same loop.
