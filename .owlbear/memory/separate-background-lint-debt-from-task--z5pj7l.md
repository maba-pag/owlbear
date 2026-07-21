---
approved_at: '2026-05-17T03:02:34.942395Z'
categories: [pitfall, process, tool-usage]
confidence: 0.9
contested_by_task: null
created_at: '2026-05-17T01:34:12.345749Z'
didnt_use_count: 6
id: a7266466-6568-45f8-9367-da275286e9d7
outstanding_count: 2
scope_agents: [verifier, collector]
score: 1.05
source_agent: copilot
state: approved
title: Separate background quality debt from task failures
unremarkable_count: 5
updated_at: '2026-07-20T21:01:28.171351+00:00'
---

When a broad quality run surfaces failures outside the builder's changed files, run a scoped pass on the changed paths before gating. Use the broad run for regression context, but decide task ownership from scoped evidence so legacy or background quality debt does not become a false task failure.
