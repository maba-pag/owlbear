---
id: 3f30ad79-7c19-4c31-baca-a9fa47c90cd4
title: Type-shape assertions need executable enforcement
categories:
- pitfall
- process
- tool-usage
confidence: 0.82
state: curated
scope_agents:
- reviewer
- test-writer
- builder
source_agent: copilot
created_at: '2026-05-17T01:38:05.563960Z'
updated_at: '2026-05-17T01:48:31.706453Z'
approved_at: null
---

TypeScript `expectTypeOf` calls and comments can overstate proof. Before accepting type-shape evidence, inspect the actual matcher and verify it would fail on the claimed regression; descriptive comments are not executable assertions.
