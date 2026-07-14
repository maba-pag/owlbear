---
approved_at: null
categories: [pitfall, process, domain-knowledge]
confidence: 0.8
contested_by_task: null
created_at: '2026-05-17T01:38:53.795457Z'
didnt_use_count: 0
id: 7a62780d-187a-4375-aded-91d7b9fdc677
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: copilot
state: deleted
title: Structural import ACs require exact import forms
unremarkable_count: 0
updated_at: '2026-07-14T23:52:17.429419+00:00'
---

AST-structural AC tests can require the exact import form named by the AC; alias re-exports that point to the same object may still fail. Use direct imports from canonical leaf modules when the structural contract names them.
