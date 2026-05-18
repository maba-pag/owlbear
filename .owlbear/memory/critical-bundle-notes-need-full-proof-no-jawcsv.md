---
id: 9e6876b5-2ce6-4cd4-87bd-c82f431295d5
title: Critical bundle notes need full proof, not scoped wrappers
categories:
- process
- pitfall
confidence: 0.9
state: curated
scope_agents:
- reviewer
source_agent: reviewer
created_at: '2026-05-18T01:44:39.570225Z'
updated_at: '2026-05-18T02:13:24.860890Z'
approved_at: null
---

For critical proof bundles, do not accept builder evidence that only cites a scoped consolidation wrapper if the AC names broader commands. A wrapper may execute only one toolchain (e.g. Playwright) while the AC also requires others (e.g. Vitest, build). Require an independent quality-runner pass covering all named commands before accepting the bundle as proof.
