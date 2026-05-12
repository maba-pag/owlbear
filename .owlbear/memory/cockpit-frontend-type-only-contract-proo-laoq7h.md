---
id: abed2012-e597-4d0c-bdc5-b4d61ec424c3
title: Cockpit frontend type-only contract proofs are not enforced by runtime Vitest
categories:
- pitfall
- process
- tool-usage
confidence: 0.89
state: curated
scope_agents:
- reviewer
- architect
- test-writer
- builder
source_agent: reviewer
created_at: '2026-05-12T10:44:51.243848Z'
updated_at: '2026-05-12T13:35:44.921051Z'
approved_at: null
---

In serve/cockpit/web, npm test runs runtime-only vitest and tsconfig excludes *.test.ts(x). Positive-only type examples in test files do not mechanically prove closed-union/interface ACs. Reviewer should treat such cases as proof gaps and route to backlog if AC requires falsifiable type-contract proof.
