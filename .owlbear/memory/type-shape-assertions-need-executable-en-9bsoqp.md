---
approved_at: null
categories: [pitfall, process, tool-usage]
confidence: 0.82
contested_by_task: null
created_at: '2026-05-17T01:38:05.563960Z'
didnt_use_count: 0
id: 3f30ad79-7c19-4c31-baca-a9fa47c90cd4
outstanding_count: 0
scope_agents: [verifier, builder]
score: 0.0
source_agent: copilot
state: deleted
title: Type-shape assertions need executable enforcement
unremarkable_count: 0
updated_at: '2026-07-14T23:51:28.528947+00:00'
---

TypeScript `expectTypeOf` calls and comments can overstate proof. Before accepting type-shape evidence, inspect the actual matcher and verify it would fail on the claimed regression; descriptive comments are not executable assertions.
