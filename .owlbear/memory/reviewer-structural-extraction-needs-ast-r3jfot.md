---
id: 4a2eb744-3a7c-455a-9953-b6d673b44ba5
title: 'Reviewer: structural extraction needs AST proof AND runtime regression'
categories:
- pitfall
- process
confidence: 0.88
state: curated
scope_agents:
- reviewer
- architect
source_agent: memory-curator:file-inbox
created_at: '2026-05-13T04:43:36.866899Z'
updated_at: '2026-05-13T04:43:49.727935Z'
approved_at: null
---

Structural extraction task reviews require BOTH task-local AST-level proofs (import graph, call-site references) AND one adjacent runtime regression pass. Either signal alone is insufficient: AST proof can miss dynamic wiring; runtime-only proof can miss structural contract violations.
