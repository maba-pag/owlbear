---
approved_at: null
categories: [pitfall, tool-usage, process]
confidence: 0.84
contested_by_task: null
created_at: '2026-05-17T01:37:40.203732Z'
didnt_use_count: 2
id: 259fc77a-599b-4d5f-a97a-64a937c3964b
outstanding_count: 0
scope_agents: [verifier, builder, collector]
score: 0.84
source_agent: copilot
state: deleted
title: Quality-runner lint clean can omit target files
unremarkable_count: 0
updated_at: '2026-07-14T19:14:07.456068+00:00'
---

A scoped quality-runner `Lint: clean` result is weak if the lint report omits the task test file or the touched frontend files. Rerun with explicit `lint_paths` for omitted Python files, and use diagnostics/Vitest rather than Python lint output for TypeScript safety.
