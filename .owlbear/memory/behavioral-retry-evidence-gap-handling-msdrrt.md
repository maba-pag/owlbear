---
approved_at: null
categories: [process, tool-usage]
confidence: 0.83
contested_by_task: null
created_at: '2026-05-25T21:16:09.922510Z'
didnt_use_count: 0
id: eb14cee7-18c2-464b-bf8a-5b343805bde7
outstanding_count: 0
scope_agents: [verifier]
score: 0.0
source_agent: reviewer
state: deleted
title: Behavioral retry evidence gap handling
unremarkable_count: 0
updated_at: '2026-07-14T23:00:22.894730+00:00'
---

For verifier passes on behavioral-bundle test-only retries, if the latest note closes the prior blocker but omits fresh lint/coverage evidence, prefer an independent scoped quality-runner rerun over another FAIL when the remaining concerns are observational rather than contract-breaking.
