---
id: 83076a5a-c62c-4ce9-8f66-2ed0850e8341
title: Chain ACs need linkage proof
categories:
- pitfall
- process
confidence: 0.91
state: approved
scope_agents:
- reviewer
source_agent: reviewer
created_at: '2026-05-16T14:23:36.558995Z'
updated_at: '2026-05-16T20:05:01.821725Z'
approved_at: '2026-05-16T20:05:01.821736Z'
---

When reviewing tests for an AC that names a relational chain like document→chunk→entity→edge, do not accept row-presence assertions alone. Require task-local assertions on the linkage/provenance fields that make the chain real, or the test can false-green if intermediate links are dropped while rows still exist.
