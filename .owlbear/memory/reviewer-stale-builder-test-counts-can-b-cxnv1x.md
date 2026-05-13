---
id: 96a7e408-c53d-4e86-b583-bc522acc2475
title: 'Reviewer: stale builder test counts can be resolved with scoped rerun'
categories:
- pitfall
- process
- tool-usage
confidence: 0.86
state: curated
scope_agents:
- reviewer
source_agent: reviewer
created_at: '2026-05-13T05:57:20.101724Z'
updated_at: '2026-05-13T05:59:37.840197Z'
approved_at: null
---

If builder notes cite an impossible pytest count for a named proof file (for example 42 passed where the file defines 24 concrete tests and no parametrization), treat it as contradictory evidence and run a scoped quality-runner verification. If the rerun confirms the actual test/lint packet and AC proof is otherwise sufficient, record the stale count as an observation rather than auto-failing the task.
