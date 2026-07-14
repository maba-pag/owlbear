---
approved_at: null
categories: [pitfall, process, tool-usage]
confidence: 0.84
contested_by_task: null
created_at: '2026-05-17T01:37:35.815638Z'
didnt_use_count: 1
id: 6212a312-b794-43ae-8cc2-5f7345c3e4eb
outstanding_count: 0
scope_agents: [verifier, collector]
score: 0.84
source_agent: copilot
state: curated
title: Independently enumerate coverage-relevant suites
unremarkable_count: 0
updated_at: '2026-07-14T06:12:40.711967+00:00'
---

Do not rely only on the builder's stated file list for coverage or regression scope. Independently enumerate adjacent suites that exercise the changed public surface; missing one suite can materially distort baseline coverage or hide shared-envelope regressions.
