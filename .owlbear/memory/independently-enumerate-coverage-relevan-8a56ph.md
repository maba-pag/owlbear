---
id: 6212a312-b794-43ae-8cc2-5f7345c3e4eb
title: Independently enumerate coverage-relevant suites
categories:
- pitfall
- process
- tool-usage
confidence: 0.84
state: curated
scope_agents:
- verifier
- collector
source_agent: copilot
created_at: '2026-05-17T01:37:35.815638Z'
updated_at: '2026-05-17T01:48:20.826067Z'
approved_at: null
---

Do not rely only on the builder's stated file list for coverage or regression scope. Independently enumerate adjacent suites that exercise the changed public surface; missing one suite can materially distort baseline coverage or hide shared-envelope regressions.
