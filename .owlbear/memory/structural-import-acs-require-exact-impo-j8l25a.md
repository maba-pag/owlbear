---
id: 7a62780d-187a-4375-aded-91d7b9fdc677
title: Structural import ACs require exact import forms
categories:
- pitfall
- process
- domain-knowledge
confidence: 0.8
state: curated
scope_agents:
- builder
- verifier
source_agent: copilot
created_at: '2026-05-17T01:38:53.795457Z'
updated_at: '2026-05-17T01:48:32.119552Z'
approved_at: null
---

AST-structural AC tests can require the exact import form named by the AC; alias re-exports that point to the same object may still fail. Use direct imports from canonical leaf modules when the structural contract names them.
