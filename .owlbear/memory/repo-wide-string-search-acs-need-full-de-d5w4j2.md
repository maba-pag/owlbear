---
id: e1e10857-dec0-4341-9138-ef02546c53e0
title: Repo-wide string-search ACs need full declared surface
categories:
- pitfall
- process
- tool-usage
confidence: 0.84
state: curated
scope_agents:
- builder
- verifier
source_agent: copilot
created_at: '2026-05-17T01:37:51.641533Z'
updated_at: '2026-05-17T01:48:21.007634Z'
approved_at: null
---

For repo-wide string-search or banned-token ACs, tests must scan the full declared surface or explicitly exempt historical paths. Scanning only `serve/` or `share/` can false-green while `.owlbear/decisions`, sources, or other retained artifacts still contain the banned text.
