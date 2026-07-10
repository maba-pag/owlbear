---
id: eb14cee7-18c2-464b-bf8a-5b343805bde7
title: Behavioral retry evidence gap handling
categories:
- process
- tool-usage
confidence: 0.83
state: curated
scope_agents:
- verifier
source_agent: reviewer
created_at: '2026-05-25T21:16:09.922510Z'
updated_at: '2026-05-26T01:23:58.770063Z'
approved_at: null
---

For verifier passes on behavioral-bundle test-only retries, if the latest note closes the prior blocker but omits fresh lint/coverage evidence, prefer an independent scoped quality-runner rerun over another FAIL when the remaining concerns are observational rather than contract-breaking.
